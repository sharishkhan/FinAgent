import io
import os
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services import persistence_service
from app.services.pdf_service import DOCUMENT_STORE
from app.services.sample_service import SAMPLE_PATH


def build_pdf(text):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


class DeleteTest(unittest.TestCase):
    def setUp(self):
        self.previous_db_path = os.environ.get("FINAGENT_DB_PATH")
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-delete.sqlite3"
        self._clean()
        os.environ["FINAGENT_DB_PATH"] = str(self.db)
        DOCUMENT_STORE.clear()
        self.client = create_app().test_client()

    def tearDown(self):
        DOCUMENT_STORE.clear()
        if self.previous_db_path is None:
            os.environ.pop("FINAGENT_DB_PATH", None)
        else:
            os.environ["FINAGENT_DB_PATH"] = self.previous_db_path
        self._clean()

    def _clean(self):
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.db}{suffix}").unlink(missing_ok=True)

    def upload(self, name, text):
        response = self.client.post("/api/upload", data={"file": (io.BytesIO(build_pdf(text)), name)},
                                    content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        return response.json["document_id"]

    def ask(self, document_id, question):
        with patch("app.routes.generate_grounded_answer") as llm:
            llm.return_value = {"success": True, "configured": True, "status": "answered",
                                "provider": "t", "model": "t", "answer": "ok"}
            return self.client.post(f"/api/documents/{document_id}/question", json={"question": question})

    def test_deleting_a_document_removes_it_with_its_questions_and_results(self):
        document_id = self.upload("a.pdf", "Revenue from operations was 500 crore in 2025.")
        self.ask(document_id, "What was the revenue from operations?")
        self.ask(document_id, "What was the revenue in 2025?")
        persistence_service.save_result(document_id, "summary", "AI summary", "generated", {"x": 1})

        response = self.client.delete(f"/api/documents/{document_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["deleted"], {"questions": 2, "results": 1})
        self.assertEqual(self.client.get("/api/documents").json["documents"], [])
        self.assertEqual(self.client.get("/api/results").json["results"], [])
        self.assertEqual(self.ask(document_id, "What was the revenue?").status_code, 404)

    def test_deleting_one_document_leaves_the_others_untouched(self):
        keep = self.upload("keep.pdf", "Profit after tax was 53 crore in 2026.")
        drop = self.upload("drop.pdf", "Borrowings were 720 crore in 2026.")
        self.ask(keep, "What was the profit after tax?")
        persistence_service.save_result(keep, "summary", "keep summary", "generated", {})
        persistence_service.save_result(drop, "summary", "drop summary", "generated", {})

        self.assertEqual(self.client.delete(f"/api/documents/{drop}").status_code, 200)

        documents = self.client.get("/api/documents").json["documents"]
        self.assertEqual([d["document_id"] for d in documents], [keep])
        self.assertEqual(len(self.client.get(f"/api/documents/{keep}/questions").json["questions"]), 1)
        self.assertEqual([r["title"] for r in self.client.get("/api/results").json["results"]], ["keep summary"])

    def test_unknown_document_returns_404(self):
        response = self.client.delete("/api/documents/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json["success"])

    def test_delete_is_all_or_nothing(self):
        document_id = self.upload("a.pdf", "Revenue from operations was 500 crore in 2025.")
        self.ask(document_id, "What was the revenue from operations?")
        persistence_service.save_result(document_id, "summary", "AI summary", "generated", {})
        with closing(sqlite3.connect(self.db)) as connection:  # make the final delete fail
            connection.execute("CREATE TRIGGER block_delete BEFORE DELETE ON documents "
                               "BEGIN SELECT RAISE(ABORT, 'blocked'); END")
            connection.commit()
        response = self.client.delete(f"/api/documents/{document_id}")
        self.assertEqual(response.status_code, 500)
        with closing(sqlite3.connect(self.db)) as connection:  # nothing was removed
            counts = [connection.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                      for t in ("documents", "question_history", "saved_results")]
        self.assertEqual(counts, [1, 1, 1])

    def test_deleting_one_saved_result(self):
        document_id = self.upload("a.pdf", "Revenue from operations was 500 crore in 2025.")
        first = persistence_service.save_result(document_id, "summary", "first", "generated", {})
        persistence_service.save_result(document_id, "agent_analysis", "second", "analyzed", {})
        self.assertEqual(self.client.delete(f"/api/results/{first}").status_code, 200)
        self.assertEqual([r["title"] for r in self.client.get("/api/results").json["results"]], ["second"])
        self.assertEqual(self.client.delete(f"/api/results/{first}").status_code, 404)
        self.assertEqual(len(self.client.get("/api/documents").json["documents"]), 1)

    @unittest.skipUnless(SAMPLE_PATH.is_file(), "sample PDF not installed")
    def test_sample_can_be_deleted_and_loaded_again(self):
        first = self.client.post("/api/sample-document").json["document_id"]
        self.assertEqual(self.client.delete(f"/api/documents/{first}").status_code, 200)
        again = self.client.post("/api/sample-document").json
        self.assertFalse(again["already_loaded"])
        self.assertEqual(len(self.client.get("/api/documents").json["documents"]), 1)


if __name__ == "__main__":
    unittest.main()
