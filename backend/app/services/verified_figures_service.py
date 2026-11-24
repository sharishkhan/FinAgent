"""Picks the extracted statement figures that matter for a question.

The figures come from statement_extractor (read directly from the financial
statements, cross-checked, with page numbers) so the analysis agent can quote exact
numbers instead of hunting for them in loose passages.
"""
from __future__ import annotations

import re

from .statement_extractor import compute_metrics, extract_financial_statements

LABELS = {
    "revenue_from_operations": "Revenue from operations", "other_income": "Other income", "total_income": "Total income",
    "cost_of_materials": "Cost of materials consumed", "employee_benefits": "Employee benefits expense",
    "finance_costs": "Finance costs", "depreciation_amortisation": "Depreciation and amortisation",
    "other_expenses": "Other expenses", "total_expenses": "Total expenses",
    "profit_before_exceptional_and_tax": "Profit before exceptional items and tax", "exceptional_items": "Exceptional items",
    "profit_before_tax": "Profit before tax", "total_tax_expense": "Total tax expense", "profit_for_the_year": "Profit for the year",
    "eps_basic": "Basic earnings per share", "inventories": "Inventories", "trade_receivables": "Trade receivables",
    "cash_and_cash_equivalents": "Cash and cash equivalents", "total_non_current_assets": "Total non-current assets",
    "total_current_assets": "Total current assets", "total_assets": "Total assets", "equity_share_capital": "Equity share capital",
    "total_equity": "Total equity", "total_non_current_liabilities": "Total non-current liabilities",
    "total_current_liabilities": "Total current liabilities", "total_equity_and_liabilities": "Total equity and liabilities",
    "borrowings_non_current": "Non-current borrowings", "borrowings_current": "Current borrowings",
}

CORE_ITEMS = ["revenue_from_operations", "profit_before_exceptional_and_tax", "exceptional_items", "profit_for_the_year", "finance_costs", "total_equity"]
CORE_METRICS = ["revenue_growth_pct", "net_profit_margin_pct", "ebitda_margin_pct", "total_borrowings", "debt_equity_ratio", "interest_coverage"]

# (question pattern, line items, metrics)
KEYWORDS = [
    (r"finance cost|interest", ["finance_costs"], ["interest_coverage"]),
    (r"revenue|sales|turnover|top[- ]line", ["revenue_from_operations"], ["revenue_growth_pct"]),
    (r"profit|loss|earning|net income|bottom[- ]line|\bpat\b|\bpbt\b",
     ["profit_for_the_year", "profit_before_tax", "profit_before_exceptional_and_tax", "exceptional_items"], ["net_profit_margin_pct", "profit_change_pct"]),
    (r"exceptional|one[- ]off|impairment", ["exceptional_items", "profit_before_exceptional_and_tax", "profit_before_tax"], []),
    (r"borrow|debt|leverage|loan|gearing", ["borrowings_non_current", "borrowings_current"], ["total_borrowings", "debt_equity_ratio"]),
    (r"equity|net worth|shareholder", ["total_equity", "equity_share_capital"], ["debt_equity_ratio"]),
    (r"asset", ["total_assets", "total_current_assets", "total_non_current_assets"], []),
    (r"liabilit", ["total_current_liabilities", "total_non_current_liabilities"], []),
    (r"liquid|current ratio|working capital", ["total_current_assets", "total_current_liabilities", "cash_and_cash_equivalents"], ["current_ratio"]),
    (r"receivable|debtor|collection", ["trade_receivables"], ["receivable_days"]),
    (r"\bcash\b", ["cash_and_cash_equivalents"], []),
    (r"inventor|stock", ["inventories"], []),
    (r"margin|ebitda|operating|profitab", [], ["ebitda_margin_pct", "net_profit_margin_pct"]),
    (r"expense|(?<!finance )\bcosts?\b", ["total_expenses", "cost_of_materials", "employee_benefits", "other_expenses", "depreciation_amortisation", "finance_costs"], []),
    (r"\bincome\b", ["total_income", "other_income"], []),
    (r"\btax", ["total_tax_expense"], []),
    (r"\beps\b|per share", ["eps_basic"], []),
]
BROAD = r"why|explain|overview|summar|perform|\byear\b|story|trend|compare|key figures|main|highlight|fell|fall|drop|declin|grew|growth|increase"


def _wanted_bases(question: str, available: list[str]) -> list[str]:
    q = question.lower()
    wants_consolidated = bool(re.search(r"consolidated|\bgroup\b", q))
    wants_standalone = bool(re.search(r"stand[- ]?alone|company only|\bparent\b", q))
    if wants_consolidated and not wants_standalone:
        chosen = ["consolidated"]
    elif wants_standalone and not wants_consolidated:
        chosen = ["standalone"]
    else:
        chosen = ["standalone", "consolidated", "unspecified"]
    return [basis for basis in chosen if basis in available]


def select_keys(question: str) -> tuple[list[str], list[str]]:
    q = question.lower()
    items: list[str] = []
    metrics: list[str] = []
    for pattern, item_keys, metric_keys in KEYWORDS:
        if re.search(pattern, q):
            items += item_keys
            metrics += metric_keys
    if not items and not metrics or re.search(BROAD, q):
        items += CORE_ITEMS
        metrics += CORE_METRICS
    return list(dict.fromkeys(items)), list(dict.fromkeys(metrics))


def build_verified_figures(document: dict, question: str) -> dict:
    output = {"tool": "get_verified_figures", "bases": [], "figures": [], "metrics": [], "checks": {"passed": 0, "total": 0}}
    try:
        extraction = extract_financial_statements(document)
    except Exception:  # extraction must never break the analysis agent
        output["note"] = "The financial statements could not be read, so no verified figures are available."
        return output
    statements = extraction["statements"]
    if not statements:
        output["note"] = "No financial statements were recognised in this document, so no verified figures are available."
        return output

    bases = _wanted_bases(question, list(statements))
    output["bases"] = bases
    item_keys, metric_keys = select_keys(question)

    for basis in bases:
        for statement_name in ("profit_and_loss", "balance_sheet"):
            statement = statements[basis].get(statement_name)
            if not statement:
                continue
            for key in item_keys:
                value = statement["values"].get(key)
                if value:
                    output["figures"].append({
                        "basis": basis, "key": key, "label": LABELS.get(key, key), "current": value["current"],
                        "previous": value["previous"], "page": value["page"], "unit": statement.get("unit"),
                        "periods": statement.get("periods", []),
                    })
        computed = compute_metrics(statements, basis)
        for key in metric_keys:
            metric = computed.get(key)
            if metric:
                output["metrics"].append({
                    "basis": basis, "key": key, "label": metric["label"], "unit": metric["unit"], "current": metric["current"],
                    "previous": metric["previous"], "formula": metric["formula"],
                    "pages": sorted({item["page"] for item in metric["inputs"]}),
                })

    relevant_checks = [c for c in extraction["checks"] if c["basis"] in bases]
    output["checks"] = {"passed": sum(1 for c in relevant_checks if c["ok"]), "total": len(relevant_checks)}
    if not output["figures"] and not output["metrics"]:
        output["note"] = "The statements were read, but none of the extracted line items match this question."
    return output


def format_for_prompt(verified: dict | None) -> str:
    """Compact text block for the LLM prompt. Empty string when there is nothing to say."""
    if not verified or not (verified.get("figures") or verified.get("metrics")):
        return ""
    lines = []
    for figure in verified["figures"]:
        periods = figure.get("periods") or []
        cur, prev = periods[:2] if len(periods) >= 2 else ("current year", "previous year")
        unit = f" ({figure['unit']})" if figure.get("unit") else ""
        lines.append(f"- [{figure['basis']}] {figure['label']}{unit}: {cur} = {figure['current']:,.2f}; {prev} = {figure['previous']:,.2f} (statement page {figure['page']})")
    for metric in verified["metrics"]:
        previous = f"; previous year = {metric['previous']}" if metric.get("previous") is not None else ""
        pages = ", ".join(str(p) for p in metric["pages"])
        lines.append(f"- [{metric['basis']}] {metric['label']} ({metric['unit']}): current year = {metric['current']}{previous}; formula: {metric['formula']} (pages {pages})")
    return "\n".join(lines)
