import io
import json
import os
import unittest
from pathlib import Path

import fitz

from app import create_app
from app.services.pdf_service import DOCUMENT_STORE
from app.services.sample_service import SAMPLE_PATH
from app.services.statement_extractor import compute_metrics, extract_financial_statements

TRUTH_PATH = Path(__file__).resolve().parents[1] / "sample_data" / "northstar_sample_truth.json"


def doc(*pages):
    return {"page_texts": [{"page": i + 1, "text": "\n".join(lines)} for i, lines in enumerate(pages)]}


def filler(count=6):
    return [x for n in range(count) for x in (f"Filler line {n}", "1.00", "2.00")]


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


class ExtractorEdgeCaseTest(unittest.TestCase):
    def values(self, result, basis="standalone", statement="profit_and_loss"):
        return result["statements"][basis][statement]["values"]

    def test_reads_messy_real_world_layout(self):
        result = extract_financial_statements(doc(PL_LINES))
        v = self.values(result)
        self.assertEqual((v["revenue_from_operations"]["current"], v["revenue_from_operations"]["previous"]), (7193.23, 7028.29))
        self.assertEqual(v["total_income"]["current"], 7255.59)                      # control char + roman numeral stripped
        self.assertEqual(v["finance_costs"]["previous"], 55.29)                        # note column skipped
        self.assertEqual(v["depreciation_amortisation"]["current"], 102.34)            # odd note "2 G" skipped
        self.assertEqual(v["profit_before_exceptional_and_tax"]["current"], 663.92)    # label wrapped onto two lines
        self.assertEqual((v["exceptional_items"]["current"], v["exceptional_items"]["previous"]), (754.85, 0.0))  # dash = nil
        self.assertEqual(v["profit_for_the_year"]["current"], -243.31)                 # "Profit/ (loss)" spacing, brackets = negative
        self.assertEqual(v["profit_for_the_year"]["previous"], 563.18)                 # later dash-only table ignored
        self.assertEqual(result["statements"]["standalone"]["profit_and_loss"]["unit"], "crore")
        self.assertEqual(result["statements"]["standalone"]["profit_and_loss"]["page"], 1)

    def test_statement_title_in_the_middle_of_the_page(self):
        lines = PL_LINES[1:] + [PL_LINES[0]]
        self.assertIn("standalone", extract_financial_statements(doc(lines))["statements"])

    def test_standalone_and_consolidated_are_kept_apart(self):
        consolidated = [PL_LINES[0].replace("Standalone", "Consolidated")] + [
            line.replace("7,193.23", "8,095.52") for line in PL_LINES[1:]]
        result = extract_financial_statements(doc(PL_LINES, consolidated))
        self.assertEqual(self.values(result, "standalone")["revenue_from_operations"]["current"], 7193.23)
        self.assertEqual(self.values(result, "consolidated")["revenue_from_operations"]["current"], 8095.52)

    def test_current_assets_section_decides_trade_receivables_and_borrowings(self):
        lines = ["Standalone Balance Sheet as at 31st March, 2026", "\u20b9 Crore", "(1) Non-current assets", "(ii) Trade receivables", "7 A", "1.08", "1.00",
                 "Total non-current assets", "2,713.60", "3,401.54", "(2) Current assets", "(a) Inventories", "6", "700.00", "650.00",
                 "(ii) Trade receivables", "7 B", "1,015.07", "900.00", "Total current assets", "2,928.51", "2,550.20",
                 "Total assets", "5,642.11", "5,951.74", "(1) Non-current liabilities", "(i)", "Borrowings", "9", "120.00", "130.00",
                 "Total non-current liabilities", "312.36", "324.79", "(2) Current liabilities", "(i)", "Borrowings", "10", "50.00", "299.81",
                 "Total current liabilities", "2,151.68", "2,022.90", "Total equity", "3,178.07", "3,604.05",
                 "TOTAL EQUITY AND LIABILITIES", "5,642.11", "5,951.74"]
        v = self.values(extract_financial_statements(doc(lines)), statement="balance_sheet")
        self.assertEqual(v["trade_receivables"]["current"], 1015.07)
        self.assertEqual((v["borrowings_non_current"]["current"], v["borrowings_current"]["previous"]), (120.0, 299.81))

    def test_whole_number_amounts_in_lakhs_are_read(self):
        lines = ["Consolidated Statement of Profit and Loss for the year ended 31 March 2026", "(in lakhs)", "Revenue from operations", "1,23,456", "1,10,000",
                 "Other income", "2,000", "1,500", "Total income", "1,25,456", "1,11,500", "Finance costs", "3,200", "2,900",
                 "Total expenses", "1,00,000", "90,000", "Profit for the year", "25,456", "21,500", "Employee benefits expense", "9,000", "8,000"]
        result = extract_financial_statements(doc(lines))
        self.assertEqual(self.values(result, "consolidated")["revenue_from_operations"]["current"], 123456.0)
        self.assertEqual(result["statements"]["consolidated"]["profit_and_loss"]["unit"], "lakh")

    def test_prose_mentioning_a_statement_is_not_mistaken_for_one(self):
        prose = ["Independent Auditor's Report", "We have audited the Balance Sheet as at 31 March 2026 and the Statement of Profit and Loss for the year then ended."] + filler()
        self.assertEqual(extract_financial_statements(doc(prose))["statements"], {})

    def test_no_statements_gives_a_warning_not_a_crash(self):
        for pages in (doc(["Just some text"]), {"page_texts": []}, {}, {"page_texts": [{"page": 1, "text": None}, {"page": None, "text": "x"}]}):
            result = extract_financial_statements(pages)
            self.assertEqual(result["statements"], {})
            self.assertTrue(result["warnings"])

    def test_cross_checks_flag_numbers_that_do_not_add_up(self):
        bad = [line.replace("6,591.67", "5,000.00") if line == "6,591.67" else line for line in PL_LINES]
        result = extract_financial_statements(doc(bad))
        self.assertTrue(any(not c["ok"] for c in result["checks"]))

    def test_metrics_are_computed_in_code_from_extracted_values(self):
        statements = extract_financial_statements(doc(PL_LINES))["statements"]
        metrics = compute_metrics(statements, "standalone")
        self.assertEqual(metrics["revenue_growth_pct"]["current"], 2.35)
        self.assertEqual(metrics["net_profit_margin_pct"]["current"], -3.38)
        self.assertEqual(metrics["interest_coverage"]["current"], 16.72)
        self.assertIn("formula", metrics["interest_coverage"])
        self.assertTrue(all("page" in item for item in metrics["interest_coverage"]["inputs"]))
        self.assertEqual(compute_metrics(statements, "consolidated"), {})


@unittest.skipUnless(SAMPLE_PATH.is_file() and TRUTH_PATH.is_file(), "sample PDF and truth file not installed in backend/sample_data")
class SampleReportAccuracyTest(unittest.TestCase):
    """Scores the extractor against the known correct answers for the fictional sample."""

    def setUp(self):
        self.truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
        pages = [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(fitz.open(SAMPLE_PATH))]
        self.result = extract_financial_statements({"page_texts": pages})
        self.statements = self.result["statements"]

    def check(self, basis, statement, key, expected):
        item = self.statements[basis][statement]["values"][key]
        self.assertAlmostEqual(item["current"], expected[0], places=2, msg=f"{basis} {key} current")
        self.assertAlmostEqual(item["previous"], expected[1], places=2, msg=f"{basis} {key} previous")

    def test_standalone_values_match_the_answer_file(self):
        s = self.truth["standalone"]
        self.check("standalone", "profit_and_loss", "revenue_from_operations", s["revenue"])
        self.check("standalone", "profit_and_loss", "profit_before_exceptional_and_tax", s["pbt_before_exceptional"])
        self.check("standalone", "profit_and_loss", "exceptional_items", s["exceptional"])
        self.check("standalone", "profit_and_loss", "profit_for_the_year", s["pat"])
        self.check("standalone", "profit_and_loss", "finance_costs", s["finance_costs"])
        self.check("standalone", "balance_sheet", "total_equity", s["total_equity"])
        self.check("standalone", "balance_sheet", "total_assets", s["total_assets"])

    def test_consolidated_values_match_and_differ_from_standalone(self):
        c = self.truth["consolidated"]
        self.check("consolidated", "profit_and_loss", "revenue_from_operations", c["revenue"])
        self.check("consolidated", "profit_and_loss", "profit_for_the_year", c["pat"])
        self.check("consolidated", "profit_and_loss", "exceptional_items", c["exceptional"])
        self.check("consolidated", "balance_sheet", "total_equity", c["total_equity"])
        self.assertNotEqual(self.statements["standalone"]["profit_and_loss"]["values"]["profit_for_the_year"]["current"],
                            self.statements["consolidated"]["profit_and_loss"]["values"]["profit_for_the_year"]["current"])

    def test_statement_pages_match_the_answer_file(self):
        pages = self.truth["pages"]
        self.assertEqual(self.statements["standalone"]["balance_sheet"]["page"], pages["standalone_bs"])
        self.assertEqual(self.statements["standalone"]["profit_and_loss"]["page"], pages["standalone_pl"])
        self.assertEqual(self.statements["consolidated"]["balance_sheet"]["page"], pages["consolidated_bs"])
        self.assertEqual(self.statements["consolidated"]["profit_and_loss"]["page"], pages["consolidated_pl"])

    def test_ratios_match_the_answer_file_and_cross_checks_pass(self):
        ratios = self.truth["ratios_fy26_fy25"]
        metrics = compute_metrics(self.statements, "standalone")
        for ours, theirs in (("debt_equity_ratio", "de"), ("current_ratio", "cr"), ("interest_coverage", "icr"),
                             ("net_profit_margin_pct", "npm"), ("ebitda_margin_pct", "ebitda_m")):
            self.assertAlmostEqual(metrics[ours]["current"], ratios[theirs][0], places=2, msg=ours)
            self.assertAlmostEqual(metrics[ours]["previous"], ratios[theirs][1], places=2, msg=ours)
        self.assertAlmostEqual(metrics["revenue_growth_pct"]["current"], self.truth["revenue_growth_pct"], places=2)
        self.assertTrue(self.result["checks"] and all(c["ok"] for c in self.result["checks"]))


@unittest.skipUnless(SAMPLE_PATH.is_file(), "sample PDF not installed in backend/sample_data")
class FinancialsEndpointTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("FINAGENT_DB_PATH")
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-financials.sqlite3"
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

    def test_endpoint_returns_statements_metrics_and_checks(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        response = self.client.get(f"/api/documents/{document_id}/financials")
        self.assertEqual(response.status_code, 200)
        body = response.json
        self.assertEqual(sorted(body["statements"]), ["consolidated", "standalone"])
        self.assertEqual(body["metrics"]["standalone"]["debt_equity_ratio"]["current"], 0.73)
        self.assertEqual(body["metrics"]["consolidated"]["debt_equity_ratio"]["current"], 0.84)
        self.assertTrue(all(c["ok"] for c in body["checks"]))

    def test_unknown_document_returns_404(self):
        self.assertEqual(self.client.get("/api/documents/nope/financials").status_code, 404)

    def test_document_without_statements_returns_a_warning(self):
        pdf = fitz.open()
        pdf.new_page().insert_text((72, 72), "A plain letter with no financial statements.")
        data = pdf.tobytes()
        pdf.close()
        document_id = self.client.post("/api/upload", data={"file": (io.BytesIO(data), "letter.pdf")},
                                       content_type="multipart/form-data").json["document_id"]
        body = self.client.get(f"/api/documents/{document_id}/financials").json
        self.assertTrue(body["success"])
        self.assertEqual(body["statements"], {})
        self.assertTrue(body["warnings"])


if __name__ == "__main__":
    unittest.main()
