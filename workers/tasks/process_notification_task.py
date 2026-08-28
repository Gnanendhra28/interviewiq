import logging
import uuid
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.modules.notifications.infrastructure.orm import NotificationDeliveryORM
from apps.api.app.modules.notifications.infrastructure.slack import SlackNotificationProvider
from apps.api.app.modules.notifications.infrastructure.teams import TeamsNotificationProvider

logger = logging.getLogger("interviewiq.workers.notification")

slack_provider = SlackNotificationProvider()
teams_provider = TeamsNotificationProvider()

class ProcessNotificationWorkerTask:
    """
    Multi-Channel Recruiter Notification Worker Task (ADR 049).
    """
    @staticmethod
    async def execute(session: AsyncSession, worker_id: str, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        org_id_str = job_payload.get("organization_id")
        user_id_str = job_payload.get("user_id")
        channel = job_payload.get("channel", "IN_APP")
        event_type = job_payload.get("event_type", "report.generated")
        title = job_payload.get("title", "InterviewIQ Notification")
        message = job_payload.get("message", "")
        webhook_url = job_payload.get("webhook_url")
        resource_id = job_payload.get("resource_id")

        if not org_id_str or not user_id_str:
            return {"status": "SKIPPED", "reason": "Missing required identifiers."}

        delivery = NotificationDeliveryORM(
            organization_id=uuid.UUID(org_id_str),
            user_id=uuid.UUID(user_id_str),
            channel=channel,
            event_type=event_type,
            title=title,
            message=message,
            resource_id=resource_id,
            is_read=False,
        )
        session.add(delivery)

        if channel == "SLACK" and webhook_url:
            await slack_provider.send_notification(webhook_url, title, message)
        elif channel == "TEAMS" and webhook_url:
            await teams_provider.send_notification(webhook_url, title, message)

        await session.commit()
        return {"status": "DELIVERED", "notification_id": str(delivery.id), "channel": channel}
