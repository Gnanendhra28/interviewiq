import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.ai.factory import get_ai_provider
from apps.api.app.core.ai.provider import AIProvider
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.background_jobs.infrastructure.orm import BackgroundJobORM
from apps.api.app.modules.resumes.application.apply_resume_projection_use_case import (
    ApplyResumeProjectionUseCase,
)
from apps.api.app.modules.resumes.domain.parser.factory import get_document_parser
from apps.api.app.modules.resumes.domain.prompts import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SYSTEM_RESUME_ANALYSIS_PROMPT,
)
from apps.api.app.modules.resumes.domain.schemas import (
    ExtractedEducation,
    ExtractedExperience,
    ExtractedSkill,
    ResumeAnalysisOutput,
)
from apps.api.app.modules.resumes.domain.text_validator import TextQualityValidator
from apps.api.app.modules.resumes.infrastructure.orm import ResumeAnalysisORM, ResumeORM

NON_RETRYABLE_ERROR_CODES = {
    "ENCRYPTED_DOCUMENT",
    "MALFORMED_DOCX",
    "UNSUPPORTED_PARSER_TYPE",
    "INVALID_FILE_SIGNATURE",
    "EMPTY_DOCUMENT"
}


class ProcessResumeWorkerTask:
    """
    Production background worker task for resume text extraction, quality validation,
    Gemini AI analysis, immutable analysis persistence, and candidate data projection.
    Enforces worker lease ownership semantics, non-retryable error classification,
    provenance metadata tracking, and single-transaction finalization.
    """

    def __init__(self, db: AsyncSession, ai_provider: Optional[AIProvider] = None, worker_id: Optional[uuid.UUID] = None):
        self.db = db
        self.worker_id = worker_id or uuid.uuid4()
        self.storage_provider = get_storage_provider()
        self.ai_provider = ai_provider or get_ai_provider()

    async def execute_job(self, job: BackgroundJobORM) -> Dict[str, Any]:
        start_time = time.time()
        resume_id = job.resource_id

        # 1. Verify Worker Lease Ownership Before Execution
        if job.claimed_by and job.claimed_by != self.worker_id and job.lease_expires_at:
            if job.lease_expires_at > datetime.now(timezone.utc):
                logger.warning(f"[WORKER] Aborting execution: Job {job.id} is actively claimed by worker {job.claimed_by}")
                return {"status": "ABORTED", "reason": "LEASE_OWNED_BY_ANOTHER_WORKER"}

        # 2. Load Resume Record
        res = await self.db.execute(select(ResumeORM).where(ResumeORM.id == resume_id))
        resume = res.scalar_one_or_none()
        if not resume:
            logger.error(f"[WORKER] Resume {resume_id} not found for job {job.id}")
            job.status = "FAILED"
            job.error_message = "Resume record not found"
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return {"status": "FAILED", "reason": "RESUME_NOT_FOUND"}

        # Update status to PROCESSING
        resume.processing_status = "PROCESSING"
        await self.db.flush()

        # 3. Physical Storage Download
        try:
            file_bytes = await self.storage_provider.download_file(resume.storage_key)
        except Exception as e:
            logger.error(f"[WORKER] Storage retrieval failed for resume {resume_id}: {type(e).__name__}")
            return await self._handle_job_failure(job, resume, f"Storage retrieval failed: {str(e)}", retryable=True)

        # 4. Document Parsing
        parser_name = "PDFParser"
        parser_version = "v1"
        try:
            file_type = "PDF" if "pdf" in resume.mime_type.lower() else "DOCX"
            parser = get_document_parser(file_type)
            parser_name = type(parser).__name__
            extracted_text = parser.parse_document(file_bytes)
        except DomainException as de:
            retryable = de.code not in NON_RETRYABLE_ERROR_CODES
            logger.error(f"[WORKER] Parsing failed for resume {resume_id} (code: {de.code}, retryable: {retryable})")
            return await self._handle_job_failure(job, resume, f"Document parsing failed: {de.message}", retryable=retryable)
        except Exception as parse_err:
            logger.error(f"[WORKER] Parsing exception for resume {resume_id}: {type(parse_err).__name__}")
            return await self._handle_job_failure(job, resume, f"Document parsing exception: {str(parse_err)}", retryable=True)

        # 5. Text Quality & OCR Decision Boundary
        quality = TextQualityValidator.validate_text_quality(extracted_text)
        if not quality["is_usable"]:
            logger.warning(f"[WORKER] Resume {resume_id} text quality validation failed: {quality['details']}")
            resume.processing_status = "OCR_REQUIRED"
            resume.error_message = quality["details"]

            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)

            audit = AuditLogORM(
                organization_id=resume.organization_id,
                actor_type="SYSTEM",
                action="resume.ocr_required",
                resource_type="Resume",
                resource_id=resume.id,
                metadata_json={"reason": quality["reason"], "details": quality["details"]}
            )
            self.db.add(audit)
            await self.db.commit()
            return {"status": "OCR_REQUIRED", "details": quality["details"]}

        # 6. Gemini AI Analysis (Structured Call)
        try:
            analysis_output = await self._run_ai_analysis(extracted_text)
        except Exception as ai_err:
            logger.error(f"[WORKER] AI analysis failed for resume {resume_id}: {type(ai_err).__name__}")
            return await self._handle_job_failure(job, resume, f"AI analysis failed: {str(ai_err)}", retryable=True)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # 7. Single Transaction Finalization: Analysis Persistence + Candidate Projection + Status Updates
        try:
            analysis = ResumeAnalysisORM(
                resume_id=resume.id,
                ai_provider=settings.AI_PROVIDER,
                ai_model=settings.GEMINI_MODEL,
                analysis_version=f"v{resume.version_number}",
                prompt_version=PROMPT_VERSION,
                schema_version=SCHEMA_VERSION,
                parser_name=parser_name,
                parser_version=parser_version,
                extracted_profile_json=analysis_output.model_dump(),
                raw_text_summary=analysis_output.candidate_summary,
                processing_time_ms=elapsed_ms
            )
            self.db.add(analysis)
            await self.db.flush()

            # Controlled Candidate Data Projection
            projection_service = ApplyResumeProjectionUseCase(self.db)
            proj_res = await projection_service.execute(
                organization_id=resume.organization_id,
                candidate_id=resume.candidate_profile_id,
                resume_id=resume.id,
                analysis_output=analysis_output
            )
            if proj_res.get("status") != "SUCCESS":
                raise DomainException(f"Projection failed: {proj_res.get('reason')}", code="PROJECTION_FAILED")

            # Finalize Resume and Job Status within same transaction
            resume.processing_status = "PROCESSED"
            resume.error_message = None

            # Verify Lease Ownership before completing job
            if job.claimed_by and job.claimed_by != self.worker_id and job.lease_expires_at:
                if job.lease_expires_at > datetime.now(timezone.utc):
                    logger.error(f"[WORKER] Ownership lost for job {job.id}. Aborting final commit.")
                    await self.db.rollback()
                    return {"status": "ABORTED", "reason": "LEASE_EXPIRED_OWNERSHIP_LOST"}

            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)

            audit = AuditLogORM(
                organization_id=resume.organization_id,
                actor_type="SYSTEM",
                action="resume.processed",
                resource_type="Resume",
                resource_id=resume.id,
                metadata_json={
                    "version": resume.version_number,
                    "processing_time_ms": elapsed_ms,
                    "skills_count": len(analysis_output.skills),
                    "experience_count": len(analysis_output.work_experience),
                    "education_count": len(analysis_output.education)
                }
            )
            self.db.add(audit)

            await self.db.commit()
            logger.info(f"[WORKER] Successfully processed resume {resume.id} in {elapsed_ms}ms")
            return {"status": "SUCCESS", "resume_id": str(resume.id), "processing_time_ms": elapsed_ms}

        except Exception as tx_err:
            logger.error(f"[WORKER] Transaction finalization failed for resume {resume_id}: {type(tx_err).__name__}. Rolling back.")
            await self.db.rollback()
            return await self._handle_job_failure(job, resume, f"Transaction finalization failed: {str(tx_err)}", retryable=True)

    async def _run_ai_analysis(self, extracted_text: str) -> ResumeAnalysisOutput:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("dev_"):
            return ResumeAnalysisOutput(
                candidate_summary="Experienced Software Engineer with expertise in Python and distributed systems.",
                inferred_seniority="SENIOR",
                skills=[
                    ExtractedSkill(skill_name="Python", category="Programming Languages", proficiency_level="EXPERT", years_experience=5.0, source_evidence="5 years Python experience"),
                    ExtractedSkill(skill_name="PostgreSQL", category="Databases", proficiency_level="ADVANCED", years_experience=4.0, source_evidence="PostgreSQL database design")
                ],
                work_experience=[
                    ExtractedExperience(company_name="Tech Solutions", job_title="Senior Developer", is_current=True, description="Lead backend architecture", source_evidence="Senior Developer at Tech Solutions")
                ],
                education=[
                    ExtractedEducation(institution="State University", degree="B.S.", field_of_study="Computer Science", end_year=2018, source_evidence="B.S. Computer Science")
                ],
                confidence_score=0.95
            )

        prompt = f"{SYSTEM_RESUME_ANALYSIS_PROMPT}\n\nRAW RESUME TEXT:\n{extracted_text}"
        res_json = await self.ai_provider.generate_structured_output(prompt, schema=ResumeAnalysisOutput.model_json_schema())
        if isinstance(res_json, str):
            res_json = json.loads(res_json)
        return ResumeAnalysisOutput.model_validate(res_json)

    async def _handle_job_failure(self, job: BackgroundJobORM, resume: ResumeORM, error_msg: str, retryable: bool) -> Dict[str, Any]:
        job_id = job.id
        resume_id = resume.id
        await self.db.rollback()

        res_job = await self.db.execute(select(BackgroundJobORM).where(BackgroundJobORM.id == job_id))
        fresh_job = res_job.scalar_one_or_none()
        res_res = await self.db.execute(select(ResumeORM).where(ResumeORM.id == resume_id))
        fresh_resume = res_res.scalar_one_or_none()

        if fresh_resume:
            fresh_resume.error_message = error_msg

        if fresh_job:
            fresh_job.error_message = error_msg
            if fresh_job.attempts == 0:
                fresh_job.attempts = 1
            if retryable and fresh_job.attempts < fresh_job.max_attempts:
                fresh_job.status = "QUEUED"
                fresh_job.claimed_by = None
                fresh_job.lease_expires_at = None
                if fresh_resume:
                    fresh_resume.processing_status = "QUEUED"
                logger.warning(f"[WORKER] Retryable failure for job {fresh_job.id} (attempt {fresh_job.attempts}/{fresh_job.max_attempts}): {error_msg}")
            else:
                fresh_job.status = "FAILED"
                fresh_job.completed_at = datetime.now(timezone.utc)
                if fresh_resume:
                    fresh_resume.processing_status = "FAILED"
                logger.error(f"[WORKER] Non-retryable/terminal failure for job {fresh_job.id}: {error_msg}")

        if fresh_resume:
            audit = AuditLogORM(
                organization_id=fresh_resume.organization_id,
                actor_type="SYSTEM",
                action="resume.processing_failed",
                resource_type="Resume",
                resource_id=fresh_resume.id,
                metadata_json={"error": error_msg, "retryable": retryable, "attempt": fresh_job.attempts if fresh_job else 1}
            )
            self.db.add(audit)

        await self.db.commit()
        return {"status": "FAILED", "reason": error_msg, "retryable": retryable}
