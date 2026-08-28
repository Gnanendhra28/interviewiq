import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.identity.domain.token_generator import hash_token
from apps.api.app.modules.identity.infrastructure.repositories import SessionRepository


class LogoutUseCase:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = SessionRepository(db)

    async def logout_current_session(self, raw_refresh_token: str, user_id: uuid.UUID) -> None:
        if raw_refresh_token:
            provided_hash = hash_token(raw_refresh_token)
            sess = await self.session_repo.get_by_token_hash(provided_hash)
            if sess and sess.user_id == user_id:
                await self.session_repo.revoke_session(sess.id, reason="LOGOUT")

        audit = AuditLogORM(
            actor_user_id=user_id,
            actor_type="USER",
            action="auth.logout",
            resource_type="User",
            resource_id=user_id,
        )
        self.db.add(audit)
        await self.db.commit()

    async def logout_all_sessions(self, user_id: uuid.UUID) -> None:
        await self.session_repo.revoke_all_user_sessions(user_id, reason="LOGOUT_ALL")

        audit = AuditLogORM(
            actor_user_id=user_id,
            actor_type="USER",
            action="auth.logout_all",
            resource_type="User",
            resource_id=user_id,
        )
        self.db.add(audit)
        await self.db.commit()
