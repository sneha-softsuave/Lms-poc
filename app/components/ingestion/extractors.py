"""Text extraction with provenance for PDF / DOCX / PPTX / TXT / images.

Every extractor returns an ``ExtractedDoc`` whose ``segments`` each carry a
``page`` and ``section`` so downstream lessons, glossary, quiz rationales and
vector chunks can all cite ``{doc, section, page}`` (PRD 4.1.1 / 4.5 provenance).

OCR is a fallback: a PDF page (or image) whose embedded text is below
``OCR_THRESHOLD`` chars is re-read with Tesseract. Heavier engines (EasyOCR,
Docling) can slot in behind the same interface in the air-gap phase.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

OCR_THRESHOLD = 50  # min chars on a page before OCR fallback kicks in


@dataclass
class Segment:
    text: str
    page: int | None = None
    section: str | None = None


@dataclass
class ExtractedDoc:
    text: str
    method: str
    char_count: int
    segments: list[Segment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _ocr_image_bytes(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image

        from app.core.config import settings

        if settings.TESSERACT_PATH:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
        return pytesseract.image_to_string(Image.open(io.BytesIO(data))).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed: %s", exc)
        return ""


def extract_txt(data: bytes) -> ExtractedDoc:
    text = data.decode("utf-8", errors="replace").strip()
    return ExtractedDoc(text, "text", len(text), [Segment(text, page=1)])


def extract_docx(data: bytes) -> ExtractedDoc:
    import docx  # python-docx

    document = docx.Document(io.BytesIO(data))
    segments: list[Segment] = []
    current_section = None
    for para in document.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if style.startswith("heading") or style == "title":
            current_section = t
        segments.append(Segment(t, page=None, section=current_section))
    text = "\n".join(s.text for s in segments)
    return ExtractedDoc(text, "docx", len(text), segments)


def extract_pptx(data: bytes) -> ExtractedDoc:
    from pptx import Presentation  # python-pptx

    prs = Presentation(io.BytesIO(data))
    segments: list[Segment] = []
    for idx, slide in enumerate(prs.slides, start=1):
        title = None
        if slide.shapes.title and slide.shapes.title.text:
            title = slide.shapes.title.text.strip()
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text.strip())
        slide_text = "\n".join(parts)
        if slide_text:
            # Slides map to "page" so provenance reads naturally in citations.
            segments.append(Segment(slide_text, page=idx, section=title or f"Slide {idx}"))
    text = "\n".join(s.text for s in segments)
    return ExtractedDoc(text, "pptx", len(text), segments)


def extract_pdf(data: bytes) -> ExtractedDoc:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    segments: list[Segment] = []
    warnings: list[str] = []
    method = "pdf-text"
    ocr_images = None  # lazy pdf2image conversion, only if needed

    for page_no, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if len(page_text) < OCR_THRESHOLD:
            # Scanned/empty page → OCR fallback.
            if ocr_images is None:
                ocr_images = _pdf_to_images(data, warnings)
            if ocr_images and page_no <= len(ocr_images):
                ocr_text = _ocr_image_bytes(ocr_images[page_no - 1])
                if len(ocr_text) > len(page_text):
                    page_text = ocr_text
                    method = "pdf-ocr"
        if page_text:
            segments.append(Segment(page_text, page=page_no))

    text = "\n".join(s.text for s in segments)
    return ExtractedDoc(text, method, len(text), segments, warnings)


def _pdf_to_images(data: bytes, warnings: list[str]) -> list[bytes]:
    try:
        from pdf2image import convert_from_bytes

        from app.core.config import settings

        kwargs = {"poppler_path": settings.POPPLER_PATH} if settings.POPPLER_PATH else {}
        images = convert_from_bytes(data, **kwargs)
        out = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            out.append(buf.getvalue())
        return out
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"PDF OCR unavailable: {exc}")
        return []


def extract_image(data: bytes) -> ExtractedDoc:
    text = _ocr_image_bytes(data)
    return ExtractedDoc(text, "image-ocr", len(text), [Segment(text, page=1)] if text else [])


# MIME / extension → extractor
_EXTRACTORS = {
    "txt": extract_txt,
    "text/plain": extract_txt,
    "docx": extract_docx,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_docx,
    "pptx": extract_pptx,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": extract_pptx,
    "pdf": extract_pdf,
    "application/pdf": extract_pdf,
    "png": extract_image,
    "jpg": extract_image,
    "jpeg": extract_image,
    "image/png": extract_image,
    "image/jpeg": extract_image,
}


def extract(data: bytes, *, filename: str, content_type: str | None = None) -> ExtractedDoc:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    fn = _EXTRACTORS.get(ext) or (_EXTRACTORS.get(content_type or "") if content_type else None)
    if fn is None:
        raise ValueError(f"Unsupported file type: filename={filename!r} content_type={content_type!r}")
    return fn(data)
