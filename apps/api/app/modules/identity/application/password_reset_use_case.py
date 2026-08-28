from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.password_policy import default_password_policy
from apps.api.app.modules.identity.domain.token_generator import generate_opaque_token, hash_token
from apps.api.app.modules.identity.infrastructure.email_provider import (
    EmailProvider,
    default_email_provider,
)
from apps.api.app.modules.identity.infrastructure.password_hasher import PasswordHasher
from apps.api.app.modules.identity.infrastructure.repositories import (
    CredentialRepository,
    SessionRepository,
    TokenRepository,
    UserRepository,
)


class PasswordResetUseCase:
    def __init__(self, db: AsyncSession, email_provider: Optional[EmailProvider] = None):
        self.db = db
        self.user_repo = UserRepository(db)
        self.cred_repo = CredentialRepository(db)
        self.session_repo = SessionRepository(db)
        self.token_repo = TokenRepository(db)
        self.email_provider = email_provider or default_email_provider

    async def request_password_reset(self, email: str) -> Dict[str, Any]:
        normalized_email = email.strip().lower()
        user = await self.user_repo.get_by_email(normalized_email)

        # Generic response to prevent account enumeration
        generic_msg = "If an account exists for this email, a password reset link has been sent."
        if not user or user.account_status in ("SUSPENDED", "DISABLED"):
            return {"message": generic_msg}

        raw_token = generate_opaque_token()
        token_hash_val = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.token_repo.create_reset_token(user_id=user.id, token_hash=token_hash_val, expires_at=expires_at)

        await self.email_provider.send_password_reset_email(to_email=user.email, raw_token=raw_token)

        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.password_reset_requested",
            resource_type="User",
            resource_id=user.id,
        )
        self.db.add(audit)
        await self.db.commit()

        return {"message": generic_msg}

    async def confirm_password_reset(self, raw_token: str, new_password: str) -> Dict[str, Any]:
        if not raw_token:
            raise DomainException("Reset token is required", code="AUTH_TOKEN_INVALID")

        # 1. Validate password policy
        default_password_policy.validate(new_password)

        # 2. Verify token
        provided_hash = hash_token(raw_token)
        tok = await self.token_repo.get_reset_token(provided_hash)
        if not tok or tok.used_at or tok.invalidated_at:
            raise DomainException("Password reset token is invalid or already used", code="AUTH_TOKEN_INVALID")

        if tok.expires_at < datetime.now(timezone.utc):
            raise DomainException("Password reset token has expired", code="AUTH_TOKEN_EXPIRED")

        user = await self.user_repo.get_by_id(tok.user_id)
        if not user or user.account_status in ("SUSPENDED", "DISABLED"):
            raise DomainException("Account is suspended or disabled", code="AUTH_ACCOUNT_SUSPENDED")

        # 3. Update password credential
        new_password_hash = PasswordHasher.hash_password(new_password)
        await self.cred_repo.update_password(user.id, new_password_hash)

        # 4. Consume token
        await self.token_repo.consume_reset_token(tok.id)

        # 5. Revoke ALL active user sessions (Security requirement!)
        await self.session_repo.revoke_all_user_sessions(user.id, reason="PASSWORD_RESET")

        # 6. Audit log
        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.password_reset_success",
            resource_type="User",
            resource_id=user.id,
        )
        self.db.add(audit)
        await self.db.commit()

        return {"message": "Password reset successfully. All active sessions have been revoked."}
