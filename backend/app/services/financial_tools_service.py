from __future__ import annotations

from typing import Any

from .retrieval_service import RetrievalError, retrieve_relevant_chunks
from .verified_figures_service import build_verified_figures


class FinancialToolError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _to_number(value: Any, field_name: str) -> float:
    if value is None or value == "":
        raise FinancialToolError(f"{field_name} is required.")

    if isinstance(value, bool):
        raise FinancialToolError(f"{field_name} must be a number.")

    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if not normalized:
            raise FinancialToolError(f"{field_name} is required.")
        try:
            number = float(normalized)
        except ValueError as exc:
            raise FinancialToolError(f"{field_name} must be a number.") from exc
    else:
        raise FinancialToolError(f"{field_name} must be a number.")

    return number


def search_document(document: dict, query: str, limit: int = 5) -> dict:
    if not isinstance(query, str) or not query.strip():
        raise FinancialToolError("search_document requires a non-empty query.")

    try:
        safe_limit = min(max(int(limit), 1), 8)
    except (TypeError, ValueError):
        safe_limit = 5

    try:
        sources = retrieve_relevant_chunks(document, query.strip(), limit=safe_limit)
    except RetrievalError as exc:
        raise FinancialToolError(str(exc), exc.status_code) from exc

    return {
        "tool": "search_document",
        "query": query.strip(),
        "sources": sources,
        "source_pages": sorted({source["page"] for source in sources}),
        "source_count": len(sources),
    }


def calculate_revenue_growth(
    prior_revenue: Any,
    current_revenue: Any,
    prior_label: str | None = None,
    current_label: str | None = None,
    evidence: str | None = None,
) -> dict:
    prior = _to_number(prior_revenue, "prior_revenue")
    current = _to_number(current_revenue, "current_revenue")

    if prior == 0:
        raise FinancialToolError("Revenue growth cannot be calculated when prior revenue is zero.")

    growth_percentage = ((current - prior) / prior) * 100

    return {
        "tool": "calculate_revenue_growth",
        "metric": "revenue_growth",
        "prior_revenue": prior,
        "current_revenue": current,
        "prior_label": prior_label or "Prior revenue",
        "current_label": current_label or "Current revenue",
        "growth_percentage": round(growth_percentage, 2),
        "formula": "((current_revenue - prior_revenue) / prior_revenue) * 100",
        "evidence": evidence or "",
    }


def calculate_profit_margin(
    profit: Any,
    revenue: Any,
    profit_label: str | None = None,
    revenue_label: str | None = None,
    evidence: str | None = None,
) -> dict:
    profit_value = _to_number(profit, "profit")
    revenue_value = _to_number(revenue, "revenue")

    if revenue_value == 0:
        raise FinancialToolError("Profit margin cannot be calculated when revenue is zero.")

    margin_percentage = (profit_value / revenue_value) * 100

    return {
        "tool": "calculate_profit_margin",
        "metric": "profit_margin",
        "profit": profit_value,
        "revenue": revenue_value,
        "profit_label": profit_label or "Profit",
        "revenue_label": revenue_label or "Revenue",
        "margin_percentage": round(margin_percentage, 2),
        "formula": "(profit / revenue) * 100",
        "evidence": evidence or "",
    }


REGISTERED_TOOLS = {
    "search_document": search_document,
    "calculate_revenue_growth": calculate_revenue_growth,
    "calculate_profit_margin": calculate_profit_margin,
    "get_verified_figures": build_verified_figures,
}


def execute_financial_tool(name: str, inputs: dict, document: dict) -> dict:
    if name not in REGISTERED_TOOLS:
        raise FinancialToolError(f"Tool '{name}' is not approved for execution.", 400)

    if not isinstance(inputs, dict):
        raise FinancialToolError("Tool inputs must be an object.", 400)

    if name == "search_document":
        return search_document(
            document=document,
            query=inputs.get("query", ""),
            limit=inputs.get("limit", 5),
        )

    if name == "calculate_revenue_growth":
        return calculate_revenue_growth(
            prior_revenue=inputs.get("prior_revenue"),
            current_revenue=inputs.get("current_revenue"),
            prior_label=inputs.get("prior_label"),
            current_label=inputs.get("current_label"),
            evidence=inputs.get("evidence"),
        )

    if name == "calculate_profit_margin":
        return calculate_profit_margin(
            profit=inputs.get("profit"),
            revenue=inputs.get("revenue"),
            profit_label=inputs.get("profit_label"),
            revenue_label=inputs.get("revenue_label"),
            evidence=inputs.get("evidence"),
        )

    if name == "get_verified_figures":
        return build_verified_figures(document, str(inputs.get("question", "")))

    raise FinancialToolError(f"Tool '{name}' is not approved for execution.", 400)
