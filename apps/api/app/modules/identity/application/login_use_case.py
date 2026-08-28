import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.token_generator import generate_opaque_token, hash_token
from apps.api.app.modules.identity.infrastructure.password_hasher import PasswordHasher
from apps.api.app.modules.identity.infrastructure.rate_limiter import (
    RedisRateLimiter,
    default_rate_limiter,
)
from apps.api.app.modules.identity.infrastructure.repositories import (
    CredentialRepository,
    SessionRepository,
    UserRepository,
)
from apps.api.app.modules.identity.infrastructure.token_service import TokenService


class LoginUseCase:
    def __init__(self, db: AsyncSession, rate_limiter: Optional[RedisRateLimiter] = None):
        self.db = db
        self.user_repo = UserRepository(db)
        self.cred_repo = CredentialRepository(db)
        self.session_repo = SessionRepository(db)
        self.rate_limiter = rate_limiter or default_rate_limiter

    async def execute(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], str]:
        normalized_email = email.strip().lower()

        # Rate limiting: Max 5 login attempts per 15 minutes per email/IP
        rate_key = f"login:{normalized_email}:{ip_address or 'anon'}"
        await self.rate_limiter.check_rate_limit(key=rate_key, max_requests=5, window_seconds=900)

        # 1. Lookup user safely
        user = await self.user_repo.get_by_email(normalized_email)
        if not user:
            # Constant-time dummy check to prevent account enumeration timing attacks
            PasswordHasher.verify_password("dummy_password", "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy")
            audit = AuditLogORM(
                actor_type="ANONYMOUS",
                action="auth.login_failure",
                resource_type="User",
                ip_address=ip_address,
                metadata_json={"email": normalized_email, "reason": "user_not_found"},
            )
            self.db.add(audit)
            await self.db.commit()
            raise DomainException("Invalid email or password", code="AUTH_INVALID_CREDENTIALS")

        # 2. Check account status
        if user.account_status == "SUSPENDED" or user.account_status == "DISABLED":
            audit = AuditLogORM(
                actor_user_id=user.id,
                actor_type="USER",
                action="auth.login_failure",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip_address,
                metadata_json={"reason": f"account_{user.account_status.lower()}"},
            )
            self.db.add(audit)
            await self.db.commit()
            raise DomainException("Account is suspended or disabled", code="AUTH_ACCOUNT_SUSPENDED")

        # 3. Verify password
        cred = await self.cred_repo.get_by_user_id(user.id)
        if not cred or not PasswordHasher.verify_password(password, cred.password_hash):
            audit = AuditLogORM(
                actor_user_id=user.id,
                actor_type="USER",
                action="auth.login_failure",
                resource_type="User",
                resource_id=user.id,
                ip_address=ip_address,
                metadata_json={"reason": "invalid_password"},
            )
            self.db.add(audit)
            await self.db.commit()
            raise DomainException("Invalid email or password", code="AUTH_INVALID_CREDENTIALS")

        # 4. Create new user session & refresh token family
        family_id = uuid.uuid4()
        raw_refresh_token = generate_opaque_token()
        refresh_token_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        sess = await self.session_repo.create_session(
            user_id=user.id,
            family_id=family_id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # 5. Issue short-lived access token
        access_token = TokenService.create_access_token(user_id=user.id)

        # 6. Audit log
        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.login_success",
            resource_type="UserSession",
            resource_id=sess.id,
            ip_address=ip_address,
            metadata_json={"session_id": str(sess.id), "family_id": str(family_id)},
        )
        self.db.add(audit)
        await self.db.commit()

        response_body = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "account_status": user.account_status,
                "is_super_admin": user.is_super_admin,
            },
        }

        return response_body, raw_refresh_token
