import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import (
    DomainException,
    ResourceNotFoundException,
)
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.candidates.infrastructure.orm import CandidateProfileORM
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewSessionORM,
)
from apps.api.app.modules.job_roles.infrastructure.orm import JobRoleORM
from apps.api.app.modules.reports.infrastructure.orm import (
    HiringDecisionHistoryORM,
    HiringDecisionORM,
    InterviewReportORM,
)


class RecruiterCommandCenterUseCase:
    """
    Production Application Service for Recruiter Command Center Dashboard Aggregations (ADR 041),
    Pipeline Searching/Filtering, Candidate Timeline, Candidate Comparison, and Review Queue.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(self, ctx: AuthorizationContext) -> Dict[str, Any]:
        org_id = ctx.organization_id

        # 1. Active Job Roles Count
        roles_res = await self.db.execute(
            select(func.count(JobRoleORM.id)).where(
                JobRoleORM.organization_id == org_id,
                JobRoleORM.is_active_version == True
            )
        )
        active_roles = roles_res.scalar() or 0

        # 2. Active Candidates Count
        cands_res = await self.db.execute(
            select(func.count(CandidateProfileORM.id)).where(
                CandidateProfileORM.organization_id == org_id,
                CandidateProfileORM.status == "ACTIVE"
            )
        )
        active_candidates = cands_res.scalar() or 0

        # 3. Interviews Grouped by Status
        int_status_res = await self.db.execute(
            select(InterviewSessionORM.status, func.count(InterviewSessionORM.id))
            .where(InterviewSessionORM.organization_id == org_id)
            .group_by(InterviewSessionORM.status)
        )
        status_counts = {str(status.value): count for status, count in int_status_res.all()}

        # 4. Reports & Decisions Count
        reps_res = await self.db.execute(
            select(func.count(InterviewReportORM.id))
            .join(InterviewSessionORM, InterviewReportORM.interview_session_id == InterviewSessionORM.id)
            .where(InterviewSessionORM.organization_id == org_id)
        )
        completed_reports = reps_res.scalar() or 0

        dec_res = await self.db.execute(
            select(func.count(HiringDecisionORM.id)).where(
                HiringDecisionORM.organization_id == org_id,
                HiringDecisionORM.status == "PENDING_REVIEW"
            )
        )
        pending_reviews = dec_res.scalar() or 0

        # 5. Recent Organization Activity Audit Trail
        audit_res = await self.db.execute(
            select(AuditLogORM)
            .where(AuditLogORM.organization_id == org_id)
            .order_by(desc(AuditLogORM.created_at))
            .limit(10)
        )
        recent_activity = [
            {
                "id": str(a.id),
                "action": a.action,
                "actor_type": a.actor_type,
                "resource_type": a.resource_type,
                "resource_id": str(a.resource_id) if a.resource_id else None,
                "created_at": a.created_at.isoformat()
            } for a in audit_res.scalars().all()
        ]

        return {
            "organization_id": str(org_id),
            "active_job_roles_count": active_roles,
            "active_candidates_count": active_candidates,
            "interviews_by_status": status_counts,
            "completed_reports_count": completed_reports,
            "pending_hiring_reviews_count": pending_reviews,
            "recent_activity": recent_activity
        }

    async def get_candidate_pipeline(
        self,
        ctx: AuthorizationContext,
        job_role_id: Optional[uuid.UUID] = None,
        interview_status: Optional[str] = None,
        hiring_signal: Optional[str] = None,
        human_decision_status: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        org_id = ctx.organization_id
        offset = (page - 1) * limit

        query = (
            select(
                CandidateProfileORM,
                InterviewSessionORM,
                InterviewReportORM,
                HiringDecisionORM
            )
            .outerjoin(InterviewSessionORM, CandidateProfileORM.id == InterviewSessionORM.candidate_profile_id)
            .outerjoin(InterviewReportORM, InterviewSessionORM.id == InterviewReportORM.interview_session_id)
            .outerjoin(HiringDecisionORM, InterviewSessionORM.id == HiringDecisionORM.interview_session_id)
            .where(CandidateProfileORM.organization_id == org_id)
        )

        if job_role_id:
            query = query.where(InterviewSessionORM.job_role_id == job_role_id)
        if interview_status:
            query = query.where(InterviewSessionORM.status == interview_status)
        if hiring_signal:
            query = query.where(InterviewReportORM.hiring_signal == hiring_signal)
        if human_decision_status:
            query = query.where(HiringDecisionORM.status == human_decision_status)
        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.where(
                or_(
                    CandidateProfileORM.first_name.ilike(pattern),
                    CandidateProfileORM.last_name.ilike(pattern),
                    CandidateProfileORM.email.ilike(pattern)
                )
            )

        query = query.order_by(desc(CandidateProfileORM.created_at)).offset(offset).limit(limit)
        results = (await self.db.execute(query)).all()

        items = []
        for cand, sess, rep, dec in results:
            items.append({
                "candidate_id": str(cand.id),
                "full_name": f"{cand.first_name} {cand.last_name}".strip(),
                "email": cand.email,
                "interview_id": str(sess.id) if sess else None,
                "interview_status": sess.status.value if sess else None,
                "job_role_id": str(sess.job_role_id) if sess else None,
                "latest_score": float(rep.overall_score) if rep else None,
                "hiring_signal": rep.hiring_signal if rep else None,
                "human_decision": dec.status.value if dec else "PENDING_REVIEW",
                "last_activity_at": cand.updated_at.isoformat()
            })

        return {
            "page": page,
            "limit": limit,
            "count": len(items),
            "candidates": items
        }

    async def get_candidate_timeline(self, ctx: AuthorizationContext, candidate_id: uuid.UUID) -> List[Dict[str, Any]]:
        org_id = ctx.organization_id

        cand_res = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.id == candidate_id,
                CandidateProfileORM.organization_id == org_id
            )
        )
        cand = cand_res.scalar_one_or_none()
        if not cand:
            raise ResourceNotFoundException("CandidateProfile", candidate_id)

        timeline_events = [
            {
                "event_type": "candidate.created",
                "description": f"Candidate profile created for {cand.first_name} {cand.last_name}",
                "timestamp": cand.created_at.isoformat()
            }
        ]

        # Ingest audit events for candidate
        audit_res = await self.db.execute(
            select(AuditLogORM)
            .where(
                AuditLogORM.organization_id == org_id,
                or_(
                    AuditLogORM.resource_id == candidate_id,
                    AuditLogORM.metadata_json.contains({"candidate_id": str(candidate_id)})
                )
            )
            .order_by(AuditLogORM.created_at.asc())
        )
        for audit in audit_res.scalars().all():
            timeline_events.append({
                "event_type": audit.action,
                "description": f"Audit Action: {audit.action}",
                "timestamp": audit.created_at.isoformat(),
                "metadata": audit.metadata_json
            })

        # Ingest hiring decision history
        dec_hist_res = await self.db.execute(
            select(HiringDecisionHistoryORM)
            .where(
                HiringDecisionHistoryORM.organization_id == org_id
            )
            .order_by(HiringDecisionHistoryORM.created_at.asc())
        )
        for dh in dec_hist_res.scalars().all():
            timeline_events.append({
                "event_type": "hiring_decision.transition",
                "description": f"Human Hiring Decision changed to {dh.new_status}",
                "timestamp": dh.created_at.isoformat(),
                "rationale": dh.rationale_text
            })

        timeline_events.sort(key=lambda x: x["timestamp"])
        return timeline_events

    async def compare_candidates(self, ctx: AuthorizationContext, candidate_ids: List[uuid.UUID]) -> Dict[str, Any]:
        if not candidate_ids or len(candidate_ids) > 5:
            raise DomainException("Candidate comparison requires between 1 and 5 candidate IDs.", code="INVALID_COMPARISON_COUNT")

        org_id = ctx.organization_id
        comparison_items = []

        for cid in candidate_ids:
            cand_res = await self.db.execute(
                select(CandidateProfileORM).where(
                    CandidateProfileORM.id == cid,
                    CandidateProfileORM.organization_id == org_id
                )
            )
            cand = cand_res.scalar_one_or_none()
            if not cand:
                raise ResourceNotFoundException("CandidateProfile", cid)

            # Resolve latest session and report
            sess_res = await self.db.execute(
                select(InterviewSessionORM).where(InterviewSessionORM.candidate_profile_id == cid).order_by(desc(InterviewSessionORM.created_at))
            )
            sess = sess_res.scalars().first()

            rep = None
            dec = None
            if sess:
                rep_res = await self.db.execute(
                    select(InterviewReportORM).where(InterviewReportORM.interview_session_id == sess.id).order_by(desc(InterviewReportORM.report_version))
                )
                rep = rep_res.scalars().first()

                dec_res = await self.db.execute(select(HiringDecisionORM).where(HiringDecisionORM.interview_session_id == sess.id))
                dec = dec_res.scalar_one_or_none()

            comparison_items.append({
                "candidate_id": str(cand.id),
                "full_name": f"{cand.first_name} {cand.last_name}".strip(),
                "interview_id": str(sess.id) if sess else None,
                "overall_score": float(rep.overall_score) if rep else None,
                "technical_competency_score": float(rep.technical_competency_score) if rep and rep.technical_competency_score else None,
                "reasoning_score": float(rep.reasoning_score) if rep and rep.reasoning_score else None,
                "communication_score": float(rep.communication_score) if rep and rep.communication_score else None,
                "requirement_scorecards": rep.requirement_scorecards_json.get("scorecards", []) if rep and rep.requirement_scorecards_json else [],
                "hiring_signal": rep.hiring_signal if rep else "INSUFFICIENT_EVIDENCE",
                "human_decision": dec.status.value if dec else "PENDING_REVIEW"
            })

        return {
            "comparison_count": len(comparison_items),
            "candidates": comparison_items
        }

    async def get_review_queue(self, ctx: AuthorizationContext) -> Dict[str, Any]:
        org_id = ctx.organization_id

        # 1. Unreviewed Completed Interview Reports
        reports_res = await self.db.execute(
            select(InterviewReportORM, InterviewSessionORM, CandidateProfileORM)
            .join(InterviewSessionORM, InterviewReportORM.interview_session_id == InterviewSessionORM.id)
            .join(CandidateProfileORM, InterviewSessionORM.candidate_profile_id == CandidateProfileORM.id)
            .outerjoin(HiringDecisionORM, InterviewSessionORM.id == HiringDecisionORM.interview_session_id)
            .where(
                InterviewSessionORM.organization_id == org_id,
                or_(HiringDecisionORM.id == None, HiringDecisionORM.status == "PENDING_REVIEW")
            )
            .order_by(desc(InterviewReportORM.created_at))
        )

        unreviewed = [
            {
                "queue_item_type": "REPORT_PENDING_DECISION",
                "resource_type": "InterviewReport",
                "resource_id": str(rep.id),
                "interview_id": str(sess.id),
                "candidate_id": str(cand.id),
                "candidate_name": f"{cand.first_name} {cand.last_name}".strip(),
                "overall_score": float(rep.overall_score),
                "hiring_signal": rep.hiring_signal,
                "priority": "HIGH"
            } for rep, sess, cand in reports_res.all()
        ]

        # 2. Failed Background Processing Jobs
        failed_jobs_res = await self.db.execute(
            select(BackgroundJobORM).where(
                BackgroundJobORM.organization_id == org_id,
                BackgroundJobORM.status == "FAILED"
            )
        )
        failed_items = [
            {
                "queue_item_type": "BACKGROUND_JOB_FAILURE",
                "resource_type": job.resource_type,
                "resource_id": str(job.resource_id),
                "job_type": job.job_type,
                "error_message": job.error_message,
                "priority": "CRITICAL"
            } for job in failed_jobs_res.scalars().all()
        ]

        queue = unreviewed + failed_items
        return {
            "total_actionable_items": len(queue),
            "queue": queue
        }
