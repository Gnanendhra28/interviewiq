from apps.api.app.core.exceptions import DomainException
from apps.api.app.modules.resumes.domain.parser.docx_parser import DOCXParser
from apps.api.app.modules.resumes.domain.parser.pdf_parser import PDFParser
from apps.api.app.modules.resumes.domain.parser.provider import DocumentParserProvider


def get_document_parser(file_type: str) -> DocumentParserProvider:
    ft = file_type.upper().strip()
    if ft == "PDF":
        return PDFParser()
    elif ft == "DOCX":
        return DOCXParser()
    else:
        raise DomainException(f"Unsupported document parser type: '{file_type}'", code="UNSUPPORTED_PARSER_TYPE")
