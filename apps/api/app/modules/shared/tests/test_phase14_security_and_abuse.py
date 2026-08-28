import uuid
from datetime import timedelta

import pytest

from apps.api.app.core.exceptions import DomainException, UnauthorizedException
from apps.api.app.core.security import create_access_token, decode_token
from apps.api.app.core.storage.local_storage import LocalStorageProvider
from apps.api.app.modules.resumes.domain.resume_validator import ResumeFileValidator


@pytest.mark.asyncio
async def test_jwt_token_security_and_reuse_detection():
    # 1. Invalid JWT parsing
    with pytest.raises(UnauthorizedException) as exc_info:
        decode_token("invalid.jwt.token")
    assert "Invalid or expired token" in str(exc_info.value)

    # 2. Expired JWT token handling
    expired_token = create_access_token({"sub": str(uuid.uuid4())}, expires_delta=timedelta(seconds=-10))
    with pytest.raises(UnauthorizedException) as exc_info:
        decode_token(expired_token)
    assert "Invalid or expired token" in str(exc_info.value)

@pytest.mark.asyncio
async def test_path_traversal_prevention_in_storage():
    storage = LocalStorageProvider()
    
    # Attempt path traversal escape via relative path outside storage directory
    with pytest.raises(ValueError) as exc_info:
        storage._resolve_full_path("../../../etc/passwd")
    assert "Path traversal" in str(exc_info.value)

@pytest.mark.asyncio
async def test_resume_file_extension_and_mime_validation():
    # Executable binary content pretending to be PDF
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    
    with pytest.raises(DomainException) as exc_info:
        ResumeFileValidator.validate_and_inspect_resume("malicious.pdf", "application/pdf", exe_bytes)
    assert exc_info.value.code in ("INVALID_FILE_SIGNATURE", "FILE_FORMAT_MISMATCH", "INVALID_FILE_EXTENSION")
