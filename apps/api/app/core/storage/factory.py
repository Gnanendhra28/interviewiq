from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.storage.gcs_storage import GCSStorageProvider
from apps.api.app.core.storage.local_storage import LocalStorageProvider
from apps.api.app.core.storage.provider import StorageProvider

_storage_provider_instance: StorageProvider = None


def get_storage_provider() -> StorageProvider:
    global _storage_provider_instance
    if _storage_provider_instance is not None:
        return _storage_provider_instance

    provider_type = settings.STORAGE_PROVIDER.lower().strip()
    if provider_type == "local":
        _storage_provider_instance = LocalStorageProvider()
    elif provider_type == "gcs":
        _storage_provider_instance = GCSStorageProvider()
    else:
        raise DomainException(
            f"Unsupported STORAGE_PROVIDER configuration: '{settings.STORAGE_PROVIDER}'. Must be 'local' or 'gcs'.",
            code="INVALID_STORAGE_CONFIG"
        )
    return _storage_provider_instance
