from datetime import timedelta
from typing import Optional

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.provider import StorageProvider


class GCSStorageProvider(StorageProvider):
    """
    Google Cloud Storage Provider for Production.
    Uses private GCS buckets with least-privilege Workload Identity runtime credentials.
    Generates short-lived 15-minute signed URLs for authorized access.
    """

    def __init__(self, bucket_name: str = None, client = None):
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME
        self._client = client

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import storage
                self._client = storage.Client()
            except Exception as e:
                logger.error(f"[GCS STORAGE] Failed to initialize GCS client: {str(e)}")
                raise DomainException("GCS Storage Client initialization failed", code="STORAGE_INIT_FAILED")
        return self._client

    async def upload_file(self, file_bytes: bytes, destination_path: str, content_type: str = "application/pdf") -> str:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(destination_path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        logger.info(f"[GCS STORAGE] Uploaded object gs://{self.bucket_name}/{destination_path}")
        return destination_path

    async def download_file(self, storage_path: str) -> bytes:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(storage_path)
        if not blob.exists():
            raise FileNotFoundError(f"GCS object not found: gs://{self.bucket_name}/{storage_path}")
        return blob.download_as_bytes()

    async def delete_file(self, storage_path: str) -> bool:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(storage_path)
        if blob.exists():
            blob.delete()
            logger.info(f"[GCS STORAGE] Deleted object gs://{self.bucket_name}/{storage_path}")
            return True
        return False

    async def exists(self, storage_path: str) -> bool:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(storage_path)
        return blob.exists()

    async def get_download_url(self, storage_path: str, expires_in_seconds: int = 900) -> Optional[str]:
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(storage_path)
        if not blob.exists():
            return None
        # Generate 15-minute V4 signed URL for private bucket access
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expires_in_seconds),
            method="GET"
        )
        return url
