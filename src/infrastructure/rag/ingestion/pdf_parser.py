"""PDF to text helper."""

from __future__ import annotations

from infrastructure.observability import get_logger

logger = get_logger("rag.pdf_parser")


def pdf_bytes_to_text(data: bytes) -> str:
    # try pymupdf then pdfminer
    try:
        import fitz  # pymupdf

        doc = fitz.open(stream=data, filetype="pdf")
        out = []
        for page in doc:
            out.append(page.get_text("text"))
        return "\n".join(out)
    except Exception as e:
        logger.warning("pymupdf failed: %s", e)
    try:
        from pdfminer.high_level import extract_text
        import io

        return extract_text(io.BytesIO(data)) or ""
    except Exception as e:
        logger.warning("pdfminer failed: %s", e)
        return ""
