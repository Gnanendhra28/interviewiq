import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import (
    DomainException,
    ForbiddenException,
    ResourceNotFoundException,
)
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateProfileORM,
    CandidateSkillORM,
)
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewBlueprintORM,
    InterviewSessionORM,
    InterviewSessionStatus,
    InterviewSnapshotORM,
    InterviewStateHistoryORM,
    InterviewTurnORM,
)
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM, JobRoleRequirementORM
from apps.api.app.modules.knowledge_rag.infrastructure.orm import (
    KnowledgeDocumentORM,
    KnowledgeDocumentVersionORM,
)
from apps.api.app.modules.resumes.infrastructure.orm import ResumeAnalysisORM

VALID_TRANSITIONS = {
    InterviewSessionStatus.CREATED: {InterviewSessionStatus.RESUME_PENDING, InterviewSessionStatus.PROFILE_READY, InterviewSessionStatus.READY, InterviewSessionStatus.CANCELLED, InterviewSessionStatus.FAILED},
    InterviewSessionStatus.RESUME_PENDING: {InterviewSessionStatus.RESUME_PROCESSING, InterviewSessionStatus.CANCELLED, InterviewSessionStatus.FAILED},
    InterviewSessionStatus.RESUME_PROCESSING: {InterviewSessionStatus.PROFILE_READY, InterviewSessionStatus.FAILED, InterviewSessionStatus.CANCELLED},
    InterviewSessionStatus.PROFILE_READY: {InterviewSessionStatus.READY, InterviewSessionStatus.CANCELLED, InterviewSessionStatus.FAILED},
    InterviewSessionStatus.READY: {InterviewSessionStatus.IN_PROGRESS, InterviewSessionStatus.CANCELLED, InterviewSessionStatus.EXPIRED, InterviewSessionStatus.FAILED},
    InterviewSessionStatus.IN_PROGRESS: {InterviewSessionStatus.PAUSED, InterviewSessionStatus.COMPLETING, InterviewSessionStatus.CANCELLED, InterviewSessionStatus.EXPIRED, InterviewSessionStatus.FAILED},
    InterviewSessionStatus.PAUSED: {InterviewSessionStatus.IN_PROGRESS, InterviewSessionStatus.CANCELLED, InterviewSessionStatus.EXPIRED, InterviewSessionStatus.FAILED},
    InterviewSessionStatus.COMPLETING: {InterviewSessionStatus.COMPLETED, InterviewSessionStatus.FAILED},
}


class ManageInterviewsUseCase:
    """
    Production Application Service for Interview Orchestration, Snapshot Freezing (ADR 027),
    Blueprint Generation (ADR 028), Turn Initialization (ADR 029), and Backend-Controlled State Machine Transitions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_interview(
        self,
        ctx: AuthorizationContext,
        candidate_profile_id: uuid.UUID,
        job_role_id: uuid.UUID,
        knowledge_base_ids: Optional[List[uuid.UUID]] = None,
        resume_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        ctx.enforce_permission("interviews:create")
        org_id = ctx.organization_id

        # 1. Validate Candidate Profile
        cand_res = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.id == candidate_profile_id,
                CandidateProfileORM.organization_id == org_id,
                CandidateProfileORM.status == "ACTIVE"
            )
        )
        cand = cand_res.scalar_one_or_none()
        if not cand:
            raise ResourceNotFoundException("CandidateProfile", candidate_profile_id)

        # 2. Validate Job Role
        role_res = await self.db.execute(
            select(JobRoleORM).where(
                JobRoleORM.id == job_role_id,
                (JobRoleORM.organization_id == org_id) | (JobRoleORM.organization_id.is_(None)),
                JobRoleORM.is_active_version.is_(True)
            )
        )
        role = role_res.scalar_one_or_none()
        if not role:
            raise ResourceNotFoundException("JobRole", job_role_id)

        # 3. Create Session
        session = InterviewSessionORM(
            organization_id=org_id,
            candidate_profile_id=cand.id,
            job_role_id=role.id,
            job_role_version=role.version_number,
            resume_id=resume_id,
            status=InterviewSessionStatus.CREATED,
            version_number=1
        )
        self.db.add(session)
        await self.db.flush()

        # Record Initial State History
        history = InterviewStateHistoryORM(
            interview_session_id=session.id,
            previous_status="NONE",
            new_status=InterviewSessionStatus.CREATED.value,
            transition_reason="Interview session created by recruiter",
            actor_type="USER",
            actor_id=ctx.user_id
        )
        self.db.add(history)

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="interview.created",
            resource_type="InterviewSession",
            resource_id=session.id,
            metadata_json={"candidate_id": str(cand.id), "job_role_id": str(role.id)}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[INTERVIEW] Created interview session {session.id} for candidate {cand.id}")
        return await self.get_interview(ctx, session.id)

    async def prepare_interview(
        self,
        ctx: AuthorizationContext,
        interview_id: uuid.UUID,
        knowledge_base_ids: Optional[List[uuid.UUID]] = None
    ) -> Dict[str, Any]:
        """
        Prepares interview session by freezing immutable InterviewSnapshotORM and InterviewBlueprintORM,
        then transitioning status to READY.
        """
        ctx.enforce_permission("interviews:manage")
        session = await self._get_session_orm(ctx, interview_id)

        if session.status not in (InterviewSessionStatus.CREATED, InterviewSessionStatus.PROFILE_READY):
            raise DomainException(f"Cannot prepare interview in status {session.status.value}", code="INVALID_STATE_TRANSITION")

        org_id = ctx.organization_id

        # 1. Fetch Candidate Snapshot Data
        cand = (await self.db.execute(
            select(CandidateProfileORM).where(CandidateProfileORM.id == session.candidate_profile_id)
        )).scalar_one()
        cand_skills = (await self.db.execute(
            select(CandidateSkillORM).where(CandidateSkillORM.candidate_profile_id == cand.id)
        )).scalars().all()

        cand_snapshot_json = {
            "first_name": cand.first_name,
            "last_name": cand.last_name,
            "email": cand.email,
            "headline": cand.headline,
            "summary": cand.summary,
            "skills": [{"skill_name": s.skill_name, "proficiency": s.proficiency_level, "source": s.source} for s in cand_skills]
        }

        # 2. Fetch Resume Analysis (if available)
        resume_analysis_id = None
        resume_analysis_version = None
        if session.resume_id:
            res_ana = (await self.db.execute(
                select(ResumeAnalysisORM).where(
                    ResumeAnalysisORM.resume_id == session.resume_id,
                    ResumeAnalysisORM.analysis_version == "v1"
                )
            )).scalar_one_or_none()
            if res_ana:
                resume_analysis_id = res_ana.id
                resume_analysis_version = res_ana.analysis_version

        # 3. Fetch Job Role Requirements
        role = (await self.db.execute(
            select(JobRoleORM).where(JobRoleORM.id == session.job_role_id)
        )).scalar_one()
        reqs = (await self.db.execute(
            select(JobRoleRequirementORM).where(JobRoleRequirementORM.job_role_id == role.id)
        )).scalars().all()

        role_reqs_json = [
            {
                "id": str(r.id),
                "skill_name": r.skill_name,
                "is_required": r.is_required,
                "target_proficiency": r.target_proficiency,
                "weight": float(r.weight)
            } for r in reqs
        ]

        # 4. Resolve Knowledge Base Document Version IDs
        kb_uuids = knowledge_base_ids or []
        doc_version_uuids = []

        if kb_uuids:
            doc_vers = (await self.db.execute(
                select(KnowledgeDocumentVersionORM)
                .join(KnowledgeDocumentORM, KnowledgeDocumentVersionORM.document_id == KnowledgeDocumentORM.id)
                .where(
                    KnowledgeDocumentORM.knowledge_base_id.in_(kb_uuids),
                    KnowledgeDocumentORM.ingestion_status == "READY",
                    KnowledgeDocumentVersionORM.is_active_version.is_(True)
                )
            )).scalars().all()
            doc_version_uuids = [str(v.id) for v in doc_vers]

        # 5. Create Immutable Interview Snapshot (ADR 027)
        snapshot = InterviewSnapshotORM(
            interview_session_id=session.id,
            organization_id=org_id,
            candidate_profile_id=cand.id,
            candidate_snapshot_json=cand_snapshot_json,
            resume_id=session.resume_id,
            resume_version=1 if session.resume_id else None,
            resume_analysis_id=resume_analysis_id,
            resume_analysis_version=resume_analysis_version,
            job_role_id=role.id,
            job_role_version=role.version_number,
            job_role_requirements_snapshot_json=role_reqs_json,
            knowledge_base_ids=[str(k) for k in kb_uuids],
            knowledge_document_version_ids=doc_version_uuids,
            embedding_provider=settings.EMBEDDING_PROVIDER,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimension=settings.EMBEDDING_DIMENSION,
            embedding_version=settings.EMBEDDING_VERSION,
            prompt_version="v1",
            ai_provider="gemini",
            ai_model="gemini-2.5-flash",
            snapshot_version=1
        )
        self.db.add(snapshot)

        # 6. Generate & Freeze Interview Blueprint (ADR 028)
        # Compute balanced topic weights based on job requirements & candidate skills
        topic_weights = []
        if reqs:
            total_weight = sum(float(r.weight) for r in reqs) or 1.0
            for r in reqs:
                normalized_w = round(float(r.weight) / total_weight, 2)
                target_q = max(1, int(normalized_w * 10))
                topic_weights.append({
                    "topic": r.skill_name,
                    "weight": normalized_w,
                    "target_questions": target_q
                })
        else:
            topic_weights = [{"topic": "General Technical Competency", "weight": 1.0, "target_questions": 10}]

        blueprint = InterviewBlueprintORM(
            interview_session_id=session.id,
            total_target_questions=10,
            estimated_duration_minutes=45,
            topic_weights_json=topic_weights,
            difficulty_distribution_json={"EASY": 2, "MEDIUM": 5, "HARD": 3},
            required_skills=[r.skill_name for r in reqs if r.is_required],
            optional_skills=[r.skill_name for r in reqs if not r.is_required],
            resume_focus_areas=[s.skill_name for s in cand_skills],
            rag_grounding_required=len(doc_version_uuids) > 0
        )
        self.db.add(blueprint)

        # 7. Transition Status to READY
        old_status = session.status.value
        session.status = InterviewSessionStatus.READY
        session.version_number += 1

        history = InterviewStateHistoryORM(
            interview_session_id=session.id,
            previous_status=old_status,
            new_status=InterviewSessionStatus.READY.value,
            transition_reason="Snapshot frozen and interview blueprint generated",
            actor_type="USER",
            actor_id=ctx.user_id
        )
        self.db.add(history)

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="interview.prepared",
            resource_type="InterviewSession",
            resource_id=session.id,
            metadata_json={"snapshot_id": str(snapshot.id), "blueprint_id": str(blueprint.id)}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[INTERVIEW] Prepared interview session {session.id} (Status READY)")
        return await self.get_interview(ctx, session.id)

    async def start_interview(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        """
        Starts interview session, transitions status to IN_PROGRESS, and initializes Turn 1 (ADR 029).
        """
        session = await self._get_session_orm(ctx, interview_id)

        # Verify candidate or recruiter access
        if ctx.candidate_profile and ctx.candidate_profile.id != session.candidate_profile_id:
            raise ForbiddenException("Candidate can only start their own interview session")
        elif not ctx.candidate_profile:
            ctx.enforce_permission("interviews:manage")

        if session.status != InterviewSessionStatus.READY:
            raise DomainException(f"Cannot start interview in status {session.status.value}", code="INVALID_STATE_TRANSITION")

        now = datetime.now(timezone.utc)
        old_status = session.status.value

        session.status = InterviewSessionStatus.IN_PROGRESS
        session.started_at = now
        session.last_activity_at = now
        session.max_duration_deadline = now + timedelta(minutes=60)
        session.version_number += 1

        # Initialize Turn 1 (ADR 029)
        turn_1 = InterviewTurnORM(
            interview_session_id=session.id,
            turn_number=1,
            turn_status="PENDING",
            idempotency_key=f"turn_{session.id}_1"
        )
        self.db.add(turn_1)

        history = InterviewStateHistoryORM(
            interview_session_id=session.id,
            previous_status=old_status,
            new_status=InterviewSessionStatus.IN_PROGRESS.value,
            transition_reason="Candidate started interview session",
            actor_type="CANDIDATE" if ctx.candidate_profile else "USER",
            actor_id=ctx.user_id
        )
        self.db.add(history)

        audit = AuditLogORM(
            organization_id=session.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="interview.started",
            resource_type="InterviewSession",
            resource_id=session.id,
            metadata_json={"started_at": now.isoformat()}
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[INTERVIEW] Started interview session {session.id} (Turn 1 initialized)")
        return await self.get_interview(ctx, session.id)

    async def pause_interview(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        return await self._transition_status(
            ctx, interview_id, target_status=InterviewSessionStatus.PAUSED, reason="Interview paused by candidate/recruiter"
        )

    async def resume_interview(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        return await self._transition_status(
            ctx, interview_id, target_status=InterviewSessionStatus.IN_PROGRESS, reason="Interview resumed"
        )

    async def cancel_interview(self, ctx: AuthorizationContext, interview_id: uuid.UUID, cancellation_reason: str) -> Dict[str, Any]:
        ctx.enforce_permission("interviews:manage")
        session = await self._get_session_orm(ctx, interview_id)
        session.cancellation_reason = cancellation_reason.strip()
        return await self._transition_status(
            ctx, interview_id, target_status=InterviewSessionStatus.CANCELLED, reason=cancellation_reason
        )

    async def get_interview(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        session = await self._get_session_orm(ctx, interview_id)
        
        # Load snapshot & blueprint
        snap_res = await self.db.execute(select(InterviewSnapshotORM).where(InterviewSnapshotORM.interview_session_id == session.id))
        snapshot = snap_res.scalar_one_or_none()

        blue_res = await self.db.execute(select(InterviewBlueprintORM).where(InterviewBlueprintORM.interview_session_id == session.id))
        blueprint = blue_res.scalar_one_or_none()

        # Load active turn
        turns_res = await self.db.execute(
            select(InterviewTurnORM).where(InterviewTurnORM.interview_session_id == session.id).order_by(InterviewTurnORM.turn_number.desc())
        )
        turns = turns_res.scalars().all()

        return {
            "id": str(session.id),
            "organization_id": str(session.organization_id),
            "candidate_profile_id": str(session.candidate_profile_id),
            "job_role_id": str(session.job_role_id),
            "job_role_version": session.job_role_version,
            "resume_id": str(session.resume_id) if session.resume_id else None,
            "status": session.status.value,
            "version_number": session.version_number,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None,
            "paused_at": session.paused_at.isoformat() if session.paused_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "has_snapshot": snapshot is not None,
            "has_blueprint": blueprint is not None,
            "total_turns": len(turns),
            "current_turn_number": turns[0].turn_number if turns else 0,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }

    async def list_interviews(
        self,
        ctx: AuthorizationContext,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        ctx.enforce_permission("interviews:read")
        cond = [InterviewSessionORM.organization_id == ctx.organization_id]
        if status_filter:
            cond.append(InterviewSessionORM.status == InterviewSessionStatus(status_filter.upper()))

        res = await self.db.execute(
            select(InterviewSessionORM).where(*cond).order_by(InterviewSessionORM.created_at.desc())
        )
        sessions = res.scalars().all()
        return [{"id": str(s.id), "status": s.status.value, "created_at": s.created_at.isoformat()} for s in sessions]

    async def _transition_status(
        self,
        ctx: AuthorizationContext,
        interview_id: uuid.UUID,
        target_status: InterviewSessionStatus,
        reason: str
    ) -> Dict[str, Any]:
        session = await self._get_session_orm(ctx, interview_id)
        current_status = session.status

        allowed_targets = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_targets:
            raise DomainException(
                f"Cannot transition interview session from {current_status.value} to {target_status.value}",
                code="INVALID_STATE_TRANSITION"
            )

        now = datetime.now(timezone.utc)
        session.status = target_status
        session.last_activity_at = now
        session.version_number += 1

        if target_status == InterviewSessionStatus.PAUSED:
            session.paused_at = now
        elif target_status == InterviewSessionStatus.COMPLETED:
            session.completed_at = now

        history = InterviewStateHistoryORM(
            interview_session_id=session.id,
            previous_status=current_status.value,
            new_status=target_status.value,
            transition_reason=reason,
            actor_type="CANDIDATE" if ctx.candidate_profile else "USER",
            actor_id=ctx.user_id
        )
        self.db.add(history)
        await self.db.commit()

        logger.info(f"[INTERVIEW] Transitioned session {session.id}: {current_status.value} -> {target_status.value}")
        return await self.get_interview(ctx, session.id)

    async def _get_session_orm(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> InterviewSessionORM:
        res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        session = res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)
        return session
