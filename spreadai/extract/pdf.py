"""Read text from a PDF, then parse it.

For a normal (text) PDF, pdfplumber reads the text directly. For a scanned PDF
(an image), there is no text to read, so we need OCR. OCR is optional: it needs
the ``spreadai[ocr]`` extra and the system ``tesseract`` binary. If OCR is not
available and the PDF has no text, we raise a clear error instead of returning
nothing.
"""

from __future__ import annotations

from pathlib import Path

from .base import ExtractionResult
from .text_parser import parse_text


def extract_text_from_pdf(path: str | Path) -> str:
    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages).strip()


def ocr_pdf(path: str | Path) -> str:
    """OCR a scanned PDF. Needs the 'ocr' extra and the tesseract binary."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "OCR needs the optional extra and tesseract: "
            "pip install 'spreadai[ocr]' and install the tesseract binary."
        ) from exc
    images = convert_from_path(str(path))
    return "\n".join(pytesseract.image_to_string(img) for img in images).strip()


def parse_pdf(path: str | Path, use_ocr_fallback: bool = True) -> ExtractionResult:
    """Extract text from a PDF (OCR if it is scanned) and parse it."""
    text = extract_text_from_pdf(path)
    if not text and use_ocr_fallback:
        text = ocr_pdf(path)
    if not text:
        raise RuntimeError(f"No text found in {path}. It may be a scanned PDF; enable OCR.")
    result = parse_text(text)
    result.method = "pdf"
    return result
