import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("interviewiq.email")


class EmailProvider(ABC):
    """Abstract interface for transactional email delivery."""

    @abstractmethod
    async def send_verification_email(self, to_email: str, raw_token: str) -> None:
        """Dispatches an email verification link."""
        pass

    @abstractmethod
    async def send_password_reset_email(self, to_email: str, raw_token: str) -> None:
        """Dispatches a password reset link."""
        pass

    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str) -> None:
        """Dispatches a generic transactional email."""
        pass


class DevConsoleEmailProvider(EmailProvider):
    """Development email provider recording deliveries to log output without exposing raw secrets."""

    async def send_verification_email(self, to_email: str, raw_token: str) -> None:
        logger.info(f"[DEV EMAIL] Verification requested for {to_email}. Token: {raw_token[:6]}***")

    async def send_password_reset_email(self, to_email: str, raw_token: str) -> None:
        logger.info(f"[DEV EMAIL] Password reset requested for {to_email}. Token: {raw_token[:6]}***")

    async def send_email(self, to_email: str, subject: str, body: str) -> None:
        logger.info(f"[DEV EMAIL] To: {to_email} | Subject: {subject} | Body: {body}")


default_email_provider = DevConsoleEmailProvider()
