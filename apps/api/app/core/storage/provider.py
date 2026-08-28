from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """
    Abstract Storage Provider Interface.
    Decouples storage (Local Filesystem for dev, GCS for prod).
    """

    @abstractmethod
    async def upload_file(
        self,
        file_bytes: bytes,
        destination_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload file to storage target and return reference URI."""
        pass

    @abstractmethod
    async def download_file(self, storage_path: str) -> bytes:
        """Download file content from storage reference path."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage target."""
        pass
