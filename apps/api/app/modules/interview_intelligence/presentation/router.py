import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.dependencies import get_active_org_context, get_db
from apps.api.app.core.exceptions import ResourceNotFoundException
from apps.api.app.modules.interview_intelligence.application.manage_answers_use_case import (
    ManageAnswersUseCase,
)
from apps.api.app.modules.interview_intelligence.application.question_generation_use_case import (
    QuestionGenerationUseCase,
)
from apps.api.app.modules.interview_intelligence.infrastructure.orm import InterviewQuestionORM
from apps.api.app.modules.interviews.infrastructure.orm import InterviewSessionORM

interview_intelligence_router = APIRouter(prefix="/interviews", tags=["Interview Intelligence"])


class SubmitAnswerRequest(BaseModel):
    answer_text: str = Field(min_length=1, description="Candidate's technical answer text.")
    duration_seconds: Optional[int] = Field(default=None, description="Duration in seconds spent answering.")


@interview_intelligence_router.post("/{interview_id}/next-question", status_code=status.HTTP_200_OK)
async def generate_next_question(
    interview_id: uuid.UUID,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = QuestionGenerationUseCase(db)
    return await use_case.generate_next_question(ctx, interview_id, idempotency_key=idempotency_key)


@interview_intelligence_router.get("/{interview_id}/questions", status_code=status.HTTP_200_OK)
async def list_interview_questions(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    ctx.enforce_permission("interviews:read")

    sess_res = await db.execute(
        select(InterviewSessionORM).where(
            InterviewSessionORM.id == interview_id,
            InterviewSessionORM.organization_id == ctx.organization_id
        )
    )
    if not sess_res.scalar_one_or_none():
        raise ResourceNotFoundException("InterviewSession", interview_id)

    qs_res = await db.execute(
        select(InterviewQuestionORM)
        .where(InterviewQuestionORM.interview_session_id == interview_id)
        .order_by(InterviewQuestionORM.sequence_number.asc())
    )
    questions = qs_res.scalars().all()

    return [
        {
            "id": str(q.id),
            "sequence_number": q.sequence_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "status": q.status,
            "created_at": q.created_at.isoformat()
        } for q in questions
    ]


@interview_intelligence_router.post("/{interview_id}/questions/{question_id}/answer", status_code=status.HTTP_201_CREATED)
async def submit_answer(
    interview_id: uuid.UUID,
    question_id: uuid.UUID,
    body: SubmitAnswerRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageAnswersUseCase(db)
    return await use_case.submit_answer(
        ctx=ctx,
        interview_id=interview_id,
        question_id=question_id,
        answer_text=body.answer_text,
        idempotency_key=idempotency_key,
        duration_seconds=body.duration_seconds
    )


@interview_intelligence_router.get("/{interview_id}/questions/{question_id}/answer", status_code=status.HTTP_200_OK)
async def get_answer(
    interview_id: uuid.UUID,
    question_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageAnswersUseCase(db)
    return await use_case.get_answer(ctx, interview_id, question_id)


@interview_intelligence_router.get("/{interview_id}/questions/{question_id}/evaluation", status_code=status.HTTP_200_OK)
async def get_evaluation(
    interview_id: uuid.UUID,
    question_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageAnswersUseCase(db)
    return await use_case.get_evaluation(ctx, interview_id, question_id)


@interview_intelligence_router.get("/{interview_id}/progress", status_code=status.HTTP_200_OK)
async def get_interview_progress(
    interview_id: uuid.UUID,
    ctx: AuthorizationContext = Depends(get_active_org_context),
    db: AsyncSession = Depends(get_db)
):
    use_case = ManageAnswersUseCase(db)
    return await use_case.get_progress(ctx, interview_id)
