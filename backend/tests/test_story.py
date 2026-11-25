import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app import create_app
from app.services.llm_service import LLMSummaryError
from app.services.pdf_service import DOCUMENT_STORE
from app.services.profit_walk_service import build_walk
from app.services.sample_service import SAMPLE_PATH
from app.services.story_service import build_prompt, build_story, check_story, pick_basis, select_drivers

CONFIGURED = {"provider": "gemini", "model": "gemini-test", "api_key": "secret-test-key", "configured": True}
UNCONFIGURED = {"provider": "openai", "model": "gpt-test", "api_key": "", "configured": False}


def make_walk():
    items = dict(
        revenue_from_operations=(1000, 1100), total_income=(1050, 1160), total_expenses=(900, 1000),
        cost_of_materials=(500, 560), employee_benefits=(200, 230), finance_costs=(50, 60), depreciation_amortisation=(50, 55),
        other_expenses=(100, 95), profit_before_exceptional_and_tax=(150, 160), profit_before_tax=(150, 100), profit_for_the_year=(110, 70))
    walk, _ = build_walk({k: {"previous": p, "current": c, "page": 5, "label": k} for k, (p, c) in items.items()}, 5)
    return walk


EVIDENCE = [{"key": "cost_of_materials", "label": "Cost of materials consumed", "effect": -60.0,
             "passages": [{"page": 4, "chunk_id": "p4-c0", "excerpt": "Steel prices rose by 12.50 percent during the year."}]},
            {"key": "tax", "label": "Tax", "effect": 10.0, "passages": []}]


class PickingTest(unittest.TestCase):
    def test_basis_defaults_to_standalone_then_consolidated(self):
        self.assertEqual(pick_basis({"standalone": 1, "consolidated": 2}, None), "standalone")
        self.assertEqual(pick_basis({"consolidated": 2}, None), "consolidated")
        self.assertEqual(pick_basis({"standalone": 1, "consolidated": 2}, "consolidated"), "consolidated")
        self.assertEqual(pick_basis({"standalone": 1}, "consolidated"), "standalone")
        self.assertIsNone(pick_basis({}, None))

    def test_drivers_are_the_biggest_moves_and_always_include_exceptional_items(self):
        keys = [d["key"] for d in select_drivers(make_walk())]
        self.assertIn("exceptional_items", keys)
        self.assertEqual(keys[0], "revenue_from_operations")
        self.assertLessEqual(len(keys), 4)


class PromptAndCheckTest(unittest.TestCase):
    def test_prompt_contains_walk_evidence_and_rules(self):
        prompt = build_prompt("standalone", make_walk(), EVIDENCE, "report.pdf")
        for text in ("Profit fell by 40.00", "Cost of materials consumed: -60.00", "[Page 4] Steel prices rose",
                     "no explanatory passage was found", "Use ONLY the profit walk", "Cite the page", "swung to a loss",
                     "standalone", "Ignore passages about accounting policies"):
            self.assertIn(text, prompt)

    def test_clean_story_passes_the_checks(self):
        story = ("- Standalone profit fell by 40.00, from 110.00 to 70.00 (Page 5).\n"
                 "- Steel prices rose by 12.50 percent, lifting materials cost by 60.00 (Pages 4 and 5).")
        checks = check_story(story, make_walk(), EVIDENCE)
        self.assertEqual(checks["pages"], {"cited": [4, 5], "unknown": []})
        self.assertEqual(checks["numbers"]["ungrounded"], [])
        self.assertTrue(checks["passed"])

    def test_invented_page_and_number_are_caught(self):
        story = "- Profit rose by 77.77 because of a new factory (Page 99). Materials cost 60.00 more (Page 4)."
        checks = check_story(story, make_walk(), EVIDENCE)
        self.assertEqual(checks["pages"]["unknown"], [99])
        self.assertEqual(checks["numbers"]["ungrounded"], [77.77])
        self.assertFalse(checks["passed"])

    def test_page_lists_are_understood(self):
        checks = check_story("Costs rose (Pages 4, 5 and 6).", make_walk(), EVIDENCE)
        self.assertEqual(checks["pages"]["cited"], [4, 5, 6])
        self.assertEqual(checks["pages"]["unknown"], [6])


@unittest.skipUnless(SAMPLE_PATH.is_file(), "sample PDF not installed in backend/sample_data")
class StoryOnSampleTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("FINAGENT_DB_PATH")
        data_dir = Path(__file__).resolve().parent / "_test_data"
        data_dir.mkdir(exist_ok=True)
        self.db = data_dir / "test-finagent-story.sqlite3"
        self._clean()
        os.environ["FINAGENT_DB_PATH"] = str(self.db)
        DOCUMENT_STORE.clear()
        self.client = create_app().test_client()
        self.document_id = self.client.post("/api/sample-document").json["document_id"]

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

    def story(self, **body):
        return self.client.post(f"/api/documents/{self.document_id}/story", json=body)

    def test_evidence_finds_managements_explanation_and_the_exceptional_note(self):
        with patch("app.services.story_service.get_llm_config", return_value=UNCONFIGURED):
            body = self.story().json
        by_key = {e["key"]: [p["page"] for p in e["passages"]] for e in body["evidence"]}
        self.assertIn(4, by_key["cost_of_materials"])          # "prices of steel and aluminium rose"
        self.assertIn(12, by_key["exceptional_items"])         # the exceptional items note
        self.assertTrue(all(8 not in pages for pages in by_key.values()))  # never the statement page itself

    def test_without_an_ai_key_the_walk_and_evidence_are_still_returned(self):
        with patch("app.services.story_service.get_llm_config", return_value=UNCONFIGURED):
            body = self.story().json
        self.assertEqual(body["status"], "not_configured")
        self.assertIsNone(body["story"])
        self.assertEqual(body["walk"]["change"], -104.0)
        self.assertTrue(body["evidence"])

    def test_generated_story_is_checked_and_saved_to_history(self):
        text = ("- Standalone profit fell by 104.00, from 157.00 to 53.00 (Page 8).\n"
                "- Steel and aluminium prices rose, raising materials cost by 240.00 (Pages 4 and 8).\n"
                "- Exceptional items cost 120.00 (Page 12).")
        with patch("app.services.story_service.get_llm_config", return_value=CONFIGURED), \
             patch("app.services.story_service._generate_text", return_value=text) as llm:
            response = self.story()
        body = response.json
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "generated")
        self.assertTrue(body["checks"]["passed"], body["checks"])
        self.assertEqual(body["basis"], "standalone")
        self.assertIn("Profit fell by 104.00", llm.call_args.args[2])
        self.assertNotIn("secret-test-key", response.get_data(as_text=True))
        results = self.client.get("/api/results").json["results"]
        self.assertEqual([r["result_type"] for r in results if r["document_id"] == self.document_id], ["story"])

    def test_invented_citation_is_flagged_in_the_response(self):
        with patch("app.services.story_service.get_llm_config", return_value=CONFIGURED), \
             patch("app.services.story_service._generate_text", return_value="- Profit fell for 11 reasons (Page 99), losing 55.55."):
            body = self.story().json
        self.assertFalse(body["checks"]["passed"])
        self.assertEqual(body["checks"]["pages"]["unknown"], [99])
        self.assertTrue(any("could not be matched" in note for note in body["limitations"]))

    def test_ai_failure_still_returns_the_calculated_parts(self):
        with patch("app.services.story_service.get_llm_config", return_value=CONFIGURED), \
             patch("app.services.story_service._generate_text", side_effect=LLMSummaryError("Gemini quota or rate limit reached.", 429)):
            response = self.story()
        body = response.json
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "llm_error")
        self.assertIsNone(body["story"])
        self.assertEqual(body["walk"]["change"], -104.0)
        self.assertTrue(any("quota" in note for note in body["limitations"]))

    def test_basis_can_be_chosen_and_falls_back_politely(self):
        with patch("app.services.story_service.get_llm_config", return_value=UNCONFIGURED):
            consolidated = self.story(basis="consolidated").json
            fallback = self.story(basis="nonsense").json
        self.assertEqual((consolidated["basis"], consolidated["walk"]["change"]), ("consolidated", -27.0))
        self.assertEqual(fallback["basis"], "standalone")
        self.assertTrue(any("nonsense" in note for note in fallback["limitations"]))
        self.assertEqual(consolidated["bases_available"], ["consolidated", "standalone"])

    def test_unknown_document_is_404(self):
        self.assertEqual(self.client.post("/api/documents/nope/story", json={}).status_code, 404)

    def test_document_without_statements_returns_a_clear_status_and_saves_nothing(self):
        pdf = fitz.open()
        pdf.new_page().insert_text((72, 72), "A plain letter.")
        data = pdf.tobytes()
        pdf.close()
        other = self.client.post("/api/upload", data={"file": (io.BytesIO(data), "letter.pdf")},
                                 content_type="multipart/form-data").json["document_id"]
        body = self.client.post(f"/api/documents/{other}/story", json={}).json
        self.assertEqual(body["status"], "no_statements")
        self.assertIsNone(body["walk"])
        self.assertTrue(body["limitations"])
        self.assertEqual([r for r in self.client.get("/api/results").json["results"] if r["document_id"] == other], [])


if __name__ == "__main__":
    unittest.main()
