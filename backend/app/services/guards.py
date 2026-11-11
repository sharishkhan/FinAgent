"""Pre-retrieval guards for FinAgent questions.

Two small, deterministic checks that run BEFORE any LLM call:

1. Investment-advice guard: FinAgent is a research assistant, not an advisor.
2. Company-mismatch guard: if the question names an organisation that never
   appears in the uploaded document, refuse instead of answering from the
   wrong company's numbers.

Both return a refusal message (str) or None. They never raise, so a bug here
can only make a guard silently pass, never crash the request.
"""
from __future__ import annotations

import re
from collections import Counter

ADVICE_MESSAGE = (
    "FinAgent is a document-based research assistant and does not give investment "
    "advice or stock recommendations. I can help you understand what this report "
    "says about the company's revenue, profit, margins, debt, or risks."
)

_ADVICE_PATTERNS = [
    r"\bshould (?:i|we|one)\s+(?:buy|sell|invest|hold|short|purchase|avoid)\b",
    r"\b(?:do|would|can|could) you recommend\b",
    r"\brecommend(?:ation)?s?\b.{0,25}\b(?:buy|sell|invest|stock|share)",
    r"\b(?:good|bad|safe|wise|right)\s+(?:time\s+to\s+|idea\s+to\s+)?(?:buy|sell|invest)\b",
    r"\bis (?:it|this|the stock|the share|the company)\s+(?:a\s+)?(?:good|bad|safe|worthwhile)\s+(?:buy|investment|stock|bet)\b",
    r"\bworth\s+(?:buying|investing|holding)\b",
    r"\b(?:price target|target price)\b",
    r"\b(?:predict|forecast)\b.{0,30}\b(?:stock|share)\s+price\b",
    r"\bwill\b.{0,30}\b(?:stock|share)\s+price\b.{0,15}\b(?:go|rise|fall|increase|drop|hit)\b",
]
_ADVICE_REGEX = re.compile("|".join(f"(?:{p})" for p in _ADVICE_PATTERNS), re.IGNORECASE)


def check_investment_advice(question: str) -> str | None:
    try:
        if _ADVICE_REGEX.search(question or ""):
            return ADVICE_MESSAGE
    except Exception:  # pragma: no cover - guard must never break the request
        return None
    return None


# --- company mismatch -------------------------------------------------------

_WORD = r"[A-Z][A-Za-z0-9&\-]{2,}"
_NAME = rf"{_WORD}(?:\s+{_WORD}){{0,3}}"
# "Voltas's revenue", "revenue of Voltas", "did Voltas grow", "for Tata Motors"
_POSSESSIVE = re.compile(rf"\b({_NAME})['\u2019]s\b")
_AFTER_PREP = re.compile(rf"\b(?:of|for|at|did|does|about|from|by|with|is|was|has|have)\s+({_NAME})")

_IGNORE_EXACT = {
    "fy", "q1", "q2", "q3", "q4", "h1", "h2", "ind", "as", "ifrs", "gaap", "sebi",
    "ebitda", "eps", "roe", "roce", "rbi", "gst", "january", "february", "march",
    "april", "may", "june", "july", "august", "september", "october", "november",
    "december", "page", "note", "notes", "india", "indian", "rupees", "crore",
    "lakh", "company", "board", "group", "standalone", "consolidated",
}
_IGNORE_REGEX = re.compile(r"^(?:fy\d*|fy-?\d{2,4}|q[1-4]|h[12]|\d.*|ind$)", re.IGNORECASE)

_LEGAL_NAME = re.compile(
    rf"({_WORD}(?:\s+{_WORD}){{0,5}})\s+(?:Limited|Ltd\.?|Inc\.?|Corporation|Corp\.?|Pvt\.?\s*Ltd\.?)"
)
_GENERIC_NAME_WORDS = {"the", "and", "for", "annual", "report", "integrated", "financial"}


def _document_text(document: dict) -> str:
    text = document.get("text")
    if isinstance(text, str) and text:
        return text
    return " ".join(chunk.get("text", "") for chunk in document.get("chunks", []))


def _tokens(value: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9&]{3,}", value)} - _GENERIC_NAME_WORDS


def detect_document_company(document: dict) -> str | None:
    """Best-effort legal name, taken from the first pages (most frequent match)."""
    try:
        pages = document.get("page_texts") or []
        head = " ".join(p.get("text", "") for p in pages[:8]) if pages else _document_text(document)[:30000]
        head = " ".join(head.split())
        names = Counter(m.group(1).strip() for m in _LEGAL_NAME.finditer(head))
        if not names:
            return None
        return names.most_common(1)[0][0]
    except Exception:  # pragma: no cover
        return None


def _candidate_names(question: str) -> list[str]:
    found = []
    for regex in (_POSSESSIVE, _AFTER_PREP):
        for match in regex.finditer(question or ""):
            name = match.group(1).strip()
            first = name.split()[0].lower()
            if first in _IGNORE_EXACT or _IGNORE_REGEX.match(first):
                continue
            if name not in found:
                found.append(name)
    return found


def check_company_mismatch(document: dict, question: str) -> str | None:
    try:
        candidates = _candidate_names(question)
        if not candidates:
            return None

        doc_text = _document_text(document).lower()
        company = detect_document_company(document)
        company_tokens = _tokens(company) if company else set()

        for name in candidates:
            if name.lower() in doc_text:
                continue
            if company_tokens and (_tokens(name) & company_tokens):
                continue  # e.g. user wrote a shortened form of the company's own name
            subject = f"'{company}'" if company else "this report"
            return (
                f"Your question mentions '{name}', which does not appear in the uploaded "
                f"document. This document is the report of {subject}. FinAgent only answers "
                f"from the uploaded document, so I can't give figures for '{name}'. "
                f"If you meant a different company, please upload its report."
            )
    except Exception:  # pragma: no cover
        return None
    return None


def check_question_guards(document: dict, question: str) -> tuple[str, str] | None:
    """Return (guard_name, message) when the question must be refused, else None."""
    message = check_investment_advice(question)
    if message:
        return "investment_advice", message
    message = check_company_mismatch(document, question)
    if message:
        return "company_mismatch", message
    return None
