"""Loads the bundled FICTIONAL sample annual report through the normal upload pipeline.

The sample PDF lives in backend/sample_data/. It is processed by the same
process_pdf_upload() used for real uploads, so it behaves exactly like a user upload.
Clicking the sample button twice does not create a duplicate: the saved copy is reused.
"""
from pathlib import Path

from werkzeug.datastructures import FileStorage

from .pdf_service import process_pdf_upload
from .persistence_service import list_documents

SAMPLE_FILENAME = "northstar_sample_annual_report.pdf"
SAMPLE_PATH = Path(__file__).resolve().parents[2] / "sample_data" / SAMPLE_FILENAME


class SampleDocumentError(Exception):
    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message)
        self.status_code = status_code


def load_sample_document() -> dict:
    if not SAMPLE_PATH.is_file():
        raise SampleDocumentError(
            "The sample report is not installed. Add northstar_sample_annual_report.pdf "
            "to backend/sample_data/."
        )

    for document in list_documents():
        if document.get("filename") == SAMPLE_FILENAME:
            return {"success": True, "status": "already_loaded", "already_loaded": True, "sample": True, **document}

    with SAMPLE_PATH.open("rb") as handle:
        upload = FileStorage(stream=handle, filename=SAMPLE_FILENAME, content_type="application/pdf")
        result = process_pdf_upload(upload)

    result["already_loaded"] = False
    result["sample"] = True
    return result
