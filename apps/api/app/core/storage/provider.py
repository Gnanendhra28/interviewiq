from abc import ABC, abstractmethod
from typing import Optional


class StorageProvider(ABC):
    """
    Abstract Storage Provider Interface.
    Decouples storage (Local Filesystem for dev, GCS for prod).
    """

    @abstractmethod
    async def upload_file(self, file_bytes: bytes, destination_path: str, content_type: str = "application/pdf") -> str:
        """Upload file to storage target and return storage reference key."""
        pass

    @abstractmethod
    async def download_file(self, storage_path: str) -> bytes:
        """Download raw file bytes from storage reference path."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage target."""
        pass

    @abstractmethod
    async def exists(self, storage_path: str) -> bool:
        """Check if file exists at storage target."""
        pass

    @abstractmethod
    async def get_download_url(self, storage_path: str, expires_in_seconds: int = 900) -> Optional[str]:
        """Generate a short-lived download URL or path reference."""
        pass
