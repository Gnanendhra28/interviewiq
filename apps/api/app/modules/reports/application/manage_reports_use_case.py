import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import (
    ForbiddenException,
    ResourceNotFoundException,
)
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewSessionORM,
    InterviewSessionStatus,
)
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM


class ManageReportsUseCase:
    """
    Production Application Service for Interview Completion Orchestration, Report History Versioning (ADR 036),
    Report Regeneration, and Recruiter Decision Support (ADR 037).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def complete_interview(self, ctx: AuthorizationContext, interview_id: uuid.UUID, reason: Optional[str] = None) -> Dict[str, Any]:
        org_id = ctx.organization_id

        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == org_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        if session.status in (InterviewSessionStatus.COMPLETING, InterviewSessionStatus.COMPLETED):
            logger.info(f"[REPORT USECASE] Interview {interview_id} already in status {session.status.value}")
            return {"status": session.status.value, "message": "Interview session already completed or completing."}

        session.status = InterviewSessionStatus.COMPLETING
        session.cancellation_reason = reason

        report_job = BackgroundJobORM(
            organization_id=org_id,
            job_type="INTERVIEW_REPORT_GENERATION",
            status="QUEUED",
            resource_type="InterviewSession",
            resource_id=session.id,
            payload_metadata={"reason": reason or "Completion criteria met"},
            idempotency_key=f"rep_gen_{session.id}_v1"
        )
        self.db.add(report_job)

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="interview.completion_started",
            resource_type="InterviewSession",
            resource_id=session.id,
            metadata_json={"reason": reason}
        )
        self.db.add(audit)

        await self.db.commit()
        logger.info(f"[REPORT USECASE] Initiated interview completion for session {session.id}")
        return {"status": "COMPLETING", "job_id": str(report_job.id), "message": "Report generation enqueued."}

    async def get_latest_report(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        report_res = await self.db.execute(
            select(InterviewReportORM)
            .where(InterviewReportORM.interview_session_id == interview_id)
            .order_by(InterviewReportORM.report_version.desc())
        )
        report = report_res.scalars().first()
        if not report:
            raise ResourceNotFoundException("InterviewReport for Session", interview_id)

        return self._format_report(ctx, report)

    async def list_report_versions(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> List[Dict[str, Any]]:
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        if not session_res.scalar_one_or_none():
            raise ResourceNotFoundException("InterviewSession", interview_id)

        reports_res = await self.db.execute(
            select(InterviewReportORM)
            .where(InterviewReportORM.interview_session_id == interview_id)
            .order_by(InterviewReportORM.report_version.desc())
        )
        reports = reports_res.scalars().all()
        return [self._format_report(ctx, r) for r in reports]

    async def get_report_version(self, ctx: AuthorizationContext, interview_id: uuid.UUID, report_id: uuid.UUID) -> Dict[str, Any]:
        report_res = await self.db.execute(
            select(InterviewReportORM)
            .join(InterviewSessionORM, InterviewReportORM.interview_session_id == InterviewSessionORM.id)
            .where(
                InterviewReportORM.id == report_id,
                InterviewReportORM.interview_session_id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        report = report_res.scalar_one_or_none()
        if not report:
            raise ResourceNotFoundException("InterviewReport", report_id)

        return self._format_report(ctx, report)

    async def regenerate_report(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        ctx.enforce_permission("interviews:manage")

        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        ver_res = await self.db.execute(
            select(func.coalesce(func.max(InterviewReportORM.report_version), 0))
            .where(InterviewReportORM.interview_session_id == session.id)
        )
        next_ver = ver_res.scalar() + 1

        report_job = BackgroundJobORM(
            organization_id=ctx.organization_id,
            job_type="INTERVIEW_REPORT_GENERATION",
            status="QUEUED",
            resource_type="InterviewSession",
            resource_id=session.id,
            payload_metadata={"target_version": next_ver, "is_regeneration": True},
            idempotency_key=f"rep_regen_{session.id}_v{next_ver}"
        )
        self.db.add(report_job)

        audit = AuditLogORM(
            organization_id=ctx.organization_id,
            actor_user_id=ctx.user_id,
            actor_type="USER",
            action="interview.report_regenerated",
            resource_type="InterviewSession",
            resource_id=session.id,
            metadata_json={"target_version": next_ver}
        )
        self.db.add(audit)

        await self.db.commit()
        return {"status": "QUEUED", "target_version": next_ver, "message": "Report regeneration enqueued."}

    async def get_decision_support(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        if ctx.candidate_profile and not ctx.user.is_super_admin:
            raise ForbiddenException("Candidates are not authorized to view recruiter decision support metrics.")

        report = await self.get_latest_report(ctx, interview_id)
        
        return {
            "interview_session_id": str(interview_id),
            "hiring_signal": report.get("hiring_signal", "HIRE_SIGNAL"),
            "overall_score": report.get("overall_score"),
            "technical_competency_score": report.get("technical_competency_score"),
            "requirement_scorecards": report.get("requirement_scorecards_json", {}).get("scorecards", []),
            "recommendation": report.get("recommendation"),
            "executive_summary": report.get("executive_summary"),
            "top_strengths": report.get("top_strengths"),
            "growth_areas": report.get("growth_areas")
        }

    def _format_report(self, ctx: AuthorizationContext, report: InterviewReportORM) -> Dict[str, Any]:
        is_recruiter = ctx.user.is_super_admin or (ctx.role and ctx.role.name in ("ORGANIZATION_ADMIN", "RECRUITER", "HIRING_MANAGER"))

        formatted = {
            "id": str(report.id),
            "interview_session_id": str(report.interview_session_id),
            "report_version": report.report_version,
            "scoring_version": report.scoring_version,
            "overall_score": float(report.overall_score),
            "seniority_assessment": report.seniority_assessment,
            "executive_summary": report.executive_summary,
            "top_strengths": report.top_strengths,
            "growth_areas": report.growth_areas,
            "created_at": report.created_at.isoformat()
        }

        if is_recruiter:
            formatted.update({
                "technical_competency_score": float(report.technical_competency_score) if report.technical_competency_score else None,
                "reasoning_score": float(report.reasoning_score) if report.reasoning_score else None,
                "communication_score": float(report.communication_score) if report.communication_score else None,
                "completeness_score": float(report.completeness_score) if report.completeness_score else None,
                "requirement_coverage_score": float(report.requirement_coverage_score) if report.requirement_coverage_score else None,
                "recommendation": report.recommendation,
                "hiring_signal": report.hiring_signal,
                "requirement_scorecards_json": report.requirement_scorecards_json,
                "evidence_provenance_json": report.evidence_provenance_json
            })

        return formatted
