import io
import json
import os
import unittest
from pathlib import Path

import fitz

from app import create_app
from app.services.pdf_service import DOCUMENT_STORE
from app.services.profit_walk_service import build_profit_walks, build_walk
from app.services.sample_service import SAMPLE_PATH
from app.services.statement_extractor import extract_financial_statements

TRUTH_PATH = Path(__file__).resolve().parents[1] / "sample_data" / "northstar_sample_truth.json"


def values(**items):
    return {key: {"previous": prev, "current": cur, "page": 5, "label": key} for key, (prev, cur) in items.items()}


def walk_from(**overrides):
    base = dict(
        revenue_from_operations=(1000, 1100), total_income=(1050, 1160), total_expenses=(900, 1000),
        cost_of_materials=(500, 560), employee_benefits=(200, 230), finance_costs=(50, 60), depreciation_amortisation=(50, 55),
        other_expenses=(100, 95),
        profit_before_exceptional_and_tax=(150, 160), profit_before_tax=(150, 100), profit_for_the_year=(110, 70))
    base.update(overrides)
    walk, missing = build_walk(values(**base), 5)
    assert walk is not None, missing
    return walk


class WalkMathTest(unittest.TestCase):
    def test_steps_add_up_exactly_to_the_change_in_profit(self):
        walk = walk_from()
        self.assertEqual(walk["start"], 110)
        self.assertEqual(walk["end"], 70)
        self.assertEqual(walk["change"], -40)
        self.assertAlmostEqual(sum(step["effect"] for step in walk["steps"]), walk["change"], places=2)
        self.assertTrue(walk["reconciled"])

    def test_each_step_has_the_right_sign(self):
        effects = {step["key"]: step["effect"] for step in walk_from()["steps"]}
        self.assertEqual(effects["revenue_from_operations"], 100)    # revenue up helps profit
        self.assertEqual(effects["other_income"], 10)
        self.assertEqual(effects["cost_of_materials"], -60)           # costs up hurt profit
        self.assertEqual(effects["other_expenses"], 5)                # costs down help profit
        self.assertEqual(effects["exceptional_items"], -60)           # profit before tax 100 vs 160 before exceptional
        self.assertEqual(effects["tax"], 10)                          # tax fell from 40 to 30

    def test_exceptional_items_work_whichever_sign_the_report_prints(self):
        # the walk reads exceptional items from the gap between the two profit lines, not from the printed sign
        positive = walk_from(exceptional_items=(0, 50))
        negative = walk_from(exceptional_items=(0, -50))
        self.assertEqual(positive["steps"][-2]["effect"], negative["steps"][-2]["effect"])
        self.assertEqual(positive["steps"][-2]["key"], "exceptional_items")

    def test_unlisted_cost_lines_are_grouped_not_hidden(self):
        # total expenses grow by 10 more than the itemised lines explain
        walk = walk_from(total_expenses=(950, 1060), profit_before_exceptional_and_tax=(100, 100),
                         profit_before_tax=(100, 100), profit_for_the_year=(75, 70))
        grouped = [step for step in walk["steps"] if step["key"] == "other_cost_lines"]
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["effect"], -10.0)
        self.assertAlmostEqual(sum(step["effect"] for step in walk["steps"]), walk["change"], places=2)
        self.assertTrue(walk["reconciled"])

    def test_numbers_that_do_not_add_up_are_flagged_and_shown(self):
        walk = walk_from(profit_before_exceptional_and_tax=(150, 175))  # inconsistent with income minus expenses
        self.assertFalse(walk["reconciled"])
        self.assertTrue(any(step["key"] == "unitemised" for step in walk["steps"]))
        self.assertAlmostEqual(sum(step["effect"] for step in walk["steps"]), walk["change"], places=2)

    def test_missing_statement_lines_return_nothing_instead_of_guessing(self):
        walk, missing = build_walk(values(revenue_from_operations=(1, 2)), 5)
        self.assertIsNone(walk)
        self.assertIn("profit_for_the_year", missing)

    def test_drivers_are_the_three_biggest_moves(self):
        drivers = walk_from()["drivers"]
        self.assertEqual(len(drivers), 3)
        self.assertEqual(drivers[0]["key"], "revenue_from_operations")
        self.assertEqual([abs(d["effect"]) for d in drivers], sorted((abs(d["effect"]) for d in drivers), reverse=True))


class WalkSentencesTest(unittest.TestCase):
    def test_profit_to_loss_is_called_a_swing_not_a_percentage(self):
        walk = walk_from(profit_before_tax=(150, -20), profit_for_the_year=(110, -30))
        self.assertIn("swung from a profit of 110.00 to a loss of 30.00", walk["sentences"][0])
        self.assertFalse(any("%" in s and "Profit swung" in s for s in walk["sentences"]))

    def test_loss_to_profit_swing(self):
        walk = walk_from(profit_before_tax=(-20, 100), profit_for_the_year=(-30, 70), profit_before_exceptional_and_tax=(-20, 160))
        self.assertIn("swung from a loss of 30.00 to a profit of 70.00", walk["sentences"][0])

    def test_plain_rise_and_fall_wording(self):
        self.assertIn("Profit fell by 40.00", walk_from()["sentences"][0])
        rising = walk_from(profit_before_tax=(150, 190), profit_for_the_year=(110, 150))
        self.assertIn("Profit rose by 40.00", rising["sentences"][0])

    def test_revenue_and_operating_sentences_are_included(self):
        sentences = walk_from()["sentences"]
        self.assertTrue(any("Revenue from operations grew 10.00%" in s for s in sentences))
        self.assertTrue(any("Profit before exceptional items and tax rose by 10.00" in s for s in sentences))
        self.assertTrue(any("Exceptional items cost 60.00" in s for s in sentences))


class ExtractorCostLinesTest(unittest.TestCase):
    def test_purchases_and_wrapped_inventory_lines_are_read(self):
        lines = ["Standalone Statement of Profit and Loss for the year ended 31st March, 2026", "2025-26", "2024-25",
                 "Revenue from operations", "100.00", "90.00", "Total Income", "110.00", "95.00",
                 "Purchases of stock-in-trade", "50.00", "40.00",
                 "Changes in inventories of finished goods,", "stock-in-trade and work-in-progress", "(5.00)", "3.00",
                 "Total Expenses", "80.00", "70.00", "Profit before exceptional items and tax", "30.00", "25.00",
                 "Profit before tax", "30.00", "25.00", "Profit for the year", "22.00", "18.00"]
        result = extract_financial_statements({"page_texts": [{"page": 1, "text": "\n".join(lines)}]})
        v = result["statements"]["standalone"]["profit_and_loss"]["values"]
        self.assertEqual((v["purchases_stock_in_trade"]["current"], v["purchases_stock_in_trade"]["previous"]), (50.0, 40.0))
        self.assertEqual((v["changes_in_inventories"]["current"], v["changes_in_inventories"]["previous"]), (-5.0, 3.0))


@unittest.skipUnless(SAMPLE_PATH.is_file() and TRUTH_PATH.is_file(), "sample PDF and truth file not installed in backend/sample_data")
class SampleWalkTest(unittest.TestCase):
    def setUp(self):
        self.truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
        pages = [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(fitz.open(SAMPLE_PATH))]
        self.result = build_profit_walks({"page_texts": pages})

    def test_standalone_and_consolidated_walks_match_the_answer_file(self):
        pat = self.truth["standalone"]["pat"]
        walk = self.result["walks"]["standalone"]
        self.assertEqual((walk["start"], walk["end"], walk["change"]), (pat[1], pat[0], pat[0] - pat[1]))
        cpat = self.truth["consolidated"]["pat"]
        cwalk = self.result["walks"]["consolidated"]
        self.assertEqual((cwalk["start"], cwalk["end"]), (cpat[1], cpat[0]))
        self.assertTrue(walk["reconciled"] and cwalk["reconciled"])

    def test_the_known_story_is_visible_in_the_steps(self):
        effects = {s["key"]: s["effect"] for s in self.result["walks"]["standalone"]["steps"]}
        self.assertEqual(effects["revenue_from_operations"], 400.0)
        self.assertEqual(effects["exceptional_items"], -120.0)
        self.assertEqual(effects["finance_costs"], -16.0)
        self.assertEqual(self.result["walks"]["consolidated"]["page"], self.truth["pages"]["consolidated_pl"])


@unittest.skipUnless(SAMPLE_PATH.is_file(), "sample PDF not installed in backend/sample_data")
class WalkEndpointTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("FINAGENT_DB_PATH")
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-walk.sqlite3"
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

    def test_endpoint_returns_both_walks(self):
        document_id = self.client.post("/api/sample-document").json["document_id"]
        response = self.client.get(f"/api/documents/{document_id}/profit-walk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(response.json["walks"]), ["consolidated", "standalone"])
        self.assertEqual(response.json["walks"]["standalone"]["change"], -104.0)

    def test_unknown_document_is_404(self):
        self.assertEqual(self.client.get("/api/documents/nope/profit-walk").status_code, 404)

    def test_document_without_statements_returns_a_warning(self):
        pdf = fitz.open()
        pdf.new_page().insert_text((72, 72), "A plain letter.")
        data = pdf.tobytes()
        pdf.close()
        document_id = self.client.post("/api/upload", data={"file": (io.BytesIO(data), "letter.pdf")},
                                       content_type="multipart/form-data").json["document_id"]
        body = self.client.get(f"/api/documents/{document_id}/profit-walk").json
        self.assertTrue(body["success"])
        self.assertEqual(body["walks"], {})
        self.assertTrue(body["warnings"])


if __name__ == "__main__":
    unittest.main()
