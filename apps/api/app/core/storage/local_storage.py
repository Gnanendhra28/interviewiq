import asyncio
import os
from typing import Optional

from apps.api.app.core.config import settings
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.STORAGE_LOCAL_PATH
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve_full_path(self, storage_path: str) -> str:
        # Prevent path traversal
        normalized = os.path.normpath(storage_path).lstrip("/\\")
        full_path = os.path.abspath(os.path.join(self.base_path, normalized))
        base_abs = os.path.abspath(self.base_path)
        if not full_path.startswith(base_abs):
            raise ValueError("Path traversal attempt detected in storage path")
        return full_path

    async def upload_file(self, file_bytes: bytes, destination_path: str, content_type: str = "application/pdf") -> str:
        full_path = self._resolve_full_path(destination_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        def _write():
            with open(full_path, "wb") as f:
                f.write(file_bytes)

        await asyncio.to_thread(_write)
        logger.info(f"[LOCAL STORAGE] Stored file at: {full_path}")
        return destination_path

    async def download_file(self, storage_path: str) -> bytes:
        full_path = self._resolve_full_path(storage_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Local storage object not found: {storage_path}")

        def _read():
            with open(full_path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def delete_file(self, storage_path: str) -> bool:
        full_path = self._resolve_full_path(storage_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.info(f"[LOCAL STORAGE] Deleted file at: {full_path}")
            return True
        return False

    async def exists(self, storage_path: str) -> bool:
        full_path = self._resolve_full_path(storage_path)
        return os.path.exists(full_path)

    async def get_download_url(self, storage_path: str, expires_in_seconds: int = 900) -> Optional[str]:
        full_path = self._resolve_full_path(storage_path)
        if os.path.exists(full_path):
            return f"/api/v1/resumes/local-file-proxy?path={storage_path}"
        return None
