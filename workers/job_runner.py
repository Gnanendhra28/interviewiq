import asyncio
import signal
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from apps.api.app.core.database import AsyncSessionLocal
from apps.api.app.core.logging import logger
from apps.api.app.modules.background_jobs.infrastructure.job_claimer import JobClaimer
from apps.api.app.modules.background_jobs.infrastructure.orm import (
    WorkerHeartbeatORM,
)
from workers.tasks.process_answer_evaluation_task import ProcessAnswerEvaluationWorkerTask
from workers.tasks.process_interview_report_task import ProcessInterviewReportWorkerTask
from workers.tasks.process_knowledge_document_task import ProcessKnowledgeDocumentWorkerTask
from workers.tasks.process_notification_task import ProcessNotificationWorkerTask
from workers.tasks.process_pdf_export_task import ProcessPDFExportWorkerTask
from workers.tasks.process_resume_task import ProcessResumeWorkerTask
from workers.tasks.process_webhook_delivery_task import ProcessWebhookDeliveryWorkerTask

WORKER_ID = uuid.uuid4()
IS_RUNNING = True


def handle_shutdown_signal(signum, frame):
    global IS_RUNNING
    logger.info(f"[WORKER {WORKER_ID}] Received shutdown signal ({signum}). Initiating graceful worker shutdown...")
    IS_RUNNING = False


async def update_worker_heartbeat(active_jobs: int = 0, status_str: str = "ACTIVE"):
    """Periodically records worker operational heartbeat in PostgreSQL (ADR 044)."""
    try:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            stmt = select(WorkerHeartbeatORM).where(WorkerHeartbeatORM.worker_id == WORKER_ID)
            res = await db.execute(stmt)
            hb = res.scalar_one_or_none()

            if hb:
                hb.last_heartbeat_at = now
                hb.active_jobs_count = active_jobs
                hb.status = status_str
            else:
                hb = WorkerHeartbeatORM(
                    worker_id=WORKER_ID,
                    status=status_str,
                    last_heartbeat_at=now,
                    active_jobs_count=active_jobs,
                    build_version="v1.0.0"
                )
                db.add(hb)
            await db.commit()
    except Exception as e:
        logger.warning(f"[WORKER {WORKER_ID}] Heartbeat update failed: {e}")


async def process_queued_jobs():
    """
    Worker task polling loop executing reliable PostgreSQL FOR UPDATE SKIP LOCKED job claiming,
    stale job crash recovery, heartbeat updates, and multi-task processing dispatch.
    """
    await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")

    async with AsyncSessionLocal() as db:
        # 1. Recover stale crashed jobs if any
        await JobClaimer.recover_stale_jobs(db, lease_timeout_minutes=10)

        # 2. Check for RESUME_PARSING jobs
        resume_job = await JobClaimer.claim_next_job(db, job_type="RESUME_PARSING")
        if resume_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {resume_job.id} (type: {resume_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            task = ProcessResumeWorkerTask(db, worker_id=WORKER_ID)
            await task.execute_job(resume_job)
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return

        # 3. Check for DOCUMENT_INGESTION jobs
        doc_job = await JobClaimer.claim_next_job(db, job_type="DOCUMENT_INGESTION")
        if doc_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {doc_job.id} (type: {doc_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            task = ProcessKnowledgeDocumentWorkerTask(db, worker_id=WORKER_ID)
            await task.execute_job(doc_job)
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return

        # 4. Check for ANSWER_EVALUATION jobs
        eval_job = await JobClaimer.claim_next_job(db, job_type="ANSWER_EVALUATION")
        if eval_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {eval_job.id} (type: {eval_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            task = ProcessAnswerEvaluationWorkerTask(db, worker_id=WORKER_ID)
            await task.execute_job(eval_job)
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return

        # 5. Check for INTERVIEW_REPORT_GENERATION jobs
        report_job = await JobClaimer.claim_next_job(db, job_type="INTERVIEW_REPORT_GENERATION")
        if report_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {report_job.id} (type: {report_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            task = ProcessInterviewReportWorkerTask(db, worker_id=WORKER_ID)
            await task.execute_job(report_job)
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return

        # 6. Check for PROCESS_WEBHOOK_DELIVERY jobs
        webhook_job = await JobClaimer.claim_next_job(db, job_type="PROCESS_WEBHOOK_DELIVERY")
        if webhook_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {webhook_job.id} (type: {webhook_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            await ProcessWebhookDeliveryWorkerTask.execute(db, str(WORKER_ID), webhook_job.payload_json)
            webhook_job.status = "COMPLETED"
            await db.commit()
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return

        # 7. Check for PROCESS_NOTIFICATION jobs
        notif_job = await JobClaimer.claim_next_job(db, job_type="PROCESS_NOTIFICATION")
        if notif_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {notif_job.id} (type: {notif_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            await ProcessNotificationWorkerTask.execute(db, str(WORKER_ID), notif_job.payload_json)
            notif_job.status = "COMPLETED"
            await db.commit()
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return

        # 8. Check for PDF_REPORT_GENERATION jobs
        pdf_job = await JobClaimer.claim_next_job(db, job_type="PDF_REPORT_GENERATION")
        if pdf_job:
            logger.info(f"[WORKER {WORKER_ID}] Dispatching background job {pdf_job.id} (type: {pdf_job.job_type})")
            await update_worker_heartbeat(active_jobs=1, status_str="ACTIVE")
            await ProcessPDFExportWorkerTask.execute(db, str(WORKER_ID), pdf_job.payload_json)
            pdf_job.status = "COMPLETED"
            await db.commit()
            await update_worker_heartbeat(active_jobs=0, status_str="ACTIVE")
            return


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    async def main_loop():
        logger.info(f"[WORKER {WORKER_ID}] Background worker process started.")
        while IS_RUNNING:
            await process_queued_jobs()
            await asyncio.sleep(2)
        await update_worker_heartbeat(active_jobs=0, status_str="SHUTTING_DOWN")
        logger.info(f"[WORKER {WORKER_ID}] Worker process shut down cleanly.")

    asyncio.run(main_loop())
