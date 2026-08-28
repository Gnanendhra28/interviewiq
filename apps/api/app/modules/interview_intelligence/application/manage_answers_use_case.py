import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import (
    DomainException,
    ForbiddenException,
    ResourceNotFoundException,
)
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.interview_intelligence.infrastructure.orm import (
    AnswerEvaluationORM,
    CandidateAnswerORM,
    InterviewQuestionORM,
)
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewBlueprintORM,
    InterviewSessionORM,
    InterviewSessionStatus,
    InterviewTurnORM,
)


class ManageAnswersUseCase:
    """
    Production Application Service for Secure Answer Submission, Database-Enforced Idempotency (ADR 031),
    Evaluation Dispatching, and Progress Tracking.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit_answer(
        self,
        ctx: AuthorizationContext,
        interview_id: uuid.UUID,
        question_id: uuid.UUID,
        answer_text: str,
        idempotency_key: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        org_id = ctx.organization_id

        # 1. Fetch & Validate Interview Session
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == org_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        if session.status != InterviewSessionStatus.IN_PROGRESS:
            raise DomainException(f"Cannot submit answer for interview in status {session.status.value}", code="INVALID_STATE_TRANSITION")

        # Candidate Authorization Check
        if ctx.candidate_profile and ctx.candidate_profile.id != session.candidate_profile_id:
            raise ForbiddenException("Candidate can only submit answers to their own interview session")

        # 2. Fetch & Validate Question
        q_res = await self.db.execute(
            select(InterviewQuestionORM).where(
                InterviewQuestionORM.id == question_id,
                InterviewQuestionORM.interview_session_id == session.id
            )
        )
        question = q_res.scalar_one_or_none()
        if not question:
            raise ResourceNotFoundException("InterviewQuestion", question_id)

        # 3. Idempotency Check: Return existing answer if already submitted (ADR 031)
        existing_ans_res = await self.db.execute(
            select(CandidateAnswerORM).where(CandidateAnswerORM.question_id == question.id)
        )
        existing_ans = existing_ans_res.scalar_one_or_none()
        if existing_ans:
            logger.info(f"[ANSWER SUBMIT] Returning idempotent existing answer {existing_ans.id} for question {question.id}")
            return self._format_answer(existing_ans)

        if idempotency_key:
            idem_res = await self.db.execute(
                select(CandidateAnswerORM).where(
                    CandidateAnswerORM.question_id == question.id,
                    CandidateAnswerORM.idempotency_key == idempotency_key
                )
            )
            idem_ans = idem_res.scalar_one_or_none()
            if idem_ans:
                logger.info(f"[ANSWER SUBMIT] Returning idempotent answer {idem_ans.id} for key {idempotency_key}")
                return self._format_answer(idem_ans)

        now = datetime.now(timezone.utc)
        answer_id = uuid.uuid4()

        # 4. Create Immutable Candidate Answer
        answer = CandidateAnswerORM(
            id=answer_id,
            interview_session_id=session.id,
            candidate_profile_id=session.candidate_profile_id,
            question_id=question.id,
            turn_id=question.turn_id,
            answer_text=answer_text.strip(),
            submission_status="SUBMITTED",
            attempt_number=1,
            duration_seconds=duration_seconds,
            idempotency_key=idempotency_key or f"ans_{question.id}_1",
            submitted_at=now
        )
        self.db.add(answer)

        session.last_activity_at = now

        if question.turn_id:
            turn_res = await self.db.execute(select(InterviewTurnORM).where(InterviewTurnORM.id == question.turn_id))
            turn = turn_res.scalar_one_or_none()
            if turn:
                turn.turn_status = "ANSWER_SUBMITTED"

        # 5. Enqueue Background ANSWER_EVALUATION Job
        eval_job = BackgroundJobORM(
            organization_id=org_id,
            job_type="ANSWER_EVALUATION",
            status="QUEUED",
            resource_type="CandidateAnswer",
            resource_id=answer.id,
            payload_metadata={"interview_session_id": str(session.id), "question_id": str(question.id)},
            idempotency_key=f"eval_ans_{answer.id}_v1"
        )
        self.db.add(eval_job)

        audit = AuditLogORM(
            organization_id=org_id,
            actor_user_id=ctx.user_id,
            actor_type="CANDIDATE" if ctx.candidate_profile else "USER",
            action="answer.submitted",
            resource_type="CandidateAnswer",
            resource_id=answer.id,
            metadata_json={"question_id": str(question.id), "turn_id": str(question.turn_id) if question.turn_id else None}
        )
        self.db.add(audit)

        await self.db.commit()
        logger.info(f"[ANSWER SUBMIT] Successfully persisted candidate answer {answer.id} and enqueued evaluation job {eval_job.id}")
        return self._format_answer(answer)

    async def get_answer(self, ctx: AuthorizationContext, interview_id: uuid.UUID, question_id: uuid.UUID) -> Dict[str, Any]:
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        ans_res = await self.db.execute(
            select(CandidateAnswerORM).where(
                CandidateAnswerORM.interview_session_id == interview_id,
                CandidateAnswerORM.question_id == question_id
            )
        )
        answer = ans_res.scalar_one_or_none()
        if not answer:
            raise ResourceNotFoundException("CandidateAnswer for Question", question_id)

        return self._format_answer(answer)

    async def get_evaluation(self, ctx: AuthorizationContext, interview_id: uuid.UUID, question_id: uuid.UUID) -> Dict[str, Any]:
        ans = await self.get_answer(ctx, interview_id, question_id)
        ans_id = uuid.UUID(ans["id"])

        eval_res = await self.db.execute(
            select(AnswerEvaluationORM).where(
                AnswerEvaluationORM.answer_id == ans_id,
                AnswerEvaluationORM.evaluation_version == 1
            )
        )
        evaluation = eval_res.scalar_one_or_none()
        if not evaluation:
            return {"status": "EVALUATING", "message": "Answer evaluation is currently processing in background worker."}

        is_recruiter = ctx.user.is_super_admin or ctx.role.name in ("ORGANIZATION_ADMIN", "RECRUITER", "HIRING_MANAGER")

        resp = {
            "id": str(evaluation.id),
            "answer_id": str(evaluation.answer_id),
            "overall_score": float(evaluation.overall_score),
            "evaluation_version": evaluation.evaluation_version,
            "created_at": evaluation.created_at.isoformat()
        }

        if is_recruiter:
            resp.update({
                "score_technical_accuracy": float(evaluation.score_technical_accuracy),
                "score_depth": float(evaluation.score_depth),
                "score_clarity": float(evaluation.score_clarity),
                "completeness_score": float(evaluation.completeness_score) if evaluation.completeness_score else None,
                "key_strengths": evaluation.key_strengths,
                "missing_elements": evaluation.missing_elements,
                "feedback_text": evaluation.feedback_text
            })

        return resp

    async def get_progress(self, ctx: AuthorizationContext, interview_id: uuid.UUID) -> Dict[str, Any]:
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == ctx.organization_id
            )
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        turns_res = await self.db.execute(
            select(func.count(InterviewTurnORM.id)).where(InterviewTurnORM.interview_session_id == session.id)
        )
        total_turns = turns_res.scalar() or 0

        completed_turns_res = await self.db.execute(
            select(func.count(InterviewTurnORM.id)).where(
                InterviewTurnORM.interview_session_id == session.id,
                InterviewTurnORM.turn_status == "EVALUATED"
            )
        )
        completed_turns = completed_turns_res.scalar() or 0

        blue_res = await self.db.execute(select(InterviewBlueprintORM).where(InterviewBlueprintORM.interview_session_id == session.id))
        blueprint = blue_res.scalar_one_or_none()
        target_questions = blueprint.total_target_questions if blueprint else 10

        return {
            "interview_session_id": str(session.id),
            "status": session.status.value,
            "total_turns": total_turns,
            "completed_turns": completed_turns,
            "target_questions": target_questions,
            "remaining_questions": max(0, target_questions - completed_turns),
            "is_complete": session.status in (InterviewSessionStatus.COMPLETING, InterviewSessionStatus.COMPLETED)
        }

    def _format_answer(self, answer: CandidateAnswerORM) -> Dict[str, Any]:
        return {
            "id": str(answer.id),
            "interview_session_id": str(answer.interview_session_id),
            "candidate_profile_id": str(answer.candidate_profile_id),
            "question_id": str(answer.question_id),
            "turn_id": str(answer.turn_id) if answer.turn_id else None,
            "submission_status": answer.submission_status,
            "attempt_number": answer.attempt_number,
            "submitted_at": answer.submitted_at.isoformat(),
            "created_at": answer.created_at.isoformat()
        }
