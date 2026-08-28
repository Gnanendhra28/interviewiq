import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import ResourceNotFoundException
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.knowledge_rag.infrastructure.orm import KnowledgeBaseORM


class ManageKnowledgeBasesUseCase:
    """
    Production Application Service for Organization-Scoped Knowledge Base lifecycle management.
    Enforces tenant boundaries and authorization checks.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_knowledge_base(
        self,
        ctx: AuthorizationContext,
        name: str,
        description: Optional[str] = None,
        job_role_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_bases:create")

        kb = KnowledgeBaseORM(
            organization_id=ctx.organization_id,
            job_role_id=job_role_id,
            name=name.strip(),
            description=description.strip() if description else None,
            status="ACTIVE"
        )
        self.db.add(kb)
        await self.db.flush()

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="knowledge_base.created",
            resource_type="KnowledgeBase",
            resource_id=kb.id,
            metadata_json={"name": kb.name, "job_role_id": str(job_role_id) if job_role_id else None}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[KNOWLEDGE BASE] Created KB '{kb.name}' ({kb.id}) for org {ctx.organization_id}")
        return self._format_kb(kb)

    async def list_knowledge_bases(self, ctx: AuthorizationContext) -> List[Dict[str, Any]]:
        ctx.enforce_permission("knowledge_bases:read")

        res = await self.db.execute(
            select(KnowledgeBaseORM).where(
                KnowledgeBaseORM.organization_id == ctx.organization_id,
                KnowledgeBaseORM.status == "ACTIVE"
            ).order_by(KnowledgeBaseORM.name.asc())
        )
        kbs = res.scalars().all()
        return [self._format_kb(kb) for kb in kbs]

    async def get_knowledge_base(self, ctx: AuthorizationContext, knowledge_base_id: uuid.UUID) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_bases:read")
        kb = await self._get_kb_orm(ctx, knowledge_base_id)
        return self._format_kb(kb)

    async def update_knowledge_base(
        self,
        ctx: AuthorizationContext,
        knowledge_base_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_bases:update")
        kb = await self._get_kb_orm(ctx, knowledge_base_id)

        if name is not None:
            kb.name = name.strip()
        if description is not None:
            kb.description = description.strip()
        if status is not None:
            kb.status = status.upper()

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="knowledge_base.updated",
            resource_type="KnowledgeBase",
            resource_id=kb.id,
            metadata_json={"name": kb.name, "status": kb.status}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[KNOWLEDGE BASE] Updated KB {kb.id}")
        return self._format_kb(kb)

    async def archive_knowledge_base(self, ctx: AuthorizationContext, knowledge_base_id: uuid.UUID) -> Dict[str, Any]:
        ctx.enforce_permission("knowledge_bases:delete")
        kb = await self._get_kb_orm(ctx, knowledge_base_id)

        kb.status = "ARCHIVED"

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="knowledge_base.archived",
            resource_type="KnowledgeBase",
            resource_id=kb.id,
            metadata_json={"name": kb.name}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[KNOWLEDGE BASE] Archived KB {kb.id}")
        return {"status": "ARCHIVED", "id": str(kb.id)}

    async def _get_kb_orm(self, ctx: AuthorizationContext, knowledge_base_id: uuid.UUID) -> KnowledgeBaseORM:
        res = await self.db.execute(
            select(KnowledgeBaseORM).where(
                KnowledgeBaseORM.id == knowledge_base_id,
                KnowledgeBaseORM.organization_id == ctx.organization_id
            )
        )
        kb = res.scalar_one_or_none()
        if not kb:
            raise ResourceNotFoundException("KnowledgeBase", knowledge_base_id)
        return kb

    def _format_kb(self, kb: KnowledgeBaseORM) -> Dict[str, Any]:
        return {
            "id": str(kb.id),
            "organization_id": str(kb.organization_id),
            "job_role_id": str(kb.job_role_id) if kb.job_role_id else None,
            "name": kb.name,
            "description": kb.description,
            "status": kb.status,
            "created_at": kb.created_at.isoformat(),
            "updated_at": kb.updated_at.isoformat()
        }
