import re
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from uuid import uuid4

import fitz
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .persistence_service import save_document

ALLOWED_MIME_TYPES = {"application/pdf", "application/x-pdf"}
LOW_TEXT_WORD_THRESHOLD = 25
PREVIEW_WORD_LIMIT = 80
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
CHUNK_WORD_LIMIT = 180
CHUNK_WORD_OVERLAP = 40

FINANCIAL_TERMS = [
    "revenue",
    "net income",
    "profit",
    "loss",
    "assets",
    "liabilities",
    "equity",
    "cash flow",
    "operating income",
    "expenses",
    "debt",
    "earnings",
    "margin",
    "risk",
    "investment",
    "stock",
    "shareholder",
]

DOCUMENT_STORE: dict[str, dict] = {}


class PDFProcessingError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _is_pdf_upload(file: FileStorage, filename: str) -> bool:
    extension_ok = Path(filename).suffix.lower() == ".pdf"
    mimetype_ok = file.mimetype in ALLOWED_MIME_TYPES or file.mimetype == ""
    return extension_ok and mimetype_ok


def _copy_to_temp(source: BinaryIO) -> str:
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        source.seek(0)
        total_bytes = 0
        while chunk := source.read(1024 * 1024):
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise PDFProcessingError("PDF files must be 25 MB or smaller.", 413)
            temp_file.write(chunk)
        return temp_file.name


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _clean_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}

    cleaned = {}
    for key, value in metadata.items():
        if value not in (None, ""):
            cleaned[key] = str(value)
    return cleaned


def _extract_preview(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""

    words = normalized.split()
    preview = " ".join(words[:PREVIEW_WORD_LIMIT])
    return f"{preview}..." if len(words) > PREVIEW_WORD_LIMIT else preview


def _detect_financial_topics(text: str) -> list[dict]:
    results = []
    for term in FINANCIAL_TERMS:
        escaped_term = re.escape(term).replace(r"\ ", r"\s+")
        pattern = rf"\b{escaped_term}\b"
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if count:
            results.append(
                {
                    "term": term.title(),
                    "count": count,
                }
            )

    return sorted(results, key=lambda item: (-item["count"], item["term"]))


def _build_page_chunks(page_texts: list[str]) -> list[dict]:
    chunks = []

    for page_number, page_text in enumerate(page_texts, start=1):
        words = page_text.split()
        if not words:
            continue

        start = 0
        chunk_index = 1
        step = max(CHUNK_WORD_LIMIT - CHUNK_WORD_OVERLAP, 1)

        while start < len(words):
            chunk_words = words[start : start + CHUNK_WORD_LIMIT]
            chunk_text = " ".join(chunk_words)

            if chunk_text.strip():
                chunks.append(
                    {
                        "chunk_id": f"p{page_number}-c{chunk_index}",
                        "page": page_number,
                        "text": chunk_text,
                        "word_count": len(chunk_words),
                    }
                )

            if start + CHUNK_WORD_LIMIT >= len(words):
                break

            start += step
            chunk_index += 1

    return chunks


def get_processed_document(document_id: str) -> dict | None:
    return DOCUMENT_STORE.get(document_id)


def process_pdf_upload(file: FileStorage) -> dict:
    if not file or not file.filename:
        raise PDFProcessingError("Please select a PDF file to upload.")

    filename = secure_filename(file.filename)
    if not filename:
        raise PDFProcessingError("The uploaded file has an invalid filename.")

    if not _is_pdf_upload(file, filename):
        raise PDFProcessingError("Only PDF files are supported.")

    temp_path = _copy_to_temp(file.stream)

    try:
        with fitz.open(temp_path) as document:
            page_count = document.page_count
            if page_count == 0:
                raise PDFProcessingError("The PDF does not contain any pages.", 422)

            metadata = _clean_metadata(document.metadata)
            page_statistics = []
            page_texts = []

            for page_index, page in enumerate(document, start=1):
                page_text = page.get_text()
                character_count = len(page_text)
                word_count = _count_words(page_text)
                page_texts.append(page_text)
                page_statistics.append(
                    {
                        "page": page_index,
                        "characters": character_count,
                        "words": word_count,
                        "has_text": bool(page_text.strip()),
                        "low_text": word_count < LOW_TEXT_WORD_THRESHOLD,
                    }
                )

            extracted_text = "\n\n".join(page_texts)
    except Exception as exc:
        if isinstance(exc, PDFProcessingError):
            raise
        raise PDFProcessingError("The PDF could not be processed.", 422) from exc
    finally:
        Path(temp_path).unlink(missing_ok=True)

    total_characters = len(extracted_text)
    total_words = _count_words(extracted_text)
    if total_words == 0:
        raise PDFProcessingError("No readable text could be extracted from this PDF.", 422)

    document_id = str(uuid4())
    text_pages = sum(1 for page in page_statistics if page["has_text"])
    low_text_pages = [page["page"] for page in page_statistics if page["low_text"]]
    average_words_per_page = round(total_words / page_count, 2) if page_count else 0
    document_title = metadata.get("title") if metadata.get("title") else None

    response = {
        "success": True,
        "document_id": document_id,
        "filename": filename,
        "pages": page_count,
        "characters": total_characters,
        "characters_extracted": total_characters,
        "words": total_words,
        "average_words_per_page": average_words_per_page,
        "text_pages": text_pages,
        "low_text_pages": low_text_pages,
        "preview": _extract_preview(extracted_text),
        "document_title": document_title,
        "metadata": metadata,
        "page_statistics": page_statistics,
        "financial_topics": _detect_financial_topics(extracted_text),
        "status": "processed",
    }

    stored_document = {
        "document_id": document_id,
        "filename": filename,
        "text": extracted_text,
        "page_texts": [
            {
                "page": page_number,
                "text": page_text,
            }
            for page_number, page_text in enumerate(page_texts, start=1)
        ],
        "chunks": _build_page_chunks(page_texts),
        "processed_at": datetime.now(UTC).isoformat(),
        "metadata": metadata,
        "response": response,
    }
    DOCUMENT_STORE[document_id] = stored_document
    save_document(stored_document)

    return response
