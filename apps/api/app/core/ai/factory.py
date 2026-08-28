from apps.api.app.core.ai.gemini_provider import GeminiAIProvider
from apps.api.app.core.ai.provider import AIProvider
from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException

_ai_provider_instance: AIProvider = None


def get_ai_provider() -> AIProvider:
    global _ai_provider_instance
    if _ai_provider_instance is not None:
        return _ai_provider_instance

    provider_name = settings.AI_PROVIDER.lower().strip()
    if provider_name == "gemini":
        _ai_provider_instance = GeminiAIProvider()
    else:
        raise DomainException(
            f"Unsupported AI_PROVIDER configuration: '{settings.AI_PROVIDER}'. Must be 'gemini'.",
            code="INVALID_AI_CONFIG"
        )
    return _ai_provider_instance
