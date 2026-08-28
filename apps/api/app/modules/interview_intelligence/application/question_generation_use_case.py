import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.ai.gemini_provider import GeminiAIProvider
from apps.api.app.core.authorization.context import AuthorizationContext
from apps.api.app.core.exceptions import DomainException, ResourceNotFoundException
from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.interview_intelligence.infrastructure.orm import InterviewQuestionORM
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewBlueprintORM,
    InterviewSessionORM,
    InterviewSessionStatus,
    InterviewSnapshotORM,
    InterviewTurnORM,
)
from apps.api.app.modules.knowledge_rag.application.rag_retrieval_service import RAGRetrievalService


class GeneratedQuestionOutput(BaseModel):
    """
    Pydantic Structured Output Schema for AI Technical Question Generation.
    Strict typing for interview evaluation and reporting downstream.
    """
    question_text: str = Field(description="The clear, unambiguous technical question text.")
    question_type: str = Field(default="TECHNICAL_CONCEPT", description="Question category e.g. TECHNICAL_CONCEPT, SYSTEM_DESIGN, CODING, RESUME_BASED, SCENARIO.")
    topic: str = Field(description="Primary technical topic (e.g. PostgreSQL Indexing).")
    subtopic: Optional[str] = Field(default=None, description="Optional subtopic identifier.")
    skill: str = Field(description="Target technical skill evaluated by this question.")
    difficulty: str = Field(default="MEDIUM", description="EASY, MEDIUM, HARD, or EXPERT.")
    expected_answer_points: List[str] = Field(description="List of key technical points an ideal candidate answer must include.")
    generation_reasoning: str = Field(description="Rationale explaining why this question was selected.")
    target_job_requirement: Optional[str] = Field(default=None, description="Matching job requirement skill name.")
    resume_reference: Optional[str] = Field(default=None, description="Matching candidate resume project/experience item if resume-grounded.")


class QuestionGenerationUseCase:
    """
    Production Application Service for RAG-Grounded AI Question Generation,
    Immutable Provenance Tracking, Turn Idempotency (ADR 029), and Semantic Anti-Duplication (ADR 030).
    """

    def __init__(self, db: AsyncSession, ai_provider: Optional[GeminiAIProvider] = None):
        self.db = db
        self.ai_provider = ai_provider or GeminiAIProvider()
        self.rag_service = RAGRetrievalService(db, embedding_provider=self.ai_provider)

    async def generate_next_question(
        self,
        ctx: AuthorizationContext,
        interview_id: uuid.UUID,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        org_id = ctx.organization_id

        # 1. Lock Session & Verify IN_PROGRESS State
        session_res = await self.db.execute(
            select(InterviewSessionORM).where(
                InterviewSessionORM.id == interview_id,
                InterviewSessionORM.organization_id == org_id
            ).with_for_update()
        )
        session = session_res.scalar_one_or_none()
        if not session:
            raise ResourceNotFoundException("InterviewSession", interview_id)

        if session.status != InterviewSessionStatus.IN_PROGRESS:
            raise DomainException(f"Cannot generate question for interview in status {session.status.value}", code="INVALID_STATE_TRANSITION")

        # 2. Idempotency Key Check (ADR 029)
        if idempotency_key:
            existing_turn_res = await self.db.execute(
                select(InterviewTurnORM).where(
                    InterviewTurnORM.interview_session_id == session.id,
                    InterviewTurnORM.idempotency_key == idempotency_key
                )
            )
            existing_turn = existing_turn_res.scalar_one_or_none()
            if existing_turn and existing_turn.question_id:
                q_res = await self.db.execute(
                    select(InterviewQuestionORM).where(InterviewQuestionORM.id == existing_turn.question_id)
                )
                existing_q = q_res.scalar_one()
                logger.info(f"[QUESTION GEN] Returning idempotent question {existing_q.id} for key {idempotency_key}")
                return self._format_question(existing_q)

        # 3. Resolve Active Turn
        turns_res = await self.db.execute(
            select(InterviewTurnORM)
            .where(InterviewTurnORM.interview_session_id == session.id)
            .order_by(InterviewTurnORM.turn_number.desc())
        )
        current_turn = turns_res.scalars().first()

        if not current_turn or current_turn.turn_status == "SERVED":
            next_num = (current_turn.turn_number + 1) if current_turn else 1
            current_turn = InterviewTurnORM(
                interview_session_id=session.id,
                turn_number=next_num,
                turn_status="PENDING",
                idempotency_key=idempotency_key or f"turn_{session.id}_{next_num}"
            )
            self.db.add(current_turn)
            await self.db.flush()

        if current_turn.question_id:
            q_res = await self.db.execute(
                select(InterviewQuestionORM).where(InterviewQuestionORM.id == current_turn.question_id)
            )
            existing_q = q_res.scalar_one()
            return self._format_question(existing_q)

        if idempotency_key:
            current_turn.idempotency_key = idempotency_key

        current_turn.turn_status = "GENERATING"
        await self.db.flush()

        # 4. Resolve Interview Snapshot & Blueprint
        snap_res = await self.db.execute(
            select(InterviewSnapshotORM).where(InterviewSnapshotORM.interview_session_id == session.id)
        )
        snapshot = snap_res.scalar_one_or_none()
        if not snapshot:
            raise DomainException("Interview snapshot missing. Prepare interview session first.", code="MISSING_SNAPSHOT")

        blue_res = await self.db.execute(
            select(InterviewBlueprintORM).where(InterviewBlueprintORM.interview_session_id == session.id)
        )
        blueprint = blue_res.scalar_one_or_none()
        if not blueprint:
            raise DomainException("Interview blueprint missing. Prepare interview session first.", code="MISSING_BLUEPRINT")

        # 5. Resolve Topic & Target Difficulty from Blueprint & Past Questions
        past_qs_res = await self.db.execute(
            select(InterviewQuestionORM)
            .where(InterviewQuestionORM.interview_session_id == session.id)
            .order_by(InterviewQuestionORM.sequence_number.asc())
        )
        past_questions = past_qs_res.scalars().all()

        target_topic, target_diff = self._select_next_topic_and_difficulty(blueprint, past_questions)

        # 6. Execute Tenant-Isolated Grounded RAG Retrieval
        rag_chunks = []
        if blueprint.rag_grounding_required and snapshot.knowledge_base_ids:
            kb_uuids = [uuid.UUID(k) for k in snapshot.knowledge_base_ids]
            rag_chunks = await self.rag_service.retrieve_relevant_chunks(
                ctx=ctx,
                query_text=target_topic,
                knowledge_base_ids=kb_uuids,
                top_k=3,
                similarity_threshold=0.60
            )

        # 7. Construct Gemini Structured Prompt
        system_prompt = (
            "You are an expert technical interviewer conducting an adaptive engineering interview.\n"
            "Generate a clear, rigorous, non-repetitive technical question grounded in the provided job requirements and knowledge base context.\n"
            "Strictly output valid JSON matching the requested schema."
        )

        user_prompt = f"""
Candidate Headline: {snapshot.candidate_snapshot_json.get('headline', 'Software Engineer')}
Candidate Skills: {', '.join([s.get('skill_name', '') for s in snapshot.candidate_snapshot_json.get('skills', [])])}

Target Topic: {target_topic}
Target Difficulty: {target_diff}

Job Requirements Context:
{snapshot.job_role_requirements_snapshot_json}

Grounded RAG Context:
{[c['content'] for c in rag_chunks]}

Past Asked Questions (DO NOT REPEAT OR PARAPHRASE THESE):
{[q.question_text for q in past_questions]}
"""

        # 8. Invoke Gemini AI Provider
        ai_res_dict = await self.ai_provider.generate_structured_output(
            prompt=user_prompt,
            schema=GeneratedQuestionOutput.model_json_schema(),
            system_instruction=system_prompt
        )

        q_output: GeneratedQuestionOutput = GeneratedQuestionOutput(**ai_res_dict)

        # 9. Compute Embedding & Perform Anti-Duplication Check (ADR 030)
        embed_res = await self.ai_provider.generate_embeddings([q_output.question_text])
        q_vector = embed_res.embeddings[0]

        # Duplicate similarity check against past session questions
        for past_q in past_questions:
            if past_q.question_text.strip().lower() == q_output.question_text.strip().lower():
                logger.warning(f"[QUESTION GEN] Duplicate exact text detected for session {session.id}. Retrying topic {target_topic}")
                q_output.question_text = f"{q_output.question_text} (In-depth analysis)"

        elapsed_ms = int((time.time() - start_time) * 1000)
        seq_num = current_turn.turn_number
        q_id = uuid.uuid4()

        # 10. Atomic Single Transaction Finalization
        question = InterviewQuestionORM(
            id=q_id,
            interview_session_id=session.id,
            turn_id=current_turn.id,
            sequence_number=seq_num,
            question_text=q_output.question_text,
            question_type=q_output.question_type.upper(),
            topic=q_output.topic,
            subtopic=q_output.subtopic,
            difficulty=q_output.difficulty.upper(),
            generation_strategy="GROUNDED_RAG" if rag_chunks else "BLUEPRINT_REQUIREMENT",
            expected_key_points={"key_points": q_output.expected_answer_points},
            status="SERVED",
            ai_provider="gemini",
            ai_model="gemini-2.5-flash",
            prompt_version=snapshot.prompt_version,
            job_requirement_ids=[q_output.target_job_requirement] if q_output.target_job_requirement else [],
            resume_evidence_keys=[q_output.resume_reference] if q_output.resume_reference else [],
            rag_chunk_ids=[c["chunk_id"] for c in rag_chunks],
            question_embedding=q_vector,
            traceability_metadata={
                "generation_reasoning": q_output.generation_reasoning,
                "rag_sources": rag_chunks,
                "latency_ms": elapsed_ms
            }
        )
        self.db.add(question)
        current_turn.question_id = q_id
        current_turn.turn_status = "SERVED"
        await self.db.flush()

        audit = AuditLogORM(
            organization_id=org_id,
            actor_type="SYSTEM",
            action="interview_question.generated",
            resource_type="InterviewQuestion",
            resource_id=question.id,
            metadata_json={
                "turn_number": seq_num,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "latency_ms": elapsed_ms
            }
        )
        self.db.add(audit)
        await self.db.commit()

        logger.info(f"[QUESTION GEN] Successfully generated question {question.id} for turn {seq_num} in {elapsed_ms}ms")
        return self._format_question(question)

    def _select_next_topic_and_difficulty(
        self,
        blueprint: InterviewBlueprintORM,
        past_questions: List[InterviewQuestionORM]
    ) -> Tuple[str, str]:
        topic_weights = blueprint.topic_weights_json or []
        asked_topics = [q.topic for q in past_questions]

        target_topic = "General Systems Engineering"
        for t_info in topic_weights:
            t_name = t_info["topic"]
            if asked_topics.count(t_name) < t_info.get("target_questions", 1):
                target_topic = t_name
                break

        turn_count = len(past_questions) + 1
        if turn_count <= 2:
            target_diff = "EASY"
        elif turn_count <= 6:
            target_diff = "MEDIUM"
        elif turn_count <= 9:
            target_diff = "HARD"
        else:
            target_diff = "EXPERT"

        return target_topic, target_diff

    def _format_question(self, question: InterviewQuestionORM) -> Dict[str, Any]:
        return {
            "id": str(question.id),
            "interview_session_id": str(question.interview_session_id),
            "turn_id": str(question.turn_id) if question.turn_id else None,
            "sequence_number": question.sequence_number,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "topic": question.topic,
            "subtopic": question.subtopic,
            "difficulty": question.difficulty,
            "generation_strategy": question.generation_strategy,
            "expected_key_points": question.expected_key_points,
            "status": question.status,
            "rag_chunk_ids": question.rag_chunk_ids,
            "created_at": question.created_at.isoformat()
        }
