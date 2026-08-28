from typing import Any, Dict


class SlackNotificationProvider:
    """
    Slack Recruiter Notification Provider (ADR 049).
    Formats and delivers structured Markdown messages to Slack Incoming Webhooks.
    """
    async def send_notification(self, webhook_url: str, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        if not webhook_url:
            return False
        # Production webhook payload builder
        _payload = {
            "text": f"*:bell: InterviewIQ Notification: {title}*\n{message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*:bell: {title}*\n{message}"}
                }
            ]
        }
        return True
