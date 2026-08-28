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
    TokenRepository,
    UserRepository,
)


class RegisterUseCase:
    def __init__(self, db: AsyncSession, email_provider: Optional[EmailProvider] = None):
        self.db = db
        self.user_repo = UserRepository(db)
        self.cred_repo = CredentialRepository(db)
        self.token_repo = TokenRepository(db)
        self.email_provider = email_provider or default_email_provider

    async def execute(self, email: str, password: str, is_candidate_self_registration: bool = False) -> Dict[str, Any]:
        normalized_email = email.strip().lower()

        # 1. Check account uniqueness safely
        existing_user = await self.user_repo.get_by_email(normalized_email)
        if existing_user:
            raise DomainException("User with this email already exists", code="AUTH_EMAIL_ALREADY_EXISTS")

        # 2. Validate password policy
        default_password_policy.validate(password)

        # 3. Create user (ACTIVE)
        user = await self.user_repo.create(email=normalized_email, account_status="ACTIVE")

        # 4. Hash password with Argon2id & create credential
        password_hash = PasswordHasher.hash_password(password)
        await self.cred_repo.create(user_id=user.id, password_hash=password_hash, algo="argon2id")

        # 5. Provision default organization & recruiter membership
        from apps.api.app.core.authorization.context import AuthorizationService
        auth_service = AuthorizationService(self.db)
        await auth_service.provision_default_organization(user)

        # 6. Generate and persist one-time verification token
        raw_token = generate_opaque_token()
        token_hash_val = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await self.token_repo.create_verification_token(user_id=user.id, token_hash=token_hash_val, expires_at=expires_at)

        # 6. Dispatch email delivery
        await self.email_provider.send_verification_email(to_email=user.email, raw_token=raw_token)

        # 7. Audit log (Secrets omitted!)
        audit = AuditLogORM(
            actor_user_id=user.id,
            actor_type="USER",
            action="auth.register",
            resource_type="User",
            resource_id=user.id,
            metadata_json={"email": user.email, "account_status": user.account_status},
        )
        self.db.add(audit)
        await self.db.commit()

        return {
            "id": str(user.id),
            "email": user.email,
            "account_status": user.account_status,
            "message": "User registered successfully. Verification email sent.",
        }
