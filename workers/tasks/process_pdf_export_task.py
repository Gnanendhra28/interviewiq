import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.storage.factory import get_storage_provider
from apps.api.app.modules.reports.application.pdf_generator import PDFReportGenerator
from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM, ReportExportORM

logger = logging.getLogger("interviewiq.workers.pdf_export")

class ProcessPDFExportWorkerTask:
    """
    Immutable Report PDF Generation Worker Task (ADR 050).
    Renders PDF document bytes from an immutable InterviewReportORM record and persists to secure storage.
    """
    @staticmethod
    async def execute(session: AsyncSession, worker_id: str, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        export_id_str = job_payload.get("export_id")
        if not export_id_str:
            return {"status": "SKIPPED", "reason": "No export_id provided."}

        export_id = uuid.UUID(export_id_str)
        stmt = select(ReportExportORM).where(ReportExportORM.id == export_id).with_for_update(skip_locked=True)
        result = await session.execute(stmt)
        export = result.scalar_one_or_none()

        if not export:
            return {"status": "SKIPPED", "reason": "ReportExport record not found or locked."}

        export.status = "PROCESSING"
        await session.flush()

        report = await session.get(InterviewReportORM, export.interview_report_id)
        if not report:
            export.status = "FAILED"
            export.error_message = "Target InterviewReport record not found."
            await session.commit()
            return {"status": "FAILED", "reason": "Missing report snapshot."}

        try:
            pdf_bytes = PDFReportGenerator.generate_pdf_bytes(report)
            storage_key = f"organizations/{export.organization_id}/reports/{export.interview_session_id}/v{export.report_version}/export.pdf"

            storage = get_storage_provider()
            await storage.upload_file(pdf_bytes, storage_key, "application/pdf")

            export.storage_object_key = storage_key
            export.file_size_bytes = len(pdf_bytes)
            export.status = "READY"
            await session.commit()

            return {"status": "READY", "export_id": str(export.id), "file_size_bytes": len(pdf_bytes)}
        except Exception as exc:
            logger.error("PDF Export generation failed: %s", str(exc), exc_info=True)
            export.status = "FAILED"
            export.error_message = str(exc)
            await session.commit()
            return {"status": "FAILED", "error": str(exc)}
