"""Rule-based extraction of key financial-statement figures from a report.

Finds the Balance Sheet and Statement of Profit and Loss, separately for the
standalone and consolidated basis, and reads a fixed set of line items (current
year, previous year, and the page they came from). Nothing is guessed: a line item
that cannot be read cleanly is left out, and cross-checks report whether the
extracted statements are internally consistent.

All maths on the extracted values is done in code (see compute_metrics); an LLM
is never asked to calculate.
"""
from __future__ import annotations

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_ROMAN_PREFIX = re.compile(r"^(?:[ivx]+\.|\([a-z0-9]{1,3}\))\s*")
_DECIMAL_AMOUNT = re.compile(r"^\(?-?[\d,]*\d\.\d+\)?$")
_INTEGER_AMOUNT = re.compile(r"^\(?-?\d{1,3}(?:,\d{2,3})+\)?$|^\(?-?\d{4,}\)?$")
_DASHES = {"-", "\u2013", "\u2014", "nil"}
_NOTE_LIKE = re.compile(r"^(?:\d{1,3}(?:\.\d+)?|\d{1,3}\s?[A-Za-z]|\d{1,3}\([a-z]\)|[A-Za-z]\d{1,3})$")

HEADER_LINES = 15

PL_ITEMS = {
    "revenue_from_operations": r"^revenue from operations",
    "other_income": r"^other income",
    "total_income": r"^total income",
    "cost_of_materials": r"^cost of materials consumed",
    "employee_benefits": r"^employee benefits? expenses?",
    "finance_costs": r"^finance costs?",
    "depreciation_amortisation": r"^depreciation and amorti[sz]ation",
    "other_expenses": r"^other expenses",
    "total_expenses": r"^total expenses",
    "profit_before_exceptional_and_tax": r"^(?:profit|loss)(?:/\s*\((?:loss|profit)\))? before exceptional",
    "exceptional_items": r"^exceptional items?",
    "profit_before_tax": r"^(?:profit|loss)(?:/\s*\((?:loss|profit)\))? before tax",
    "total_tax_expense": r"^total tax expenses?",
    "profit_for_the_year": r"^(?:profit|loss)(?:/\s*\((?:loss|profit)\))? for the (?:year|period)",
    "eps_basic": r"^basic and diluted earnings per|^basic earnings per",
}
BS_ITEMS = {
    "cash_and_cash_equivalents": r"^cash and cash equivalents",
    "total_non_current_assets": r"^total non[- ]current assets",
    "total_current_assets": r"^total current assets",
    "total_assets": r"^total assets",
    "equity_share_capital": r"^equity share capital",
    "total_equity": r"^total equity$|^total equity \(",
    "total_non_current_liabilities": r"^total non[- ]current liabilities",
    "total_current_liabilities": r"^total current liabilities",
    "total_equity_and_liabilities": r"^total equity and liabilities",
}
# "Borrowings" appears under both non-current and current liabilities, so it is read per section.
SECTION_HEADINGS = {
    "nca": r"^non[- ]current assets$",
    "ca": r"^current assets$",
    "ncl": r"^non[- ]current liabilities$",
    "cl": r"^current liabilities$",
}
SECTION_ITEMS = [
    # (key, section the line must sit in or None, label pattern)
    ("inventories", "ca", r"^inventories"),
    ("trade_receivables", "ca", r"^trade receivables"),
    ("borrowings_non_current", "ncl", r"^borrowings"),
    ("borrowings_non_current", None, r"^non[- ]current borrowings"),
    ("borrowings_current", "cl", r"^borrowings"),
    ("borrowings_current", None, r"^current borrowings"),
]

_PL_HEADER = re.compile(r"^(?:(standalone|consolidated)\s+)?(?:financial\s+)?statements? of profit and loss")
_BS_HEADER = re.compile(r"^(?:(standalone|consolidated)\s+)?balance sheet as at")
_UNIT = re.compile(r"(crores?|lakhs?|lacs?|millions?|billions?)", re.I)
_YEARS = re.compile(r"\b(20\d{2}-\d{2}|20\d{2}-20\d{2})\b")


def _clean(line: str) -> str:
    return " ".join(_CONTROL.sub("", line).replace("\t", " ").split())


def _norm_label(line: str) -> str:
    text = _clean(line).lower()
    text = _ROMAN_PREFIX.sub("", text)
    return text.strip()


def _is_amount(token: str, integer_mode: bool) -> bool:
    token = _clean(token)
    if token.lower() in _DASHES:
        return True
    if _DECIMAL_AMOUNT.match(token):
        return True
    return integer_mode and bool(_INTEGER_AMOUNT.match(token))


def _to_number(token: str) -> float:
    token = _clean(token)
    if token.lower() in _DASHES:
        return 0.0
    negative = token.startswith("(") or token.startswith("-")
    value = float(re.sub(r"[(),\s-]", "", token))
    return -value if negative else value


def _page_lines(text: str) -> list[str]:
    return [_clean(line) for line in text.split("\n") if _clean(line)]


def _detect_header(lines: list[str]):
    """Return (statement, basis) when the page opens with a statement heading."""
    head = lines[:HEADER_LINES]
    for line in lines:
        if len(line) > 120:
            continue
        norm = _norm_label(line)
        for statement, regex in (("profit_and_loss", _PL_HEADER), ("balance_sheet", _BS_HEADER)):
            match = regex.match(norm)
            if match:
                basis = match.group(1)
                if not basis:
                    joined = " ".join(lines).lower() if len(lines) < 40 else " ".join(head).lower()
                    if "consolidated" in joined and "standalone" not in joined:
                        basis = "consolidated"
                    elif "standalone" in joined and "consolidated" not in joined:
                        basis = "standalone"
                    else:
                        basis = "unspecified"
                return statement, basis
    return None


def _count_amounts(lines: list[str]) -> tuple[int, int]:
    decimals = sum(1 for line in lines if _DECIMAL_AMOUNT.match(line))
    integers = sum(1 for line in lines if _INTEGER_AMOUNT.match(line))
    return decimals, integers


def _read_amounts(lines: list[str], start: int, integer_mode: bool, patterns: list[str]):
    """Read the two amounts that follow a label line, skipping the note column."""
    amounts: list[float] = []
    continuation_used = False
    for offset in range(1, 9):
        index = start + offset
        if index >= len(lines):
            break
        line = lines[index]
        if _is_amount(line, integer_mode):
            amounts.append(_to_number(line))
            if len(amounts) == 2:
                return amounts
            continue
        if _NOTE_LIKE.match(line) and not amounts:
            continue
        has_letters = len(re.findall(r"[A-Za-z]", line)) >= 3
        if has_letters and not amounts and not continuation_used:
            previous = lines[index - 1].lower()
            if line[:1].islower() or previous.endswith(("and", ",", "-", "(")):
                if not any(re.match(p, _norm_label(line)) for p in patterns):
                    continuation_used = True
                    continue
        break
    return None


def _extract_statement(lines: list[str], statement: str, page: int) -> dict:
    decimals, integers = _count_amounts(lines)
    integer_mode = decimals < 8 and integers >= 8
    items = PL_ITEMS if statement == "profit_and_loss" else BS_ITEMS
    all_patterns = list(items.values()) + [pattern for _, _, pattern in SECTION_ITEMS]
    values: dict[str, dict] = {}
    section = None

    for index, line in enumerate(lines):
        norm = _norm_label(line)
        for name, regex in SECTION_HEADINGS.items():
            if re.match(regex, norm):
                section = name
        if len(re.findall(r"[A-Za-z]", norm)) < 3:
            continue

        for key, regex in items.items():
            if key in values or not re.match(regex, norm):
                continue
            amounts = _read_amounts(lines, index, integer_mode, all_patterns)
            if amounts:
                values[key] = {"current": amounts[0], "previous": amounts[1], "page": page, "label": _clean(line)}
            break

        if statement == "balance_sheet":
            for key, needed_section, regex in SECTION_ITEMS:
                if key in values or (needed_section is not None and section != needed_section) or not re.match(regex, norm):
                    continue
                amounts = _read_amounts(lines, index, integer_mode, all_patterns)
                if amounts:
                    values[key] = {"current": amounts[0], "previous": amounts[1], "page": page, "label": _clean(line)}
                break

    header_text = " ".join(lines[:HEADER_LINES])
    unit = _UNIT.search(header_text)
    years = list(dict.fromkeys(_YEARS.findall(header_text)))
    return {
        "page": page,
        "values": values,
        "unit": unit.group(1).lower().rstrip("s") if unit else None,
        "periods": years[:2],
    }


def extract_financial_statements(document: dict) -> dict:
    """Locate statements in document['page_texts'] and read their key line items."""
    candidates: dict[tuple[str, str], list[dict]] = {}
    for entry in document.get("page_texts") or []:
        text = entry.get("text", "") if isinstance(entry, dict) else str(entry)
        page = entry.get("page") if isinstance(entry, dict) else None
        if not text or page is None:
            continue
        lines = _page_lines(text)
        detected = _detect_header(lines)
        if not detected:
            continue
        decimals, integers = _count_amounts(lines)
        if decimals + integers < 8:
            continue  # contents pages and prose mentioning a statement name
        statement, basis = detected
        extracted = _extract_statement(lines, statement, page)
        if extracted["values"]:
            candidates.setdefault((basis, statement), []).append(extracted)

    statements: dict[str, dict] = {}
    for (basis, statement), found in candidates.items():
        best = max(found, key=lambda item: (len(item["values"]), -item["page"]))
        statements.setdefault(basis, {})[statement] = best

    result = {"statements": statements, "warnings": []}
    result["checks"] = run_checks(statements)
    if not statements:
        result["warnings"].append("No balance sheet or statement of profit and loss was recognised in this document.")
    if "unspecified" in statements:
        result["warnings"].append("Some statements do not say whether they are standalone or consolidated.")
    return result


def _value(statements: dict, basis: str, statement: str, key: str):
    return statements.get(basis, {}).get(statement, {}).get("values", {}).get(key)


def run_checks(statements: dict) -> list[dict]:
    """Cross-checks that show whether the extracted numbers hang together."""
    checks = []

    def close(a: float, b: float) -> bool:
        return abs(a - b) <= max(0.02, abs(b) * 0.0005)

    for basis in statements:
        bs = statements[basis].get("balance_sheet")
        pl = statements[basis].get("profit_and_loss")
        if bs:
            v = bs["values"]
            if "total_assets" in v and "total_equity_and_liabilities" in v:
                for column in ("current", "previous"):
                    checks.append({
                        "basis": basis, "name": f"Balance sheet balances ({column} year)",
                        "ok": close(v["total_assets"][column], v["total_equity_and_liabilities"][column]),
                        "page": bs["page"],
                    })
        if pl:
            v = pl["values"]
            if all(k in v for k in ("total_income", "total_expenses", "profit_before_exceptional_and_tax")):
                for column in ("current", "previous"):
                    expected = v["total_income"][column] - v["total_expenses"][column]
                    checks.append({
                        "basis": basis, "name": f"Income minus expenses equals profit before exceptional items ({column} year)",
                        "ok": close(expected, v["profit_before_exceptional_and_tax"][column]), "page": pl["page"],
                    })
    return checks


def _metric(label, unit, current, previous, formula, inputs):
    return {"label": label, "unit": unit, "current": current, "previous": previous, "formula": formula, "inputs": inputs}


def compute_metrics(statements: dict, basis: str) -> dict:
    """Ratios and growth figures, calculated in code from extracted values only."""
    metrics: dict[str, dict] = {}
    pl = statements.get(basis, {}).get("profit_and_loss", {}).get("values", {})
    bs = statements.get(basis, {}).get("balance_sheet", {}).get("values", {})

    def both(fn):
        try:
            return fn("current"), fn("previous")
        except (KeyError, ZeroDivisionError):
            return None, None

    def ref(statement_values, key):
        item = statement_values[key]
        return {"name": key, "page": item["page"]}

    if "revenue_from_operations" in pl:
        rev = pl["revenue_from_operations"]
        if rev["previous"]:
            growth = (rev["current"] / rev["previous"] - 1) * 100
            metrics["revenue_growth_pct"] = _metric("Revenue growth", "%", round(growth, 2), None,
                                                    "(revenue this year / revenue last year - 1) x 100", [ref(pl, "revenue_from_operations")])
        if "profit_for_the_year" in pl:
            cur, prev = both(lambda c: pl["profit_for_the_year"][c] / pl["revenue_from_operations"][c] * 100)
            if cur is not None:
                metrics["net_profit_margin_pct"] = _metric("Net profit margin (on revenue from operations)", "%", round(cur, 2), round(prev, 2),
                                                           "profit for the year / revenue from operations x 100",
                                                           [ref(pl, "profit_for_the_year"), ref(pl, "revenue_from_operations")])
    if "profit_for_the_year" in pl and pl["profit_for_the_year"]["previous"]:
        p = pl["profit_for_the_year"]
        change = (p["current"] / p["previous"] - 1) * 100 if p["previous"] > 0 else None
        if change is not None:
            metrics["profit_change_pct"] = _metric("Change in profit for the year", "%", round(change, 2), None,
                                                   "(profit this year / profit last year - 1) x 100", [ref(pl, "profit_for_the_year")])
    if all(k in pl for k in ("profit_before_exceptional_and_tax", "finance_costs")):
        cur, prev = both(lambda c: (pl["profit_before_exceptional_and_tax"][c] + pl["finance_costs"][c]) / pl["finance_costs"][c])
        if cur is not None:
            metrics["interest_coverage"] = _metric("Interest coverage", "times", round(cur, 2), round(prev, 2),
                                                   "(profit before exceptional items and tax + finance costs) / finance costs",
                                                   [ref(pl, "profit_before_exceptional_and_tax"), ref(pl, "finance_costs")])
    if all(k in pl for k in ("profit_before_exceptional_and_tax", "finance_costs", "depreciation_amortisation", "other_income", "revenue_from_operations")):
        def ebitda(c):
            return (pl["profit_before_exceptional_and_tax"][c] + pl["finance_costs"][c]
                    + pl["depreciation_amortisation"][c] - pl["other_income"][c])
        cur, prev = both(lambda c: ebitda(c) / pl["revenue_from_operations"][c] * 100)
        if cur is not None:
            metrics["ebitda_margin_pct"] = _metric("EBITDA margin", "%", round(cur, 2), round(prev, 2),
                                                   "(profit before exceptional items and tax + finance costs + depreciation - other income) / revenue x 100",
                                                   [ref(pl, k) for k in ("profit_before_exceptional_and_tax", "finance_costs", "depreciation_amortisation", "other_income", "revenue_from_operations")])
    if "total_equity" in bs and ("borrowings_non_current" in bs or "borrowings_current" in bs):
        def borrowings(c):
            return bs.get("borrowings_non_current", {}).get(c, 0.0) + bs.get("borrowings_current", {}).get(c, 0.0)
        cur, prev = both(lambda c: borrowings(c) / bs["total_equity"][c])
        if cur is not None:
            inputs = [ref(bs, k) for k in ("borrowings_non_current", "borrowings_current") if k in bs] + [ref(bs, "total_equity")]
            metrics["total_borrowings"] = _metric("Total borrowings", "crore", borrowings("current"), borrowings("previous"),
                                                  "non-current borrowings + current borrowings", inputs[:-1])
            metrics["debt_equity_ratio"] = _metric("Debt-equity ratio", "times", round(cur, 2), round(prev, 2),
                                                   "total borrowings / total equity", inputs)
    if all(k in bs for k in ("total_current_assets", "total_current_liabilities")):
        cur, prev = both(lambda c: bs["total_current_assets"][c] / bs["total_current_liabilities"][c])
        if cur is not None:
            metrics["current_ratio"] = _metric("Current ratio", "times", round(cur, 2), round(prev, 2),
                                               "total current assets / total current liabilities",
                                               [ref(bs, "total_current_assets"), ref(bs, "total_current_liabilities")])
    if "trade_receivables" in bs and "revenue_from_operations" in pl:
        cur, prev = both(lambda c: bs["trade_receivables"][c] / pl["revenue_from_operations"][c] * 365)
        if cur is not None:
            metrics["receivable_days"] = _metric("Receivable days", "days", round(cur, 1), round(prev, 1),
                                                 "trade receivables / revenue from operations x 365",
                                                 [ref(bs, "trade_receivables"), ref(pl, "revenue_from_operations")])
    return metrics
