import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.services import llm_service
from app.services.pdf_service import DOCUMENT_STORE
from app.services.sample_service import SAMPLE_PATH

SOURCES = [
    {"page": 3, "chunk_id": "p3-c0", "excerpt": "Revenue from operations grew 20.0% to 2,400.00 crore."},
    {"page": 4, "chunk_id": "p4-c0", "excerpt": "Steel and aluminium prices rose during the year."},
]


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_gemini_reply(captured):
    def _urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        reply = {"candidates": [{"content": {"parts": [{"text": "Revenue grew 20.0% (Page 3)."}]}}]}
        return FakeResponse(json.dumps(reply).encode("utf-8"))

    return _urlopen


class QuestionPromptTest(unittest.TestCase):
    def test_prompt_is_a_real_string_with_question_and_sources(self):
        prompt = llm_service._build_question_prompt("Why did profit fall?", SOURCES, "report.pdf")
        self.assertIsInstance(prompt, str)
        self.assertIn("Why did profit fall?", prompt)
        self.assertIn("report.pdf", prompt)
        self.assertIn("Page 3", prompt)
        self.assertIn("Steel and aluminium prices rose", prompt)
        self.assertIn("ONLY", prompt)

    def test_gemini_request_never_sends_an_empty_prompt(self):
        captured = {}
        config = {"model": "gemini-test", "api_key": "test-key"}
        with patch("app.services.llm_service.urllib.request.urlopen", fake_gemini_reply(captured)):
            answer = llm_service._gemini_answer(config, "Why did profit fall?", SOURCES, "report.pdf")
        text = captured["body"]["contents"][0]["parts"][0]["text"]
        self.assertIsInstance(text, str)
        self.assertIn("Why did profit fall?", text)
        self.assertIn("Revenue from operations grew", text)
        self.assertEqual(answer, "Revenue grew 20.0% (Page 3).")


@unittest.skipUnless(SAMPLE_PATH.is_file(), "sample PDF not installed in backend/sample_data")
class ChatEndToEndWithFakeGeminiTest(unittest.TestCase):
    def setUp(self):
        self.previous = {key: os.environ.get(key) for key in ("FINAGENT_DB_PATH", "LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL")}
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-prompts.sqlite3"
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.db}{suffix}").unlink(missing_ok=True)
        os.environ.update({"FINAGENT_DB_PATH": str(self.db), "LLM_PROVIDER": "gemini", "LLM_API_KEY": "test-key", "LLM_MODEL": "gemini-test"})
        DOCUMENT_STORE.clear()
        self.client = create_app().test_client()

    def tearDown(self):
        DOCUMENT_STORE.clear()
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.db}{suffix}").unlink(missing_ok=True)

    def test_chat_question_sends_retrieved_pages_to_gemini_and_returns_the_answer(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        captured = {}
        with patch("app.services.llm_service.urllib.request.urlopen", fake_gemini_reply(captured)):
            response = self.client.post(f"/api/documents/{document_id}/question",
                                        json={"question": "Why did profit fall although revenue grew?"})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["status"], "answered")
        text = captured["body"]["contents"][0]["parts"][0]["text"]
        self.assertIn("Why did profit fall although revenue grew?", text)
        self.assertIn("Source passages", text)
        self.assertTrue(set(response.json["source_pages"]) & {3, 4})


if __name__ == "__main__":
    unittest.main()
