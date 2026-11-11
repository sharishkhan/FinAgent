import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services.guards import (
    check_company_mismatch,
    check_investment_advice,
    check_question_guards,
    detect_document_company,
)
from app.services.pdf_service import DOCUMENT_STORE


def build_pdf(pages):
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def make_document():
    text = (
        "Northstar Components Limited Annual Report. Northstar Components Limited "
        "reported revenue from operations of 500 crore. Standalone and Consolidated results."
    )
    return {"text": text, "page_texts": [{"page": 1, "text": text}], "chunks": []}


class InvestmentAdviceGuardTest(unittest.TestCase):
    def test_advice_questions_are_declined(self):
        for question in [
            "Should I buy this stock?",
            "Is this a good investment?",
            "Will the share price go up next year?",
            "Do you recommend buying Northstar?",
            "What is the target price?",
        ]:
            self.assertIsNotNone(check_investment_advice(question), question)

    def test_normal_financial_questions_are_not_declined(self):
        for question in [
            "What was revenue from operations?",
            "How many shares were issued under ESOP?",
            "What is the share capital?",
            "What was the dividend per share?",
        ]:
            self.assertIsNone(check_investment_advice(question), question)


class CompanyMismatchGuardTest(unittest.TestCase):
    def test_detects_company_name_from_first_pages(self):
        self.assertEqual(detect_document_company(make_document()), "Northstar Components")

    def test_other_company_is_declined(self):
        document = make_document()
        for question in [
            "What was Voltas's revenue?",
            "What was the revenue of Voltas?",
            "How did Voltas perform?",
        ]:
            message = check_company_mismatch(document, question)
            self.assertIsNotNone(message, question)
            self.assertIn("Voltas", message)

    def test_own_company_and_shortened_names_are_allowed(self):
        document = make_document()
        for question in [
            "What was Northstar's revenue?",
            "What was the revenue of Northstar Components?",
            "What was the revenue of Northstar Industries?",
            "What was the standalone revenue?",
            "What was revenue for FY2025-26?",
        ]:
            self.assertIsNone(check_company_mismatch(document, question), question)

    def test_guard_never_raises_on_odd_input(self):
        self.assertIsNone(check_question_guards({}, ""))
        self.assertIsNone(check_question_guards({"chunks": None}, "What was revenue?"))


class GuardEndpointTest(unittest.TestCase):
    def setUp(self):
        self.previous_db_path = os.environ.get("FINAGENT_DB_PATH")
        self.test_data_dir = Path(__file__).resolve().parent / "_test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.test_db_path = self.test_data_dir / "test-finagent-guards.sqlite3"
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
                "Northstar Components Limited Annual Report. Revenue from operations "
                "was 500 crore in 2025 and 450 crore in 2024.",
            ]
        )
        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(pdf_bytes), "report.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        return response.json["document_id"]

    def test_question_endpoint_declines_other_company_without_calling_llm(self):
        document_id = self.upload_pdf()
        with patch("app.routes.generate_grounded_answer") as mocked_llm:
            response = self.client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "What was Voltas's revenue?"},
            )
        mocked_llm.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "insufficient_evidence")
        self.assertEqual(response.json["sources"], [])
        self.assertIn("Voltas", response.json["answer"])

    def test_question_endpoint_declines_investment_advice(self):
        document_id = self.upload_pdf()
        with patch("app.routes.generate_grounded_answer") as mocked_llm:
            response = self.client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "Should I buy this stock?"},
            )
        mocked_llm.assert_not_called()
        self.assertEqual(response.json["status"], "insufficient_evidence")
        self.assertIn("investment advice", response.json["answer"])

    def test_question_endpoint_still_answers_normal_questions(self):
        document_id = self.upload_pdf()
        with patch("app.routes.generate_grounded_answer") as mocked_llm:
            mocked_llm.return_value = {
                "success": True,
                "configured": True,
                "status": "answered",
                "provider": "test",
                "model": "test-model",
                "answer": "Revenue was 500 crore.",
            }
            response = self.client.post(
                f"/api/documents/{document_id}/question",
                json={"question": "What was Northstar's revenue from operations?"},
            )
        mocked_llm.assert_called_once()
        self.assertEqual(response.json["status"], "answered")

    def test_agent_declines_other_company_before_any_search_or_llm_call(self):
        document_id = self.upload_pdf()
        with (
            patch("app.services.agent_service.generate_analysis_tool_plan") as mocked_plan,
            patch("app.services.agent_service.generate_agent_final_answer") as mocked_final,
        ):
            response = self.client.post(
                f"/api/documents/{document_id}/analyze",
                json={"question": "What was Voltas's revenue?"},
            )
        mocked_plan.assert_not_called()
        mocked_final.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "insufficient_evidence")
        self.assertEqual(response.json["tools_executed"], [])
        self.assertEqual(response.json["sources"], [])


if __name__ == "__main__":
    unittest.main()
