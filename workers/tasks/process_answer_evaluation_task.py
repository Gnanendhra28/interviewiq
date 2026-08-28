import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.ai.gemini_provider import GeminiAIProvider
from apps.api.app.core.exceptions import ResourceNotFoundException
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.interview_intelligence.infrastructure.orm import (
    AdaptiveDecisionORM,
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

DIFFICULTY_LEVELS = ["EASY", "MEDIUM", "HARD", "EXPERT"]


class AnswerEvaluationOutput(BaseModel):
    overall_score: float = Field(description="Overall answer score from 0.0 to 10.0", ge=0.0, le=10.0)
    score_technical_accuracy: float = Field(description="Technical accuracy score from 0.0 to 10.0", ge=0.0, le=10.0)
    score_depth: float = Field(description="Conceptual depth score from 0.0 to 10.0", ge=0.0, le=10.0)
    score_clarity: float = Field(description="Communication clarity score from 0.0 to 10.0", ge=0.0, le=10.0)
    completeness_score: float = Field(default=8.0, description="Completeness score from 0.0 to 10.0", ge=0.0, le=10.0)
    reasoning_quality_score: float = Field(default=8.0, description="Reasoning quality score from 0.0 to 10.0", ge=0.0, le=10.0)
    confidence_level: float = Field(default=0.9, description="Evaluator confidence from 0.0 to 1.0", ge=0.0, le=1.0)
    key_strengths: List[str] = Field(description="List of identified candidate answer strengths.")
    missing_elements: List[str] = Field(description="List of missing concepts or key points.")
    feedback_text: str = Field(description="Constructive technical feedback text for recruiter evaluation.")


class ProcessAnswerEvaluationWorkerTask:
    """
    Durable Background Worker Task for AI Answer Evaluation, Evaluation Versioning (ADR 032),
    Deterministic Adaptive Intelligence (ADR 033), and Single-Transaction Finalization.
    """

    def __init__(self, db: AsyncSession, ai_provider: Optional[GeminiAIProvider] = None, worker_id: Optional[uuid.UUID] = None):
        self.db = db
        self.ai_provider = ai_provider or GeminiAIProvider()
        self.worker_id = worker_id or uuid.uuid4()

    async def execute_job(self, job: BackgroundJobORM) -> None:
        start_time = time.time()
        answer_id = job.resource_id

        # 1. Fetch Candidate Answer
        ans_res = await self.db.execute(
            select(CandidateAnswerORM).where(CandidateAnswerORM.id == answer_id)
        )
        answer = ans_res.scalar_one_or_none()
        if not answer:
            raise ResourceNotFoundException("CandidateAnswer", answer_id)

        session_id = answer.interview_session_id
        org_id = job.organization_id

        # 2. Fetch Interview Orchestration Context
        sess_res = await self.db.execute(select(InterviewSessionORM).where(InterviewSessionORM.id == session_id))
        session = sess_res.scalar_one()

        q_res = await self.db.execute(select(InterviewQuestionORM).where(InterviewQuestionORM.id == answer.question_id))
        question = q_res.scalar_one()

        turn_res = await self.db.execute(select(InterviewTurnORM).where(InterviewTurnORM.id == question.turn_id))
        turn = turn_res.scalar_one_or_none()

        blue_res = await self.db.execute(select(InterviewBlueprintORM).where(InterviewBlueprintORM.interview_session_id == session_id))
        blueprint = blue_res.scalar_one_or_none()

        past_evals_res = await self.db.execute(
            select(AnswerEvaluationORM)
            .join(CandidateAnswerORM, AnswerEvaluationORM.answer_id == CandidateAnswerORM.id)
            .where(CandidateAnswerORM.interview_session_id == session_id)
        )
        past_evals_res.scalars().all()

        # 3. Construct Gemini Evaluation Prompt
        system_prompt = (
            "You are an expert technical evaluation engine scoring a candidate's technical interview answer.\n"
            "Evaluate the answer against the question's expected key points and job role context.\n"
            "Strictly output valid JSON matching the requested schema."
        )

        user_prompt = f"""
Question Text: {question.question_text}
Question Topic: {question.topic}
Question Difficulty: {question.difficulty}
Expected Key Points: {question.expected_key_points}

Candidate Submitted Answer:
{answer.answer_text}
"""

        # 4. Invoke Gemini AI Provider
        ai_res_dict = await self.ai_provider.generate_structured_output(
            prompt=user_prompt,
            schema=AnswerEvaluationOutput.model_json_schema(),
            system_instruction=system_prompt
        )

        eval_out = AnswerEvaluationOutput(**ai_res_dict)

        # 5. Execute Deterministic Adaptive Intelligence Rules (ADR 033)
        current_diff = question.difficulty.upper()
        next_diff = self._adapt_difficulty(current_diff, eval_out.overall_score)
        
        # Check completion boundary
        turn_num = turn.turn_number if turn else 1
        total_target = blueprint.total_target_questions if blueprint else 10
        is_completion = turn_num >= total_target

        past_qs_res = await self.db.execute(
            select(InterviewQuestionORM).where(InterviewQuestionORM.interview_session_id == session_id)
        )
        past_topics = [q.topic for q in past_qs_res.scalars().all()]

        next_topic = "General Technical Systems"
        if blueprint and blueprint.topic_weights_json:
            for tw in blueprint.topic_weights_json:
                if past_topics.count(tw["topic"]) < tw.get("target_questions", 1):
                    next_topic = tw["topic"]
                    break

        rationale = (
            f"Evaluated Turn {turn_num} score {eval_out.overall_score:.2f}/10.0. "
            f"Adapted difficulty {current_diff} -> {next_diff}. "
            f"{'Interview target turns reached. Transitioning to COMPLETING.' if is_completion else f'Selected next topic {next_topic}.'}"
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 6. Single-Transaction Atomic Persistence
        evaluation = AnswerEvaluationORM(
            answer_id=answer.id,
            evaluation_version=1,
            overall_score=eval_out.overall_score,
            score_technical_accuracy=eval_out.score_technical_accuracy,
            score_depth=eval_out.score_depth,
            score_clarity=eval_out.score_clarity,
            completeness_score=eval_out.completeness_score,
            reasoning_quality_score=eval_out.reasoning_quality_score,
            confidence_level=eval_out.confidence_level,
            key_strengths={"strengths": eval_out.key_strengths},
            missing_elements={"missing": eval_out.missing_elements},
            feedback_text=eval_out.feedback_text,
            evaluation_metadata_json={"latency_ms": elapsed_ms},
            ai_provider="gemini",
            ai_model="gemini-2.5-flash",
            prompt_version="v1"
        )
        self.db.add(evaluation)

        adaptive_decision = AdaptiveDecisionORM(
            interview_session_id=session_id,
            turn_id=turn.id if turn else None,
            decision_point_sequence=turn_num,
            previous_difficulty=current_diff,
            selected_next_difficulty=next_diff,
            selected_next_topic=next_topic,
            is_completion_decision=is_completion,
            performance_signal_summary=f"Turn {turn_num} score: {eval_out.overall_score:.2f}",
            decision_rationale=rationale,
            decision_metadata_json={"latency_ms": elapsed_ms}
        )
        self.db.add(adaptive_decision)

        if turn:
            turn.turn_status = "EVALUATED"

        if is_completion:
            session.status = InterviewSessionStatus.COMPLETING
            session.completed_at = datetime.now(timezone.utc)

        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)

        audit_a = AuditLogORM(
            organization_id=org_id,
            actor_type="SYSTEM",
            action="answer.evaluated",
            resource_type="AnswerEvaluation",
            resource_id=evaluation.id,
            metadata_json={"answer_id": str(answer.id), "score": float(evaluation.overall_score)}
        )
        self.db.add(audit_a)

        audit_b = AuditLogORM(
            organization_id=org_id,
            actor_type="SYSTEM",
            action="interview.adaptation_decided",
            resource_type="AdaptiveDecision",
            resource_id=adaptive_decision.id,
            metadata_json={"next_topic": next_topic, "next_difficulty": next_diff, "is_completion": is_completion}
        )
        self.db.add(audit_b)

        await self.db.commit()
        logger.info(f"[ANSWER EVAL WORKER] Evaluated answer {answer.id} (Score: {eval_out.overall_score}) in {elapsed_ms}ms")

    def _adapt_difficulty(self, current_diff: str, score: float) -> str:
        idx = DIFFICULTY_LEVELS.index(current_diff) if current_diff in DIFFICULTY_LEVELS else 1
        if score >= 8.0 and idx < len(DIFFICULTY_LEVELS) - 1:
            idx += 1
        elif score < 5.0 and idx > 0:
            idx -= 1
        return DIFFICULTY_LEVELS[idx]
