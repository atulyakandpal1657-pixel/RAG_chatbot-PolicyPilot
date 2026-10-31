import io
import logging
from pathlib import Path
from typing import Dict, List, Union

logger = logging.getLogger(__name__)


def extract_pages_from_pdf(content: bytes, filename: str) -> List[Dict[str, Union[int, str]]]:
    """
    Extracts text per page from PDF using PyMuPDF (fitz).
    Returns list of dicts: [{"page_number": 1, "text": "..."}, ...]
    """
    import fitz  # PyMuPDF

    pages = []
    doc = fitz.open(stream=content, filetype="pdf")
    total_pages = len(doc)
    
    total_chars = 0
    for page_idx in range(total_pages):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        total_chars += len(text)
        pages.append({
            "page_number": page_idx + 1,
            "text": text
        })
    doc.close()

    if total_chars == 0:
        logger.warning(
            f"File '{filename}' yielded 0 extractable characters across {total_pages} pages. "
            "It may be a scanned or image-only PDF."
        )

    return pages


def extract_pages_from_docx(content: bytes, filename: str) -> List[Dict[str, Union[int, str]]]:
    """
    Extracts text from DOCX files, detecting page breaks or segmenting by size.
    Returns list of dicts: [{"page_number": 1, "text": "..."}, ...]
    """
    import docx

    doc = docx.Document(io.BytesIO(content))
    pages: List[Dict[str, Union[int, str]]] = []
    current_page_text: List[str] = []
    current_page_num = 1
    current_page_len = 0

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        
        # Check if paragraph has a page break run
        has_page_break = False
        for run in paragraph.runs:
            if "\f" in run.text or "w:br" in run._r.xml:
                has_page_break = True
                break

        current_page_text.append(text)
        current_page_len += len(text)

        # Split on explicit break or approximate page (~2500 characters)
        if has_page_break or current_page_len >= 2500:
            pages.append({
                "page_number": current_page_num,
                "text": "\n\n".join(current_page_text)
            })
            current_page_text = []
            current_page_len = 0
            current_page_num += 1

    if current_page_text:
        pages.append({
            "page_number": current_page_num,
            "text": "\n\n".join(current_page_text)
        })

    if not pages:
        pages.append({"page_number": 1, "text": ""})

    return pages


def extract_pages_from_txt(content: bytes, filename: str) -> List[Dict[str, Union[int, str]]]:
    """
    Extracts text from plain text or markdown files.
    Respects form-feed page markers '\\f' or splits into 2500-character pages.
    """
    text = content.decode("utf-8", errors="replace").strip()
    if "\f" in text:
        raw_pages = text.split("\f")
        pages = [
            {"page_number": i + 1, "text": p.strip()}
            for i, p in enumerate(raw_pages)
            if p.strip()
        ]
        return pages if pages else [{"page_number": 1, "text": text}]

    # Approximate pages by ~2500 characters on paragraph boundaries
    paragraphs = text.split("\n\n")
    pages = []
    current_page_paragraphs: List[str] = []
    current_len = 0
    page_num = 1

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        current_page_paragraphs.append(p_clean)
        current_len += len(p_clean)
        if current_len >= 2500:
            pages.append({
                "page_number": page_num,
                "text": "\n\n".join(current_page_paragraphs)
            })
            current_page_paragraphs = []
            current_len = 0
            page_num += 1

    if current_page_paragraphs:
        pages.append({
            "page_number": page_num,
            "text": "\n\n".join(current_page_paragraphs)
        })

    return pages if pages else [{"page_number": 1, "text": ""}]


def parse_document(content: bytes, filename: str) -> List[Dict[str, Union[int, str]]]:
    """
    Dispatches file parsing according to file extension.
    Returns list of {"page_number": int, "text": str}.
    Raises ValueError on unsupported formats.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_pages_from_pdf(content, filename)
    elif ext in [".docx", ".doc"]:
        return extract_pages_from_docx(content, filename)
    elif ext in [".txt", ".md", ".markdown"]:
        return extract_pages_from_txt(content, filename)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported types: .pdf, .docx, .txt, .md")
