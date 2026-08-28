from abc import ABC, abstractmethod


class DocumentParserProvider(ABC):
    """
    Abstract interface for document text extraction.
    Decouples PDF, DOCX, and future parser implementations from worker execution loops.
    """

    @abstractmethod
    def parse_document(self, file_bytes: bytes) -> str:
        """Extracts plain text content from raw document bytes."""
        pass
