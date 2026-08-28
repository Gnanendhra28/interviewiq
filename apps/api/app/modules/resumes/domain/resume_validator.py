import hashlib
import os
from typing import Any, Dict, Optional

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import DomainException

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/x-pdf",
    "application/octet-stream" # Browser fallback for multipart upload
}

PDF_MAGIC_BYTES = b"%PDF-"
DOCX_MAGIC_BYTES = b"PK\x03\x04"


class ResumeFileValidator:
    @staticmethod
    def validate_and_inspect_resume(filename: str, content_type: Optional[str], file_bytes: bytes) -> Dict[str, Any]:
        if not file_bytes:
            raise DomainException("Uploaded file is empty", code="EMPTY_FILE")

        # 1. File Size Enforcement
        file_size = len(file_bytes)
        if file_size > settings.MAX_RESUME_SIZE_BYTES:
            max_mb = settings.MAX_RESUME_SIZE_BYTES // (1024 * 1024)
            raise DomainException(
                f"File size ({file_size} bytes) exceeds maximum limit of {max_mb} MB",
                code="FILE_TOO_LARGE"
            )

        # 2. Extension Check
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise DomainException(
                f"Unsupported file extension '{ext}'. Allowed extensions: .pdf, .docx",
                code="INVALID_FILE_EXTENSION"
            )

        # 3. Magic Bytes / File Signature Inspection
        normalized_file_type = None
        if file_bytes.startswith(PDF_MAGIC_BYTES):
            normalized_file_type = "PDF"
            canonical_mime = "application/pdf"
        elif file_bytes.startswith(DOCX_MAGIC_BYTES):
            normalized_file_type = "DOCX"
            canonical_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            raise DomainException(
                "File signature (magic bytes) mismatch for PDF or DOCX format",
                code="INVALID_FILE_SIGNATURE"
            )

        # 4. Check Extension & Magic Byte Match
        if ext == ".pdf" and normalized_file_type != "PDF":
            raise DomainException("File has .pdf extension but content is not a valid PDF document", code="FILE_FORMAT_MISMATCH")
        if ext == ".docx" and normalized_file_type != "DOCX":
            raise DomainException("File has .docx extension but content is not a valid DOCX document", code="FILE_FORMAT_MISMATCH")

        # 5. SHA-256 Checksum Calculation
        checksum_sha256 = hashlib.sha256(file_bytes).hexdigest()

        return {
            "original_filename": filename,
            "file_type": normalized_file_type,
            "mime_type": canonical_mime,
            "file_size_bytes": file_size,
            "checksum_sha256": checksum_sha256,
        }
