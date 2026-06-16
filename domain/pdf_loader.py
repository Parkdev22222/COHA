"""
PDF text extractor for doctrine documents.
Requires: pip install pymupdf
"""
import logging
import os

logger = logging.getLogger(__name__)


def load_pdf_text(pdf_path: str) -> str:
    """Extract full text from a PDF file using PyMuPDF.

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        Extracted text with page separators.

    Raises:
        ImportError: If PyMuPDF (fitz) is not installed.
        FileNotFoundError: If the PDF file does not exist.
        RuntimeError: If text extraction fails.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required to read PDF doctrine files. "
            "Install with: pip install pymupdf"
        )

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        pages = []
        for i, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                pages.append(f"--- Page {i} ---\n{text.strip()}")
        doc.close()
        full_text = "\n\n".join(pages)
        logger.info(f"Loaded PDF: {pdf_path} ({len(doc)} pages, {len(full_text)} chars)")
        return full_text
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {pdf_path}: {e}") from e
