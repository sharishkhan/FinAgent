import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.services.pdf_service import DOCUMENT_STORE
from app.services.sample_service import SAMPLE_FILENAME, SAMPLE_PATH

SAMPLE_INSTALLED = SAMPLE_PATH.is_file()


class SampleDocumentTest(unittest.TestCase):
    def setUp(self):
        self.previous_db_path = os.environ.get("FINAGENT_DB_PATH")
        self.test_data_dir = Path(__file__).resolve().parent / "_test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.test_db_path = self.test_data_dir / "test-finagent-sample.sqlite3"
        self._remove_test_database()
        os.environ["FINAGENT_DB_PATH"] = str(self.test_db_path)
        DOCUMENT_STORE.clear()
        self.client = create_app().test_client()

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

    def test_missing_sample_file_returns_clear_404(self):
        with patch("app.services.sample_service.SAMPLE_PATH", Path("does-not-exist.pdf")):
            response = self.client.post("/api/sample-document")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json["success"])
        self.assertIn("sample_data", response.json["error"])

    @unittest.skipUnless(SAMPLE_INSTALLED, "sample PDF not installed in backend/sample_data")
    def test_sample_loads_through_the_normal_pipeline(self):
        response = self.client.post("/api/sample-document")
        self.assertEqual(response.status_code, 200)
        body = response.json
        self.assertTrue(body["success"])
        self.assertTrue(body["sample"])
        self.assertFalse(body["already_loaded"])
        self.assertEqual(body["filename"], SAMPLE_FILENAME)
        self.assertEqual(body["pages"], 12)
        self.assertIn("document_id", body)

    @unittest.skipUnless(SAMPLE_INSTALLED, "sample PDF not installed in backend/sample_data")
    def test_clicking_twice_does_not_create_a_duplicate(self):
        first = self.client.post("/api/sample-document").json
        second = self.client.post("/api/sample-document").json
        self.assertTrue(second["already_loaded"])
        self.assertEqual(first["document_id"], second["document_id"])
        documents = self.client.get("/api/documents").json["documents"]
        self.assertEqual(len([d for d in documents if d["filename"] == SAMPLE_FILENAME]), 1)

    @unittest.skipUnless(SAMPLE_INSTALLED, "sample PDF not installed in backend/sample_data")
    def test_sample_supports_questions_with_page_sources(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        with patch("app.routes.generate_grounded_answer") as mocked_llm:
            mocked_llm.return_value = {"success": True, "configured": True, "status": "answered",
                                       "provider": "test", "model": "test", "answer": "Profit was 53.00 crore."}
            response = self.client.post(f"/api/documents/{document_id}/question",
                                        json={"question": "What was the profit for the year?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "answered")
        self.assertTrue(set(response.json["source_pages"]) & {8, 10})

    @unittest.skipUnless(SAMPLE_INSTALLED, "sample PDF not installed in backend/sample_data")
    def test_guards_work_on_the_sample(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        with patch("app.routes.generate_grounded_answer") as mocked_llm:
            mocked_llm.return_value = {"success": True, "configured": True, "status": "answered",
                                       "provider": "test", "model": "test", "answer": "Revenue was 2,400.00 crore."}
            other = self.client.post(f"/api/documents/{document_id}/question", json={"question": "What was Voltas's revenue?"})
            own = self.client.post(f"/api/documents/{document_id}/question", json={"question": "What was Northstar's revenue?"})
        self.assertEqual(other.json["status"], "insufficient_evidence")
        self.assertNotEqual(own.json["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
