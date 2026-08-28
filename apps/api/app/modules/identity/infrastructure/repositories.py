import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.modules.identity.infrastructure.orm import (
    EmailVerificationTokenORM,
    PasswordCredentialORM,
    PasswordResetTokenORM,
    UserORM,
    UserSessionORM,
)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserORM]:
        result = await self.session.execute(select(UserORM).where(UserORM.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserORM]:
        normalized = email.strip().lower()
        result = await self.session.execute(select(UserORM).where(UserORM.email == normalized))
        return result.scalar_one_or_none()

    async def create(self, email: str, account_status: str = "ACTIVE", is_super_admin: bool = False) -> UserORM:
        user = UserORM(
            email=email.strip().lower(),
            account_status=account_status,
            is_super_admin=is_super_admin,
        )
        self.session.add(user)
        await self.session.flush()
        return user


class CredentialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[PasswordCredentialORM]:
        result = await self.session.execute(select(PasswordCredentialORM).where(PasswordCredentialORM.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user_id: uuid.UUID, password_hash: str, algo: str = "argon2id") -> PasswordCredentialORM:
        cred = PasswordCredentialORM(
            user_id=user_id,
            password_hash=password_hash,
            password_algo=algo,
        )
        self.session.add(cred)
        await self.session.flush()
        return cred

    async def update_password(self, user_id: uuid.UUID, password_hash: str) -> None:
        await self.session.execute(
            update(PasswordCredentialORM)
            .where(PasswordCredentialORM.user_id == user_id)
            .values(password_hash=password_hash, updated_at=datetime.now(timezone.utc))
        )


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> UserSessionORM:
        sess = UserSessionORM(
            user_id=user_id,
            family_id=family_id,
            current_token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
        )
        self.session.add(sess)
        await self.session.flush()
        return sess

    async def get_by_token_hash(self, token_hash: str) -> Optional[UserSessionORM]:
        result = await self.session.execute(select(UserSessionORM).where(UserSessionORM.current_token_hash == token_hash))
        return result.scalar_one_or_none()

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[UserSessionORM]:
        result = await self.session.execute(select(UserSessionORM).where(UserSessionORM.id == session_id))
        return result.scalar_one_or_none()

    async def get_active_sessions_by_user(self, user_id: uuid.UUID) -> List[UserSessionORM]:
        result = await self.session.execute(
            select(UserSessionORM)
            .where(UserSessionORM.user_id == user_id, UserSessionORM.is_revoked == False)
            .order_by(UserSessionORM.last_refreshed_at.desc())
        )
        return list(result.scalars().all())

    async def update_token_rotation(self, session_id: uuid.UUID, new_token_hash: str, new_expires_at: datetime) -> None:
        await self.session.execute(
            update(UserSessionORM)
            .where(UserSessionORM.id == session_id)
            .values(
                current_token_hash=new_token_hash,
                expires_at=new_expires_at,
                last_refreshed_at=datetime.now(timezone.utc),
            )
        )

    async def revoke_session(self, session_id: uuid.UUID, reason: str = "LOGOUT") -> None:
        await self.session.execute(
            update(UserSessionORM)
            .where(UserSessionORM.id == session_id)
            .values(is_revoked=True, revoked_reason=reason, updated_at=datetime.now(timezone.utc))
        )

    async def revoke_all_user_sessions(self, user_id: uuid.UUID, reason: str = "LOGOUT_ALL") -> None:
        await self.session.execute(
            update(UserSessionORM)
            .where(UserSessionORM.user_id == user_id, UserSessionORM.is_revoked == False)
            .values(is_revoked=True, revoked_reason=reason, updated_at=datetime.now(timezone.utc))
        )

    async def revoke_family(self, family_id: uuid.UUID, reason: str = "REUSE_DETECTED") -> None:
        await self.session.execute(
            update(UserSessionORM)
            .where(UserSessionORM.family_id == family_id)
            .values(is_revoked=True, revoked_reason=reason, updated_at=datetime.now(timezone.utc))
        )


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_verification_token(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> EmailVerificationTokenORM:
        tok = EmailVerificationTokenORM(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(tok)
        await self.session.flush()
        return tok

    async def get_verification_token(self, token_hash: str) -> Optional[EmailVerificationTokenORM]:
        result = await self.session.execute(select(EmailVerificationTokenORM).where(EmailVerificationTokenORM.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def consume_verification_token(self, token_id: uuid.UUID) -> None:
        await self.session.execute(
            update(EmailVerificationTokenORM)
            .where(EmailVerificationTokenORM.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )

    async def create_reset_token(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> PasswordResetTokenORM:
        tok = PasswordResetTokenORM(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(tok)
        await self.session.flush()
        return tok

    async def get_reset_token(self, token_hash: str) -> Optional[PasswordResetTokenORM]:
        result = await self.session.execute(select(PasswordResetTokenORM).where(PasswordResetTokenORM.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def consume_reset_token(self, token_id: uuid.UUID) -> None:
        await self.session.execute(
            update(PasswordResetTokenORM)
            .where(PasswordResetTokenORM.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
