import io
import json
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services import llm_service, persistence_service
from app.services.llm_service import LLMSummaryError
from app.services.pdf_service import DOCUMENT_STORE

ENV_KEYS = ("FINAGENT_DB_PATH", "LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL", "LLM_API_BASE_URL")


def http_error(code, message):
    body = json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")
    return urllib.error.HTTPError("https://example.test", code, "err", {}, io.BytesIO(body))


class GeminiErrorMessageTest(unittest.TestCase):
    def test_invalid_key_is_explained(self):
        message = llm_service._describe_gemini_http_error(http_error(400, "API key not valid. Please pass a valid API key."))
        self.assertIn("API key is not valid", message)
        self.assertIn("backend/.env", message)

    def test_status_codes_have_clear_messages(self):
        self.assertIn("quota", llm_service._describe_gemini_http_error(http_error(429, "x")).lower())
        self.assertIn("model", llm_service._describe_gemini_http_error(http_error(404, "x")).lower())
        self.assertIn("unavailable", llm_service._describe_gemini_http_error(http_error(503, "x")).lower())
        self.assertIn("permissions", llm_service._describe_gemini_http_error(http_error(403, "x")))

    def test_other_400_keeps_geminis_reason_and_never_leaks_a_key(self):
        fake_key = "AIza" + "x" * 35
        message = llm_service._describe_gemini_http_error(http_error(400, f"Bad field near {fake_key}"))
        self.assertIn("Gemini rejected the request", message)
        self.assertNotIn(fake_key, message)
        self.assertIn("[key hidden]", message)

    def test_unreadable_body_still_gives_a_message(self):
        broken = urllib.error.HTTPError("https://example.test", 400, "err", {}, io.BytesIO(b"not json"))
        self.assertEqual(llm_service._describe_gemini_http_error(broken), "Gemini rejected the request.")


class SettingsEndpointsTest(unittest.TestCase):
    def setUp(self):
        self.previous = {key: os.environ.get(key) for key in ENV_KEYS}
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-settings.sqlite3"
        self._clean()
        os.environ["FINAGENT_DB_PATH"] = str(self.db)
        for key in ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL", "LLM_API_BASE_URL"):
            os.environ.pop(key, None)
        DOCUMENT_STORE.clear()
        self.client = create_app().test_client()

    def tearDown(self):
        DOCUMENT_STORE.clear()
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._clean()

    def _clean(self):
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.db}{suffix}").unlink(missing_ok=True)

    def configure(self):
        os.environ.update({"LLM_PROVIDER": "gemini", "LLM_API_KEY": "super-secret-test-key", "LLM_MODEL": "gemini-test"})

    def test_overview_reports_status_without_exposing_the_key(self):
        self.configure()
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        body = response.json
        self.assertEqual(body["llm"], {"provider": "gemini", "model": "gemini-test", "key_configured": True, "configured": True})
        self.assertNotIn("super-secret-test-key", response.get_data(as_text=True))
        self.assertEqual(body["storage"]["counts"], {"documents": 0, "questions": 0, "results": 0})

    def test_overview_counts_saved_data(self):
        document = fitz.open()
        document.new_page().insert_text((72, 72), "Revenue from operations was 500 crore in 2025.")
        pdf_bytes = document.tobytes()
        document.close()
        upload = self.client.post("/api/upload", data={"file": (io.BytesIO(pdf_bytes), "a.pdf")},
                                  content_type="multipart/form-data")
        self.assertEqual(upload.status_code, 200)
        persistence_service.save_result(upload.json["document_id"], "summary", "AI summary", "generated", {})
        counts = self.client.get("/api/settings").json["storage"]["counts"]
        self.assertEqual(counts, {"documents": 1, "questions": 0, "results": 1})

    def test_connection_test_when_not_configured(self):
        body = self.client.post("/api/settings/test-connection").json
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "not_configured")
        self.assertIn("LLM_API_KEY", body["message"])

    def test_connection_test_success(self):
        self.configure()
        with patch("app.services.settings_service._generate_text", return_value="OK"):
            body = self.client.post("/api/settings/test-connection").json
        self.assertTrue(body["success"])
        self.assertEqual(body["status"], "ok")
        self.assertIn("latency_ms", body)
        self.assertNotIn("super-secret-test-key", json.dumps(body))

    def test_connection_test_failures_are_classified(self):
        self.configure()
        for code, expected in ((429, "quota"), (404, "model"), (400, "key_or_request"), (503, "provider_down")):
            with patch("app.services.settings_service._generate_text", side_effect=LLMSummaryError(f"problem {code}", code)):
                body = self.client.post("/api/settings/test-connection").json
            self.assertFalse(body["success"])
            self.assertEqual(body["status"], expected)
            self.assertEqual(body["message"], f"problem {code}")

    def test_old_stranded_prompt_copy_is_gone(self):
        source = Path(llm_service.__file__).read_text(encoding="utf-8")
        self.assertEqual(source.count("You are answering a question about an uploaded financial PDF"), 0)


if __name__ == "__main__":
    unittest.main()
