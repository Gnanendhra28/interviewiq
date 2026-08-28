import os

import aiofiles

from apps.api.app.core.config import settings
from apps.api.app.core.logging import logger
from apps.api.app.core.storage.provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str = None):
        self.base_path = base_path or settings.STORAGE_LOCAL_PATH
        os.makedirs(self.base_path, exist_ok=True)

    async def upload_file(
        self,
        file_bytes: bytes,
        destination_path: str,
        content_type: str = "application/pdf",
    ) -> str:
        full_path = os.path.join(self.base_path, destination_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_bytes)
        logger.info(f"File stored locally at: {full_path}")
        return full_path

    async def download_file(self, storage_path: str) -> bytes:
        async with aiofiles.open(storage_path, "rb") as f:
            return await f.read()

    async def delete_file(self, storage_path: str) -> bool:
        if os.path.exists(storage_path):
            os.remove(storage_path)
            return True
        return False
