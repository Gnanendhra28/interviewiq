import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.modules.integrations.infrastructure.orm import (
    DeliveryAttemptHistoryORM,
    IntegrationEventORM,
    IntegrationORM,
    WebhookDeliveryORM,
)
from apps.api.app.modules.integrations.infrastructure.providers.greenhouse import GreenhouseProvider
from apps.api.app.modules.integrations.infrastructure.providers.lever import LeverProvider
from apps.api.app.modules.integrations.infrastructure.providers.workday import WorkdayProvider

logger = logging.getLogger("interviewiq.workers.webhook")

PROVIDERS = {
    "greenhouse": GreenhouseProvider(),
    "lever": LeverProvider(),
    "workday": WorkdayProvider(),
}

class ProcessWebhookDeliveryWorkerTask:
    """
    Transactional Outbox Webhook Delivery Task (ADR 047, ADR 048).
    Claims PENDING/RETRYING deliveries via SELECT FOR UPDATE SKIP LOCKED, executes provider dispatch, and logs delivery history.
    """
    @staticmethod
    async def execute(session: AsyncSession, worker_id: str, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        delivery_id_str = job_payload.get("delivery_id")
        if not delivery_id_str:
            return {"status": "SKIPPED", "reason": "No delivery_id specified."}

        delivery_id = uuid.UUID(delivery_id_str)
        stmt = (
            select(WebhookDeliveryORM)
            .where(WebhookDeliveryORM.id == delivery_id)
            .where(WebhookDeliveryORM.status.in_(["PENDING", "RETRYING"]))
            .with_for_update(skip_locked=True)
        )
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()

        if not delivery:
            return {"status": "SKIPPED", "reason": "Delivery not found or locked."}

        delivery.status = "PROCESSING"
        delivery.claimed_by = worker_id
        delivery.lease_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        delivery.attempts += 1
        await session.flush()

        # Fetch Integration and Event
        integration = await session.get(IntegrationORM, delivery.integration_id)
        event = await session.get(IntegrationEventORM, delivery.event_id)

        if not integration or not event:
            delivery.status = "FAILED"
            delivery.last_error_message = "Integration or Event missing."
            await session.commit()
            return {"status": "FAILED", "reason": "Missing resources."}

        provider = PROVIDERS.get(integration.provider_type)
        if not provider:
            delivery.status = "FAILED"
            delivery.last_error_message = f"Unsupported provider type: {integration.provider_type}"
            await session.commit()
            return {"status": "FAILED", "reason": "Unsupported provider."}

        start_time = datetime.now(timezone.utc)
        try:
            if event.event_type == "candidate.hiring_decision.updated":
                resp = await provider.deliver_hiring_decision(integration.config_metadata_json, integration.encrypted_secret or "", event.payload_json)
            else:
                resp = await provider.deliver_interview_report(integration.config_metadata_json, integration.encrypted_secret or "", event.payload_json)

            latency = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            attempt = DeliveryAttemptHistoryORM(
                delivery_id=delivery.id,
                attempt_number=delivery.attempts,
                response_status_code=resp.get("status_code", 200),
                latency_ms=latency,
            )
            session.add(attempt)

            delivery.status = "DELIVERED"
            delivery.last_response_code = resp.get("status_code", 200)
            delivery.claimed_by = None
            await session.commit()

            return {"status": "DELIVERED", "delivery_id": str(delivery.id), "attempts": delivery.attempts}
        except Exception as exc:
            latency = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            delivery.last_error_message = str(exc)
            attempt = DeliveryAttemptHistoryORM(
                delivery_id=delivery.id,
                attempt_number=delivery.attempts,
                response_status_code=500,
                error_message=str(exc),
                latency_ms=latency,
            )
            session.add(attempt)

            if delivery.attempts >= delivery.max_attempts:
                delivery.status = "DEAD_LETTER"
            else:
                delivery.status = "RETRYING"
                delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=2 ** delivery.attempts * 10)

            delivery.claimed_by = None
            await session.commit()
            return {"status": "RETRYING", "error": str(exc), "attempts": delivery.attempts}
