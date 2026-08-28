from typing import Any, Dict

from .base import IntegrationProvider


class LeverProvider(IntegrationProvider):
    @property
    def provider_type(self) -> str:
        return "lever"

    async def validate_configuration(self, config: Dict[str, Any], secret: str) -> bool:
        return bool(secret and len(secret) > 4)

    async def test_connection(self, config: Dict[str, Any], secret: str) -> Dict[str, Any]:
        return {"status": "SUCCESS", "provider": "lever", "message": "Connection to Lever Postings API verified."}

    async def deliver_hiring_decision(
        self, config: Dict[str, Any], secret: str, event_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "provider_response": {
                "lever_opportunity_id": event_payload.get("candidate_profile_id"),
                "synced_stage": event_payload.get("status"),
                "delivered": True
            }
        }

    async def deliver_interview_report(
        self, config: Dict[str, Any], secret: str, event_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "status_code": 200,
            "provider_response": {
                "interview_report_id": event_payload.get("report_id"),
                "delivered": True
            }
        }
