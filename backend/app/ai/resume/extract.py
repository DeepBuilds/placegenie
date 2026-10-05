"""Stage 1 - text extraction from a PDF.

Only *text-based* PDFs are supported. A scanned resume (a picture of a page) contains no
text to read, and OCR is deliberately out of scope for this project.
"""
from dataclasses import dataclass
from io import BytesIO

import pdfplumber

MIN_TEXT_CHARS = 50  # fewer characters than this = effectively an empty / image-only resume


class ResumeExtractionError(Exception):
    """A problem with the PDF that the student can understand and fix."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class ExtractedPdf:
    text: str
    page_count: int


def extract_pdf_text(data: bytes, max_pages: int = 10) -> ExtractedPdf:
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                raise ResumeExtractionError("This PDF has no pages.")
            if page_count > max_pages:
                raise ResumeExtractionError(
                    f"This PDF has {page_count} pages; resumes can have at most {max_pages}."
                )
            pages = [(page.extract_text() or "") for page in pdf.pages]
    except ResumeExtractionError:
        raise
    except Exception as exc:  # pdfminer raises many different types for damaged / protected files
        name = type(exc).__name__
        if "Password" in name or "Encrypted" in name:
            raise ResumeExtractionError("This PDF is password protected. Remove the password and upload it again.") from exc
        raise ResumeExtractionError("This file could not be read as a PDF. It may be damaged.") from exc

    text = "\n".join(pages)
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise ResumeExtractionError(
            "No readable text was found in this PDF. If it is a scanned image, "
            "export or save your resume as a text-based PDF and upload that."
        )
    return ExtractedPdf(text=text, page_count=page_count)
