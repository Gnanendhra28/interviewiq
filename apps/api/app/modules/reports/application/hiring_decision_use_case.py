import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import (
    ForbiddenException,
    ResourceNotFoundException,
)
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.interviews.infrastructure.orm import InterviewSessionORM
from apps.api.app.modules.reports.infrastructure.orm import (
    HiringDecisionHistoryORM,
    HiringDecisionORM,
    HiringDecisionStatus,
)


class HiringDecisionUseCase:
    """
    Production Application Service for Human Hiring Decision Management (ADR 039)
    and Immutable Append-Only Decision History Tracking (ADR 040).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_hiring_decision(
        self,
        ctx: AuthorizationContext,
        interview_id: uuid.UUID,
        status: HiringDecisionStatus,
        rationale_text: Optional[str] = None
    ) -> Dict[str, Any]:
        # Enforce Recruiter / Admin Role Authority (Candidate Denial)
        if ctx.candidate_profile and not ctx.user.is_super_admin:
            raise ForbiddenException("Candidates cannot record human hiring decisions.")

        org_id = ctx.organization_id

        # 1. Verify Interview Session
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == org_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        now = datetime.now(timezone.utc)

        # 2. Check Existing Hiring Decision
        existing_res = await self.db.execute(
            select(HiringDecisionORM).where(HiringDecisionORM.interview_session_id == session.id)
        )
        existing_decision = existing_res.scalar_one_or_none()
        previous_status = existing_decision.status.value if existing_decision else "PENDING_REVIEW"

        if existing_decision:
            existing_decision.status = status
            existing_decision.decision_maker_user_id = ctx.user_id
            existing_decision.rationale_text = rationale_text
            existing_decision.updated_at = now
            active_decision = existing_decision
        else:
            active_decision = HiringDecisionORM(
                organization_id=org_id,
                interview_session_id=session.id,
                candidate_profile_id=session.candidate_profile_id,
                status=status,
                decision_maker_user_id=ctx.user_id,
                rationale_text=rationale_text
            )
            self.db.add(active_decision)

        # 3. Create Immutable Append-Only Hiring Decision History (ADR 040)
        history_record = HiringDecisionHistoryORM(
            organization_id=org_id,
            interview_session_id=session.id,
            previous_status=previous_status,
            new_status=status.value,
            actor_user_id=ctx.user_id,
            rationale_text=rationale_text
        )
        self.db.add(history_record)

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="interview.human_decision_recorded",
            resource_type="HiringDecision",
            resource_id=active_decision.id if active_decision.id else session.id,
            metadata_json={"previous_status": previous_status, "new_status": status.value, "interview_id": str(session.id)}
        )
        self.db.add(audit)

        await self.db.commit()
        logger.info(f"[HIRING DECISION] Recorded human decision {status.value} for session {session.id} by user {ctx.user_id}")
        return self._format_decision(active_decision)

    async def get_hiring_decision(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        if ctx.candidate_profile and not ctx.user.is_super_admin:
            raise ForbiddenException("Candidates cannot view recruiter hiring decisions.")

        dec_res = await self.db.execute(
            select(HiringDecisionORM).where(
                HiringDecisionORM.interview_session_id == interview_id,
                HiringDecisionORM.organization_id == ctx.organization_id
            )
        )
        dec = dec_res.scalar_one_or_none()
        if not dec:
            return {
                "interview_session_id": str(interview_id),
                "status": "PENDING_REVIEW",
                "message": "No human hiring decision recorded yet."
            }
        return self._format_decision(dec)

    async def get_hiring_decision_history(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> List[Dict[str, Any]]:
        if ctx.candidate_profile and not ctx.user.is_super_admin:
            raise ForbiddenException("Candidates cannot view decision audit history.")

        hist_res = await self.db.execute(
            select(HiringDecisionHistoryORM)
            .where(
                HiringDecisionHistoryORM.interview_session_id == interview_id,
                HiringDecisionHistoryORM.organization_id == ctx.organization_id
            )
            .order_by(desc(HiringDecisionHistoryORM.created_at))
        )
        history = hist_res.scalars().all()
        return [
            {
                "id": str(h.id),
                "interview_session_id": str(h.interview_session_id),
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "actor_user_id": str(h.actor_user_id),
                "rationale_text": h.rationale_text,
                "created_at": h.created_at.isoformat()
            } for h in history
        ]

    def _format_decision(self, decision: HiringDecisionORM) -> Dict[str, Any]:
        return {
            "id": str(decision.id) if decision.id else None,
            "interview_session_id": str(decision.interview_session_id),
            "candidate_profile_id": str(decision.candidate_profile_id),
            "status": decision.status.value if hasattr(decision.status, "value") else decision.status,
            "decision_maker_user_id": str(decision.decision_maker_user_id),
            "rationale_text": decision.rationale_text,
            "created_at": decision.created_at.isoformat() if decision.created_at else None,
            "updated_at": decision.updated_at.isoformat() if decision.updated_at else None
        }
