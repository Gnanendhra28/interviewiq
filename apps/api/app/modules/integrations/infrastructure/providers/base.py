from abc import ABC, abstractmethod
from typing import Any, Dict


class IntegrationProvider(ABC):
    """
    Abstract Integration Provider Base Class (ADR 046).
    Decouples third-party ATS communication from core application use cases.
    """
    @property
    @abstractmethod
    def provider_type(self) -> str:
        pass

    @abstractmethod
    async def validate_configuration(self, config: Dict[str, Any], secret: str) -> bool:
        pass

    @abstractmethod
    async def test_connection(self, config: Dict[str, Any], secret: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def deliver_hiring_decision(
        self, config: Dict[str, Any], secret: str, event_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def deliver_interview_report(
        self, config: Dict[str, Any], secret: str, event_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass
