"""The Story: a short, cited explanation of why profit changed.

Three layers, strongest first:
1. The profit walk, calculated in code from the financial statements.
2. Evidence: passages from the report about the biggest drivers (notes, management discussion).
3. A short explanation written by the AI from ONLY those two things.

The AI's text is then checked: every page it cites must be one we gave it, and every
decimal number it uses must appear in the walk or the evidence. The walk and the evidence are
always returned, even when the AI is unavailable.
"""
from __future__ import annotations

import re

from .llm_service import LLMSummaryError, _generate_text, get_llm_config
from .profit_walk_service import build_profit_walks
from .retrieval_service import RetrievalError, retrieve_relevant_chunks

DRIVER_QUERIES = {
    "exceptional_items": "exceptional items impairment restructuring one-time charge reasons",
    "revenue_from_operations": "revenue growth volume demand sales increase",
    "other_income": "other income interest income",
    "cost_of_materials": "raw material prices cost of materials increase",
    "purchases_stock_in_trade": "purchases of stock-in-trade cost increase",
    "changes_in_inventories": "inventories stock levels change",
    "employee_benefits": "employee costs hiring salaries wages increase",
    "depreciation_amortisation": "depreciation amortisation capacity capital expenditure",
    "other_expenses": "other expenses advertising freight cost increase",
    "finance_costs": "finance costs interest borrowings",
    "tax": "tax expense effective tax rate deferred tax",
    "other_cost_lines": "cost increase reasons",
}
EXCERPT_CHARS = 700
MAX_DRIVERS = 4
_NUMBER = re.compile(r"\d[\d,]*\.\d+")
_PAGE_REF = re.compile(r"\b[Pp]ages?\s+(\d+(?:\s*(?:,|and|&|-)\s*\d+)*)")

SYSTEM_PROMPT = (
    "You write short, plain-language explanations of why a company's profit changed, for a financial "
    "research tool. You never give investment advice and never predict the future."
)


def pick_basis(walks: dict, requested: str | None) -> str | None:
    if requested and requested in walks:
        return requested
    for basis in ("standalone", "consolidated"):
        if basis in walks:
            return basis
    return next(iter(walks), None)


def select_drivers(walk: dict) -> list[dict]:
    steps = [s for s in walk["steps"] if s["direction"] != "flat" and s["key"] != "unitemised"]
    ranked = sorted(steps, key=lambda s: abs(s["effect"]), reverse=True)
    chosen = ranked[:MAX_DRIVERS - 1]
    exceptional = next((s for s in ranked if s["key"] == "exceptional_items"), None)
    if exceptional and exceptional not in chosen:
        chosen.append(exceptional)
    else:
        chosen = ranked[:MAX_DRIVERS]
    return chosen


DRIVER_WORDS = {
    "exceptional_items": r"exceptional|impairment|restructur",
    "revenue_from_operations": r"revenue|sales|turnover",
    "other_income": r"other income|interest income",
    "cost_of_materials": r"raw material|cost of materials|material cost|steel|aluminium|copper",
    "purchases_stock_in_trade": r"purchases?|stock[- ]in[- ]trade|traded goods",
    "changes_in_inventories": r"inventor",
    "employee_benefits": r"employee|wages|salar|manpower",
    "depreciation_amortisation": r"depreciation|amorti[sz]ation",
    "other_expenses": r"other expenses|advertis|freight|selling",
    "finance_costs": r"finance cost|interest",
    "tax": r"\btax",
    "other_cost_lines": r"\bcosts?\b|expenses?",
}
STRONG_CUES = re.compile(
    r"\b(due to|owing to|on account of|attributable to|attributes?|attributed to|as a result of|resulted in|because of|primarily|mainly|variance is|reason)\b", re.I)
MOVEMENT_WORDS = re.compile(r"\b(increas\w*|decreas\w*|higher|lower|rose|risen|rise|fell|fall|declin\w*|reduc\w*|growth|grew|drop\w*)\b", re.I)
POLICY_TEXT = re.compile(
    r"accounting polic|is measured at|are measured at|recogni[sz]ed at|useful li(?:fe|ves)|in accordance with ind as|as per ind as|"
    r"weighted average|lower of cost|net realisable|net realizable|carrying amount|recoverable amount|impairment loss was recogni", re.I)
MIN_RELEVANCE = 12.0
# descriptive notes are enough for exceptional items: they state what the item was
DESCRIPTIVE_OK = {"exceptional_items"}
CANDIDATES = 15
PASSAGES_PER_DRIVER = {"exceptional_items": 3}


def _relevance(chunk: dict, key: str, words: re.Pattern, basis: str) -> float | None:
    """Score a passage for a driver, or None when it should not be used."""
    text = chunk["excerpt"]
    lowered = text.lower()
    if not words.search(text):
        return None
    other, own = ("consolidated", "standalone") if basis == "standalone" else ("standalone", "consolidated")
    if other in lowered and own not in lowered:
        return None  # clearly written about the other basis
    strong = bool(STRONG_CUES.search(text))
    moves = bool(MOVEMENT_WORDS.search(text))
    if not (strong or moves) and key not in DESCRIPTIVE_OK:
        return None
    score = float(chunk["score"]) * (2.0 if strong else 1.3 if moves else 1.0)
    if POLICY_TEXT.search(text):
        score *= 0.5
    digits = sum(ch.isdigit() for ch in text)
    if digits / max(len(text), 1) > 0.25:
        score *= 0.5  # mostly a table of numbers
    return score


def gather_evidence(document: dict, walk: dict, basis: str = "standalone") -> list[dict]:
    """For each big driver, keep passages that mention it and read like an explanation."""
    evidence = []
    for driver in select_drivers(walk):
        query = DRIVER_QUERIES.get(driver["key"], driver["label"])
        words = re.compile(DRIVER_WORDS.get(driver["key"], re.escape(driver["label"].split()[0])), re.I)
        try:
            found = retrieve_relevant_chunks(document, query, limit=CANDIDATES)
        except RetrievalError:
            found = []
        scored = []
        for chunk in found:
            if chunk["page"] == walk["page"]:
                continue  # the statement page itself holds the number, not the explanation
            score = _relevance(chunk, driver["key"], words, basis)
            if score is not None and score >= MIN_RELEVANCE:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        passages, seen = [], set()
        for _, chunk in scored:
            if chunk["chunk_id"] in seen:
                continue
            seen.add(chunk["chunk_id"])
            passages.append({"page": chunk["page"], "chunk_id": chunk["chunk_id"], "excerpt": chunk["excerpt"][:EXCERPT_CHARS]})
            if len(passages) == PASSAGES_PER_DRIVER.get(driver["key"], 2):
                break
        evidence.append({"key": driver["key"], "label": driver["label"], "effect": driver["effect"], "passages": passages})
    return evidence


def build_prompt(basis: str, walk: dict, evidence: list[dict], filename: str) -> str:
    unit = walk.get("unit") or "currency units"
    steps = "\n".join(f"- {s['label']}: {s['effect']:+,.2f} (statement page {', '.join(str(p) for p in s['pages'])})" for s in walk["steps"] if s["direction"] != "flat")
    blocks = []
    for item in evidence:
        header = f"Driver: {item['label']} ({item['effect']:+,.2f})"
        if item["passages"]:
            body = "\n".join(f"  [Page {p['page']}] {p['excerpt']}" for p in item["passages"])
        else:
            body = "  (no explanatory passage was found for this driver)"
        blocks.append(f"{header}\n{body}")
    return (
        "Explain why the company's profit changed between the two years.\n\n"
        "RULES\n"
        "- Write 4 to 6 short bullet points in plain language.\n"
        "- Use ONLY the profit walk and the evidence passages below. Every number must come from them.\n"
        "- Cite the page for every claim, like (Page 12).\n"
        "- Use a passage only if it clearly explains the driver. Ignore passages about accounting policies or unrelated topics.\n"
        "- If the evidence does not explain a driver, say 'the report does not explain this in the passages found' instead of guessing.\n"
        f"- Say that the figures are {basis}. If profit swung from a profit to a loss, say it swung to a loss.\n"
        "- Do not predict the future and do not give investment advice.\n\n"
        f"Document: {filename}\nBasis: {basis}\nUnit: {unit}\n\n"
        "PROFIT WALK (calculated from the financial statements; positive helps profit, negative hurts it)\n"
        + "\n".join(walk["sentences"]) + "\n" + steps + "\n\n"
        "EVIDENCE PASSAGES\n" + "\n\n".join(blocks)
    )


def _numbers(text: str) -> set[float]:
    return {round(float(match.replace(",", "")), 2) for match in _NUMBER.findall(text)}


def check_story(story: str, walk: dict, evidence: list[dict]) -> dict:
    allowed_pages = {walk["page"]} | {p["page"] for item in evidence for p in item["passages"]}
    cited: set[int] = set()
    for match in _PAGE_REF.findall(story):
        cited.update(int(n) for n in re.findall(r"\d+", match))

    allowed_numbers = {round(abs(v), 2) for v in (walk["start"], walk["end"], walk["change"])}
    for step in walk["steps"]:
        allowed_numbers.update(round(abs(step[key]), 2) for key in ("effect", "previous", "current"))
    operating = walk["operating"]
    allowed_numbers.update(round(abs(v), 2) for v in (operating["profit_before_exceptional_previous"], operating["profit_before_exceptional_current"], operating["change"]))
    for value in (operating.get("change_pct"), walk.get("revenue_growth_pct")):
        if value is not None:
            allowed_numbers.add(round(abs(value), 2))
    for item in evidence:
        for passage in item["passages"]:
            allowed_numbers |= {round(abs(n), 2) for n in _numbers(passage["excerpt"])}

    used = _numbers(story)
    ungrounded = sorted(n for n in used if round(abs(n), 2) not in allowed_numbers)
    return {
        "pages": {"cited": sorted(cited), "unknown": sorted(cited - allowed_pages)},
        "numbers": {"checked": len(used), "ungrounded": ungrounded},
        "passed": not (cited - allowed_pages) and not ungrounded,
    }


def build_story(document: dict, requested_basis: str | None = None) -> dict:
    result = {"success": True, "document_id": document.get("document_id"), "story": None, "status": "no_statements",
              "basis": None, "walk": None, "evidence": [], "checks": None, "limitations": [], "bases_available": []}
    walks = build_profit_walks(document)
    result["limitations"].extend(walks["warnings"])
    if not walks["walks"]:
        return result

    result["bases_available"] = sorted(walks["walks"])
    basis = pick_basis(walks["walks"], requested_basis)
    if requested_basis and requested_basis != basis:
        result["limitations"].append(f"The {requested_basis} figures were not found, so the {basis} figures are shown.")
    walk = walks["walks"][basis]
    result.update({"basis": basis, "walk": walk, "status": "walk_only"})
    if not walk["reconciled"]:
        result["limitations"].append("The profit walk did not reconcile exactly to the reported profit; treat it with care.")

    result["evidence"] = gather_evidence(document, walk, basis)
    missing = [e["label"] for e in result["evidence"] if not e["passages"]]
    if missing:
        result["limitations"].append("No explanatory passage was found for: " + ", ".join(missing) + ".")

    config = get_llm_config()
    result["provider"], result["model"] = config["provider"], config["model"]
    if not config["configured"]:
        result["status"] = "not_configured"
        result["limitations"].append("No AI provider is configured, so only the calculated walk and the evidence are shown.")
        return result

    try:
        text = _generate_text(config, SYSTEM_PROMPT, build_prompt(basis, walk, result["evidence"], document.get("filename", "document")))
    except LLMSummaryError as exc:
        result["status"] = "llm_error"
        result["limitations"].append(f"The AI explanation could not be written: {exc}")
        return result

    result["story"] = text.strip()
    result["checks"] = check_story(result["story"], walk, result["evidence"])
    result["status"] = "generated"
    if not result["checks"]["passed"]:
        result["limitations"].append("Some pages or numbers in the explanation could not be matched to the evidence. Check them before relying on the text.")
    return result
