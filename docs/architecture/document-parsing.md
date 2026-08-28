# Document Parsing Architecture & Text Quality Inspection

## 1. Document Parser Abstraction

Document parsing is decoupled from background workers using the `DocumentParserProvider` interface (`apps/api/app/modules/resumes/domain/parser/provider.py`):

```
DocumentParserProvider Interface
 ├── PDFParser (pypdf / stream text fallback)
 └── DOCXParser (python-docx / XXE-safe zipfile XML fallback)
```

- **`PDFParser`**: Handles encrypted or password-protected PDFs gracefully, raising `ENCRYPTED_DOCUMENT` without crashing worker threads.
- **`DOCXParser`**: Extracts text from paragraphs and tables while preventing macro execution and external XML entity resolution (XXE safe).

---

## 2. Text Quality & OCR Decision Boundary

Before invoking Google Gemini AI analysis, `TextQualityValidator` evaluates extracted text:
- **Minimum Text Threshold**: $\ge 100$ characters required.
- **Maximum Noise Ratio**: Non-printable / ascii noise ratio must be $< 15\%$.

If validation fails, the document transitions to `OCR_REQUIRED` status with internal diagnostic reason `INSUFFICIENT_EXTRACTABLE_TEXT`. This defines a clean integration boundary for future Cloud Vision or Document AI OCR services without presenting unreadable documents to the LLM.
