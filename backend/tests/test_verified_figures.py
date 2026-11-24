import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services.llm_service import _build_agent_final_prompt
from app.services.pdf_service import DOCUMENT_STORE
from app.services.sample_service import SAMPLE_PATH
from app.services.verified_figures_service import build_verified_figures, format_for_prompt, select_keys


def doc(*pages):
    return {"page_texts": [{"page": i + 1, "text": "\n".join(lines)} for i, lines in enumerate(pages)]}


PL_LINES = [
    "Standalone Statement of Profit and Loss for the year ended 31st March, 2026", "\u20b9 Crore", "Particulars", "Notes", "2025-26", "2024-25",
    "I.", "\x07Revenue from operations", "18", "7,193.23", "7,028.29",
    "II.", "\x07Other income", "19", "62.36", "64.23",
    "III.\t \x07Total Income (I+II)", "7,255.59", "7,092.52",
    "Finance costs", "24", "42.24", "55.29",
    "Depreciation and amortisation expense", "2 G", "102.34", "84.21",
    "\x07Total Expenses (IV)", "6,591.67", "6,336.93",
    "V. Profit before exceptional items and", "tax (III-IV)", "663.92", "755.59",
    "Exceptional items", "26", "754.85", "-",
    "VI. Profit/ (loss) before tax", "(90.93)", "755.59",
    "VIII. Profit/ (loss) for the year (VI-VII)", "(243.31)", "563.18",
    "Profit for the year", "-", "-",
]


class SelectionTest(unittest.TestCase):
    def test_keywords_pick_the_relevant_items(self):
        items, metrics = select_keys("What were the finance costs?")
        self.assertEqual(items, ["finance_costs"])
        self.assertEqual(metrics, ["interest_coverage"])

    def test_borrowing_questions_pick_debt_metrics(self):
        items, metrics = select_keys("How much debt does the company have?")
        self.assertIn("borrowings_current", items)
        self.assertIn("debt_equity_ratio", metrics)

    def test_broad_or_unmatched_questions_get_the_core_set(self):
        for question in ("Why did profit fall although revenue grew?", "Tell me about this company"):
            items, metrics = select_keys(question)
            self.assertIn("revenue_from_operations", items)
            self.assertIn("profit_for_the_year", items)
            self.assertIn("debt_equity_ratio", metrics)


class BuildFiguresTest(unittest.TestCase):
    def two_basis_doc(self):
        consolidated = [PL_LINES[0].replace("Standalone", "Consolidated")] + [
            line.replace("42.24", "44.03").replace("7,193.23", "8,095.52") for line in PL_LINES[1:]]
        return doc(PL_LINES, consolidated)

    def test_unspecified_basis_returns_both(self):
        output = build_verified_figures(self.two_basis_doc(), "What were the finance costs?")
        found = {(f["basis"], f["current"]) for f in output["figures"] if f["key"] == "finance_costs"}
        self.assertEqual(found, {("standalone", 42.24), ("consolidated", 44.03)})
        self.assertEqual(output["tool"], "get_verified_figures")

    def test_question_naming_a_basis_returns_only_that_basis(self):
        output = build_verified_figures(self.two_basis_doc(), "What were the consolidated finance costs?")
        self.assertEqual({f["basis"] for f in output["figures"]}, {"consolidated"})
        output = build_verified_figures(self.two_basis_doc(), "Standalone finance costs please")
        self.assertEqual({f["basis"] for f in output["figures"]}, {"standalone"})

    def test_every_figure_carries_its_page(self):
        output = build_verified_figures(self.two_basis_doc(), "What was revenue?")
        self.assertTrue(output["figures"])
        self.assertTrue(all(isinstance(f["page"], int) for f in output["figures"]))

    def test_document_without_statements_is_a_clean_empty_result(self):
        output = build_verified_figures(doc(["Just a letter."]), "What was revenue?")
        self.assertEqual((output["figures"], output["metrics"]), ([], []))
        self.assertIn("No financial statements", output["note"])

    def test_extraction_errors_never_break_the_agent(self):
        with patch("app.services.verified_figures_service.extract_financial_statements", side_effect=RuntimeError("boom")):
            output = build_verified_figures(doc(PL_LINES), "What was revenue?")
        self.assertEqual(output["figures"], [])
        self.assertIn("could not be read", output["note"])


class PromptTest(unittest.TestCase):
    SOURCES = [{"page": 3, "chunk_id": "p3-c0", "excerpt": "Some passage."}]

    def test_prompt_includes_verified_figures_with_pages_and_basis_rules(self):
        verified = build_verified_figures(doc(PL_LINES), "What were the finance costs?")
        trace = [{"tool": "get_verified_figures", "status": "success", "output": verified}]
        prompt = _build_agent_final_prompt("What were the finance costs?", self.SOURCES, [], trace, "r.pdf", verified_figures=verified)
        self.assertIn("Verified statement figures", prompt)
        self.assertIn("Finance costs", prompt)
        self.assertIn("42.24", prompt)
        self.assertIn("statement page 1", prompt)
        self.assertIn("standalone or consolidated", prompt)
        self.assertEqual(prompt.count("42.24"), 1)  # not duplicated through the tool trace

    def test_prompt_is_unchanged_in_shape_without_figures(self):
        prompt = _build_agent_final_prompt("Q?", self.SOURCES, [], [], "r.pdf")
        self.assertNotIn("Verified statement figures", prompt)
        self.assertIn("Retrieved passages", prompt)

    def test_format_returns_empty_text_when_nothing_found(self):
        self.assertEqual(format_for_prompt(None), "")
        self.assertEqual(format_for_prompt({"figures": [], "metrics": []}), "")


@unittest.skipUnless(SAMPLE_PATH.is_file(), "sample PDF not installed in backend/sample_data")
class AgentIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("FINAGENT_DB_PATH")
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-verified.sqlite3"
        self._clean()
        os.environ["FINAGENT_DB_PATH"] = str(self.db)
        DOCUMENT_STORE.clear()
        self.client = create_app().test_client()

    def tearDown(self):
        DOCUMENT_STORE.clear()
        if self.previous is None:
            os.environ.pop("FINAGENT_DB_PATH", None)
        else:
            os.environ["FINAGENT_DB_PATH"] = self.previous
        self._clean()

    def _clean(self):
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.db}{suffix}").unlink(missing_ok=True)

    def run_agent(self, document_id, question):
        plan = {"success": True, "configured": True, "status": "planned", "provider": "t", "model": "t", "tool_calls": [], "limitations": []}
        final = {"success": True, "configured": True, "status": "analyzed", "provider": "t", "model": "t", "answer": "ok", "disclaimer": "d"}
        with (patch("app.services.agent_service.generate_analysis_tool_plan", return_value=plan),
              patch("app.services.agent_service.generate_agent_final_answer", return_value=final) as mocked_final):
            response = self.client.post(f"/api/documents/{document_id}/analyze", json={"question": question})
        return response, mocked_final

    def test_agent_always_runs_the_tool_and_hands_exact_figures_to_the_answer_step(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        response, mocked_final = self.run_agent(document_id, "What were the finance costs?")
        self.assertEqual(response.status_code, 200)
        self.assertIn("get_verified_figures", [t["tool"] for t in response.json["tools_executed"]])
        figures = {(f["basis"], f["current"], f["previous"], f["page"]) for f in response.json["verified_figures"]["figures"]
                   if f["key"] == "finance_costs"}
        self.assertEqual(figures, {("standalone", 56.0, 40.0, 8), ("consolidated", 70.0, 48.0, 10)})
        self.assertEqual(mocked_final.call_args.kwargs["verified_figures"]["bases"], ["standalone", "consolidated"])

    def test_basis_in_the_question_is_respected_end_to_end(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        response, _ = self.run_agent(document_id, "What were the consolidated finance costs?")
        self.assertEqual({f["basis"] for f in response.json["verified_figures"]["figures"]}, {"consolidated"})

    def test_documents_without_statements_still_work(self):
        pdf = fitz.open()
        pdf.new_page().insert_text((72, 72), "Revenue from operations grew strongly this year according to management.")
        data = pdf.tobytes()
        pdf.close()
        document_id = self.client.post("/api/upload", data={"file": (io.BytesIO(data), "letter.pdf")},
                                       content_type="multipart/form-data").json["document_id"]
        response, _ = self.run_agent(document_id, "How did revenue from operations do?")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["verified_figures"]["figures"], [])

    def test_refusals_do_not_run_any_tools(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        response, _ = self.run_agent(document_id, "Should I buy this stock?")
        self.assertEqual(response.json["tools_executed"], [])


if __name__ == "__main__":
    unittest.main()
