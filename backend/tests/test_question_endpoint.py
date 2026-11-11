import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services.pdf_service import DOCUMENT_STORE


def build_pdf(pages: list[str]) -> bytes:
    document = fitz.open()

    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)

    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


class DocumentQuestionEndpointTest(unittest.TestCase):
    def setUp(self):
        self.previous_db_path = os.environ.get("FINAGENT_DB_PATH")
        self.test_data_dir = Path(__file__).resolve().parent / "_test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.test_db_path = self.test_data_dir / "test-finagent.sqlite3"
        self._remove_test_database()
        os.environ["FINAGENT_DB_PATH"] = str(self.test_db_path)
        DOCUMENT_STORE.clear()
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        DOCUMENT_STORE.clear()
        if self.previous_db_path is None:
            os.environ.pop("FINAGENT_DB_PATH", None)
        else:
            os.environ["FINAGENT_DB_PATH"] = self.previous_db_path
        self._remove_test_database()

    def _remove_test_database(self):
        for suffix in ("", "-wal", "-shm"):
            path = Path(f"{self.test_db_path}{suffix}")
            if path.exists():
                path.unlink()

    def upload_pdf(self):
        pdf_bytes = build_pdf(
            [
                (
                    "Annual results show revenue of 120 million dollars. "
                    "Net income was 14 million dollars and margin improved."
                ),
                (
                    "Risk factors include market volatility and liquidity risk. "
                    "Debt levels remained manageable."
                ),
            ]
        )

        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(pdf_bytes), "annual-results.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        return response.json["document_id"]

    def test_question_endpoint_returns_grounded_answer_and_sources(self):
        document_id = self.upload_pdf()

        with patch("app.routes.generate_grounded_answer") as mocked_answer:
            mocked_answer.return_value = {
                "success": True,
                "configured": True,
                "status": "answered",
                "provider": "test",
                "model": "test-model",
                "answer": "Revenue was 120 million dollars (page 1).",
                "disclaimer": "AI-generated answer grounded in retrieved document excerpts. Not investment advice.",
            }

            response = self.client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "What was revenue?"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "answered")
        self.assertIn("history_id", payload)
        self.assertIn(1, payload["source_pages"])
        self.assertGreaterEqual(len(payload["sources"]), 1)
        self.assertEqual(payload["sources"][0]["page"], 1)
        self.assertIn("revenue", payload["sources"][0]["excerpt"].lower())

    def test_question_endpoint_returns_insufficient_evidence_without_llm_call(self):
        document_id = self.upload_pdf()

        with patch("app.routes.generate_grounded_answer") as mocked_answer:
            response = self.client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "What was employee headcount?"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json
        self.assertEqual(payload["status"], "insufficient_evidence")
        self.assertIn("history_id", payload)
        self.assertEqual(payload["source_pages"], [])
        mocked_answer.assert_not_called()

    def test_question_endpoint_validates_question(self):
        document_id = self.upload_pdf()

        response = self.client.post(
            f"/api/documents/{document_id}/question",
            json={"question": "   "},
        )

        self.assertEqual(response.status_code, 400)

    def test_question_endpoint_returns_not_found_for_unknown_document(self):
        response = self.client.post(
            "/api/documents/not-a-real-document/question",
            json={"question": "What was revenue?"},
        )

        self.assertEqual(response.status_code, 404)

    def test_saved_document_can_be_queried_after_store_reload(self):
        document_id = self.upload_pdf()
        self.assertIn(document_id, DOCUMENT_STORE)

        DOCUMENT_STORE.clear()
        reloaded_app = create_app()
        reloaded_client = reloaded_app.test_client()
        self.assertIn(document_id, DOCUMENT_STORE)

        with patch("app.routes.generate_grounded_answer") as mocked_answer:
            mocked_answer.return_value = {
                "success": True,
                "configured": True,
                "status": "answered",
                "provider": "test",
                "model": "test-model",
                "answer": "Revenue was 120 million dollars (page 1).",
                "disclaimer": "AI-generated answer grounded in retrieved document excerpts. Not investment advice.",
            }

            response = reloaded_client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "What was revenue?"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(1, response.json["source_pages"])

    def test_saved_documents_and_question_history_endpoints(self):
        document_id = self.upload_pdf()

        documents_response = self.client.get("/api/documents")
        self.assertEqual(documents_response.status_code, 200)
        self.assertTrue(documents_response.json["success"])
        self.assertEqual(documents_response.json["documents"][0]["document_id"], document_id)

        with patch("app.routes.generate_grounded_answer") as mocked_answer:
            mocked_answer.return_value = {
                "success": True,
                "configured": True,
                "status": "answered",
                "provider": "test",
                "model": "test-model",
                "answer": "Revenue was 120 million dollars (page 1).",
                "disclaimer": "AI-generated answer grounded in retrieved document excerpts. Not investment advice.",
            }

            self.client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "What was revenue?"},
            )

        history_response = self.client.get(f"/api/documents/{document_id}/questions")
        self.assertEqual(history_response.status_code, 200)
        self.assertTrue(history_response.json["success"])
        self.assertEqual(history_response.json["questions"][0]["question"], "What was revenue?")

    def test_summary_result_is_saved_and_retrievable(self):
        document_id = self.upload_pdf()

        with patch("app.routes.generate_document_summary") as mocked_summary:
            mocked_summary.return_value = {
                "success": True,
                "configured": True,
                "status": "generated",
                "provider": "test",
                "model": "test-model",
                "summary": "## Document Overview\nRevenue improved.",
                "disclaimer": "AI-generated summary. Not investment advice.",
            }

            summary_response = self.client.post(f"/api/documents/{document_id}/summary")

        self.assertEqual(summary_response.status_code, 200)
        result_id = summary_response.json["result_id"]

        results_response = self.client.get("/api/results")
        self.assertEqual(results_response.status_code, 200)
        self.assertEqual(results_response.json["results"][0]["id"], result_id)

        result_response = self.client.get(f"/api/results/{result_id}")
        self.assertEqual(result_response.status_code, 200)
        self.assertEqual(result_response.json["result"]["payload"]["summary"], "## Document Overview\nRevenue improved.")


if __name__ == "__main__":
    unittest.main()
