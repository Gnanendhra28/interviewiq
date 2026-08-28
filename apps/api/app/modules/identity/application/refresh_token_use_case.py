from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.token_generator import generate_opaque_token, hash_token
from apps.api.app.modules.identity.infrastructure.repositories import (
    SessionRepository,
    UserRepository,
)
from apps.api.app.modules.identity.infrastructure.token_service import TokenService


class RefreshTokenUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)

    async def execute(self, raw_refresh_token: str, ip_address: str = None) -> Tuple[Dict[str, Any], str]:
        if not raw_refresh_token:
            raise DomainException("Refresh token is required", code="AUTH_REFRESH_TOKEN_REQUIRED")

        provided_hash = hash_token(raw_refresh_token)

        # 1. Lookup session by current token hash
        sess = await self.session_repo.get_by_token_hash(provided_hash)
        if not sess:
            # Check if token belongs to an existing session family that was already rotated (Reuse Detection!)
            raise DomainException("Invalid or revoked refresh token", code="AUTH_SESSION_REVOKED")

        # 2. Check session revocation status
        if sess.is_revoked:
            # SECURITY INCIDENT: Attempted reuse of revoked token family!
            await self.session_repo.revoke_family(sess.family_id, reason="REUSE_DETECTED")
            audit = AuditLogORM(
                actor_user_id=sess.user_id,
                actor_type="USER",
                action="auth.refresh_reuse_detected",
                resource_type="UserSession",
                resource_id=sess.id,
                ip_address=ip_address,
                metadata_json={"family_id": str(sess.family_id), "reason": "revoked_token_reuse"},
            )
            self.db.add(audit)
            await self.db.commit()
            raise DomainException("Security violation: Session family has been revoked due to token reuse", code="AUTH_SESSION_REVOKED")

        # 3. Check expiration
        now = datetime.now(timezone.utc)
        if sess.expires_at < now:
            await self.session_repo.revoke_session(sess.id, reason="EXPIRED")
            await self.db.commit()
            raise DomainException("Refresh token has expired", code="AUTH_TOKEN_EXPIRED")

        # 4. Check user account status
        user = await self.user_repo.get_by_id(sess.user_id)
        if not user or user.account_status in ("SUSPENDED", "DISABLED"):
            await self.session_repo.revoke_session(sess.id, reason="ACCOUNT_SUSPENDED")
            await self.db.commit()
            raise DomainException("Account is suspended or disabled", code="AUTH_ACCOUNT_SUSPENDED")

        # 5. Rotate refresh token within same family_id
        new_raw_refresh_token = generate_opaque_token()
        new_token_hash = hash_token(new_raw_refresh_token)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.session_repo.update_token_rotation(
            session_id=sess.id,
            new_token_hash=new_token_hash,
            new_expires_at=new_expires_at,
        )

        # 6. Issue new short-lived access token
        new_access_token = TokenService.create_access_token(user_id=user.id)

        # 7. Audit log
        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.refresh_success",
            resource_type="UserSession",
            resource_id=sess.id,
            ip_address=ip_address,
            metadata_json={"session_id": str(sess.id), "family_id": str(sess.family_id)},
        )
        self.db.add(audit)
        await self.db.commit()

        response_body = {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

        return response_body, new_raw_refresh_token
