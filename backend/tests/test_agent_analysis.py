import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services.agent_service import analyze_document_with_agent
from app.services.financial_tools_service import (
    FinancialToolError,
    calculate_profit_margin,
    calculate_revenue_growth,
)
from app.services.pdf_service import DOCUMENT_STORE


def build_pdf(pages: list[str]) -> bytes:
    document = fitz.open()

    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)

    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


class FinancialToolsTest(unittest.TestCase):
    def test_revenue_growth_calculation(self):
        result = calculate_revenue_growth(
            prior_revenue=100,
            current_revenue=125,
            prior_label="2023 revenue",
            current_label="2024 revenue",
        )

        self.assertEqual(result["growth_percentage"], 25.0)
        self.assertEqual(result["metric"], "revenue_growth")

    def test_revenue_growth_rejects_zero_prior_revenue(self):
        with self.assertRaises(FinancialToolError):
            calculate_revenue_growth(prior_revenue=0, current_revenue=125)

    def test_profit_margin_calculation(self):
        result = calculate_profit_margin(profit=14, revenue=120)

        self.assertEqual(result["margin_percentage"], 11.67)
        self.assertEqual(result["metric"], "profit_margin")

    def test_profit_margin_rejects_zero_revenue(self):
        with self.assertRaises(FinancialToolError):
            calculate_profit_margin(profit=14, revenue=0)


class AgentAnalysisEndpointTest(unittest.TestCase):
    def setUp(self):
        self.previous_db_path = os.environ.get("FINAGENT_DB_PATH")
        self.test_data_dir = Path(__file__).resolve().parent / "_test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        self.test_db_path = self.test_data_dir / "test-finagent-agent.sqlite3"
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
                    "Annual results report revenue of 100 million dollars in 2023 "
                    "and revenue of 125 million dollars in 2024."
                ),
                (
                    "Net income was 15 million dollars in 2024. "
                    "Risk factors include customer concentration and liquidity risk."
                ),
            ]
        )

        response = self.client.post(
            "/api/upload",
            data={"file": (io.BytesIO(pdf_bytes), "agent-results.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        return response.json["document_id"]

    def test_agent_endpoint_runs_tools_and_persists_result(self):
        document_id = self.upload_pdf()

        with (
            patch("app.services.agent_service.generate_analysis_tool_plan") as mocked_plan,
            patch("app.services.agent_service.generate_agent_final_answer") as mocked_final,
        ):
            mocked_plan.return_value = {
                "success": True,
                "configured": True,
                "status": "planned",
                "provider": "test",
                "model": "test-model",
                "tool_calls": [
                    {
                        "tool": "calculate_revenue_growth",
                        "inputs": {
                            "prior_revenue": 100,
                            "current_revenue": 125,
                            "prior_label": "2023 revenue",
                            "current_label": "2024 revenue",
                            "evidence": "revenue of 100 million dollars in 2023 and revenue of 125 million dollars in 2024",
                        },
                    },
                    {
                        "tool": "calculate_profit_margin",
                        "inputs": {
                            "profit": 15,
                            "revenue": 125,
                            "profit_label": "2024 net income",
                            "revenue_label": "2024 revenue",
                            "evidence": "Net income was 15 million dollars in 2024",
                        },
                    },
                ],
                "limitations": [],
            }
            mocked_final.return_value = {
                "success": True,
                "configured": True,
                "status": "analyzed",
                "provider": "test",
                "model": "test-model",
                "answer": "Revenue grew 25% and profit margin was 12% based on document evidence.",
                "disclaimer": "AI-generated financial analysis grounded in document evidence and verified tool outputs. Not investment advice.",
            }

            response = self.client.post(
                f"/api/documents/{document_id}/analyze",
                json={"question": "Calculate revenue growth and profit margin."},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json
        self.assertTrue(payload["success"])
        self.assertEqual(payload["status"], "analyzed")
        self.assertIn("result_id", payload)
        self.assertEqual(payload["calculations"][0]["growth_percentage"], 25.0)
        self.assertEqual(payload["calculations"][1]["margin_percentage"], 12.0)
        self.assertEqual(payload["tools_executed"][0]["tool"], "search_document")
        self.assertIn(1, payload["source_pages"])

        result_response = self.client.get(f"/api/results/{payload['result_id']}")
        self.assertEqual(result_response.status_code, 200)
        self.assertEqual(
            result_response.json["result"]["payload"]["answer"],
            "Revenue grew 25% and profit margin was 12% based on document evidence.",
        )

    def test_agent_endpoint_validates_question(self):
        document_id = self.upload_pdf()

        response = self.client.post(
            f"/api/documents/{document_id}/analyze",
            json={"question": "   "},
        )

        self.assertEqual(response.status_code, 400)

    def test_agent_endpoint_returns_insufficient_evidence(self):
        document_id = self.upload_pdf()

        with patch("app.services.agent_service.generate_analysis_tool_plan") as mocked_plan:
            response = self.client.post(
                f"/api/documents/{document_id}/analyze",
                json={"question": "What was employee headcount?"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "insufficient_evidence")
        self.assertEqual(response.json["source_pages"], [])
        mocked_plan.assert_not_called()

    def test_unapproved_and_excess_tool_calls_are_bounded(self):
        document_id = self.upload_pdf()
        document = DOCUMENT_STORE[document_id]

        with (
            patch("app.services.agent_service.generate_analysis_tool_plan") as mocked_plan,
            patch("app.services.agent_service.generate_agent_final_answer") as mocked_final,
        ):
            mocked_plan.return_value = {
                "success": True,
                "configured": True,
                "status": "planned",
                "provider": "test",
                "model": "test-model",
                "tool_calls": [
                    {"tool": "run_python", "inputs": {"code": "print(1)"}},
                    {"tool": "calculate_revenue_growth", "inputs": {"prior_revenue": 100, "current_revenue": 125}},
                    {"tool": "calculate_profit_margin", "inputs": {"profit": 15, "revenue": 125}},
                    {"tool": "calculate_profit_margin", "inputs": {"profit": 1, "revenue": 2}},
                    {"tool": "calculate_profit_margin", "inputs": {"profit": 2, "revenue": 4}},
                ],
                "limitations": [],
            }
            mocked_final.return_value = {
                "success": True,
                "configured": True,
                "status": "analyzed",
                "provider": "test",
                "model": "test-model",
                "answer": "Bounded analysis complete.",
                "disclaimer": "AI-generated financial analysis grounded in document evidence and verified tool outputs. Not investment advice.",
            }

            result = analyze_document_with_agent(
                document,
                "Calculate revenue growth and profit margin from reported figures.",
            )

        self.assertEqual(len(result["tools_executed"]), 4)
        self.assertNotIn("run_python", [trace["tool"] for trace in result["tools_executed"]])
        self.assertTrue(any("Unapproved tool" in item for item in result["limitations"]))
        self.assertTrue(any("tool-call limit" in item for item in result["limitations"]))

    def test_agent_endpoint_returns_503_when_llm_unconfigured(self):
        document_id = self.upload_pdf()

        with patch("app.services.agent_service.generate_analysis_tool_plan") as mocked_plan:
            mocked_plan.return_value = {
                "success": False,
                "configured": False,
                "status": "unavailable",
                "message": "Agentic financial analysis requires an LLM API key configured in the backend environment.",
            }

            response = self.client.post(
                f"/api/documents/{document_id}/analyze",
                json={"question": "Analyze revenue."},
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json["configured"])


if __name__ == "__main__":
    unittest.main()
