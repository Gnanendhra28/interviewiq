from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.token_generator import generate_opaque_token, hash_token
from apps.api.app.modules.identity.infrastructure.email_provider import (
    EmailProvider,
    default_email_provider,
)
from apps.api.app.modules.identity.infrastructure.repositories import (
    TokenRepository,
    UserRepository,
)


class EmailVerificationUseCase:
    def __init__(self, db: AsyncSession, email_provider: Optional[EmailProvider] = None):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = TokenRepository(db)
        self.email_provider = email_provider or default_email_provider

    async def request_verification(self, email: str) -> Dict[str, Any]:
        normalized_email = email.strip().lower()
        user = await self.user_repo.get_by_email(normalized_email)
        
        # Generic response to prevent email enumeration
        generic_msg = "If an account exists for this email, a verification link has been sent."
        if not user or user.account_status != "PENDING_VERIFICATION":
            return {"message": generic_msg}

        raw_token = generate_opaque_token()
        token_hash_val = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await self.token_repo.create_verification_token(user_id=user.id, token_hash=token_hash_val, expires_at=expires_at)

        await self.email_provider.send_verification_email(to_email=user.email, raw_token=raw_token)

        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.email_verification_requested",
            resource_type="User",
            resource_id=user.id,
        )
        self.db.add(audit)
        await self.db.commit()

        return {"message": generic_msg}

    async def confirm_verification(self, raw_token: str) -> Dict[str, Any]:
        if not raw_token:
            raise DomainException("Verification token is required", code="AUTH_TOKEN_INVALID")

        provided_hash = hash_token(raw_token)
        tok = await self.token_repo.get_verification_token(provided_hash)
        if not tok or tok.used_at or tok.invalidated_at:
            raise DomainException("Verification token is invalid or already used", code="AUTH_TOKEN_INVALID")

        if tok.expires_at < datetime.now(timezone.utc):
            raise DomainException("Verification token has expired", code="AUTH_TOKEN_EXPIRED")

        # Update user status
        user = await self.user_repo.get_by_id(tok.user_id)
        if not user:
            raise DomainException("Associated user not found", code="AUTH_USER_NOT_FOUND")

        now = datetime.now(timezone.utc)
        user.account_status = "ACTIVE"
        user.email_verified_at = now
        await self.token_repo.consume_verification_token(tok.id)

        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.email_verification_success",
            resource_type="User",
            resource_id=user.id,
        )
        self.db.add(audit)
        await self.db.commit()

        return {"message": "Email successfully verified. You can now log in.", "account_status": "ACTIVE"}
