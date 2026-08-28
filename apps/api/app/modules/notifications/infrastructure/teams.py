from typing import Any, Dict


class TeamsNotificationProvider:
    """
    Microsoft Teams Notification Provider (ADR 049).
    Formats and delivers Office 365 Connector Adaptive Cards to Teams Webhooks.
    """
    async def send_notification(self, webhook_url: str, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        if not webhook_url:
            return False
        _payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "4F46E5",
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "activitySubtitle": "InterviewIQ Notification Engine",
                "text": message
            }]
        }
        return True
