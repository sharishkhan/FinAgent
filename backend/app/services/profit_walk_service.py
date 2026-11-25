"""Profit walk: explains the change in profit between two years as a bridge.

Each step is how much one part of the income statement moved profit up or down.
Everything is calculated in code from the extracted statements (no AI), and the
steps add up exactly to the change in profit for the year. Anything the
statements do not itemise is shown as its own "Other (not itemised)" step instead
of being hidden.
"""
from __future__ import annotations

from .statement_extractor import extract_financial_statements

REQUIRED = ["revenue_from_operations", "total_income", "total_expenses", "profit_before_exceptional_and_tax",
            "profit_before_tax", "profit_for_the_year"]
COST_LINES = [
    ("cost_of_materials", "Cost of materials consumed"),
    ("purchases_stock_in_trade", "Purchases of stock-in-trade"),
    ("changes_in_inventories", "Changes in inventories"),
    ("employee_benefits", "Employee benefits expense"),
    ("depreciation_amortisation", "Depreciation and amortisation"),
    ("other_expenses", "Other expenses"),
    ("finance_costs", "Finance costs"),
]
TOLERANCE = 0.005


def _money(value: float) -> str:
    return f"{abs(value):,.2f}"


def _step(key, label, effect, previous, current, pages):
    return {"key": key, "label": label, "effect": round(effect, 2), "previous": round(previous, 2), "current": round(current, 2),
            "pages": sorted(set(pages)), "direction": "up" if effect > TOLERANCE else "down" if effect < -TOLERANCE else "flat"}


def build_walk(values: dict, page: int) -> tuple[dict | None, list[str]]:
    missing = [key for key in REQUIRED if key not in values]
    if missing:
        return None, missing

    v = {key: (item["previous"], item["current"]) for key, item in values.items()}

    def delta(key):
        return v[key][1] - v[key][0]

    steps = []
    steps.append(_step("revenue_from_operations", "Revenue from operations", delta("revenue_from_operations"),
                       v["revenue_from_operations"][0], v["revenue_from_operations"][1], [page]))

    other_prev = v["total_income"][0] - v["revenue_from_operations"][0]
    other_cur = v["total_income"][1] - v["revenue_from_operations"][1]
    steps.append(_step("other_income", "Other income", other_cur - other_prev, other_prev, other_cur, [page]))

    itemised_prev = itemised_cur = 0.0
    for key, label in COST_LINES:
        if key in v:
            itemised_prev += v[key][0]
            itemised_cur += v[key][1]
            steps.append(_step(key, label, -(v[key][1] - v[key][0]), v[key][0], v[key][1], [page]))

    rest_prev = v["total_expenses"][0] - itemised_prev
    rest_cur = v["total_expenses"][1] - itemised_cur
    if abs(rest_cur - rest_prev) > TOLERANCE:
        steps.append(_step("other_cost_lines", "Other cost lines (not itemised separately)", -(rest_cur - rest_prev), rest_prev, rest_cur, [page]))

    pbe_prev, pbe_cur = v["profit_before_exceptional_and_tax"]
    pbt_prev, pbt_cur = v["profit_before_tax"]
    pat_prev, pat_cur = v["profit_for_the_year"]
    exc_prev, exc_cur = pbe_prev - pbt_prev, pbe_cur - pbt_cur  # expense amounts, whatever sign the report prints
    steps.append(_step("exceptional_items", "Exceptional items", -(exc_cur - exc_prev), exc_prev, exc_cur, [page]))
    tax_prev, tax_cur = pbt_prev - pat_prev, pbt_cur - pat_cur
    steps.append(_step("tax", "Tax", -(tax_cur - tax_prev), tax_prev, tax_cur, [page]))

    change = pat_cur - pat_prev
    residual = change - sum(step["effect"] for step in steps)
    reconciled = abs(residual) <= max(0.05, abs(change) * 0.001)
    if abs(residual) > TOLERANCE:
        steps.append(_step("unitemised", "Other (not itemised)", residual, 0.0, residual, [page]))

    pbe_change = pbe_cur - pbe_prev
    walk = {
        "start": round(pat_prev, 2), "end": round(pat_cur, 2), "change": round(change, 2),
        "steps": steps, "reconciled": reconciled, "page": page,
        "operating": {
            "profit_before_exceptional_previous": round(pbe_prev, 2), "profit_before_exceptional_current": round(pbe_cur, 2),
            "change": round(pbe_change, 2),
            "change_pct": round(pbe_change / abs(pbe_prev) * 100, 2) if pbe_prev else None,
        },
    }
    revenue_prev, revenue_cur = v["revenue_from_operations"]
    walk["revenue_growth_pct"] = round((revenue_cur / revenue_prev - 1) * 100, 2) if revenue_prev else None
    ranked = sorted((s for s in steps if s["direction"] != "flat"), key=lambda s: abs(s["effect"]), reverse=True)
    walk["drivers"] = [{**s, "share_of_change_pct": round(s["effect"] / change * 100, 1) if abs(change) > TOLERANCE else None} for s in ranked[:3]]
    walk["sentences"] = _sentences(walk, pat_prev, pat_cur, steps)
    return walk, []


def _sentences(walk: dict, pat_prev: float, pat_cur: float, steps: list[dict]) -> list[str]:
    sentences = []
    change = walk["change"]
    if pat_prev > 0 > pat_cur:
        sentences.append(f"Profit swung from a profit of {_money(pat_prev)} to a loss of {_money(pat_cur)}, a move of {_money(change)}.")
    elif pat_prev < 0 < pat_cur:
        sentences.append(f"Profit swung from a loss of {_money(pat_prev)} to a profit of {_money(pat_cur)}, a move of {_money(change)}.")
    elif abs(change) <= TOLERANCE:
        sentences.append(f"Profit was unchanged at {_money(pat_cur)}.")
    else:
        verb = "rose" if change > 0 else "fell"
        sentences.append(f"Profit {verb} by {_money(change)}, from {pat_prev:,.2f} to {pat_cur:,.2f}.")

    growth = walk.get("revenue_growth_pct")
    operating = walk["operating"]
    if growth is not None:
        sentences.append(f"Revenue from operations {'grew' if growth >= 0 else 'fell'} {abs(growth):.2f}%.")
    if operating["change"]:
        pct = f" ({operating['change_pct']:+.1f}%)" if operating["change_pct"] is not None else ""
        verb = "rose" if operating["change"] > 0 else "fell"
        sentences.append(f"Profit before exceptional items and tax {verb} by {_money(operating['change'])}{pct}.")
    exceptional = next((s for s in steps if s["key"] == "exceptional_items"), None)
    if exceptional and exceptional["direction"] != "flat":
        verb = "cost" if exceptional["effect"] < 0 else "added"
        sentences.append(f"Exceptional items {verb} {_money(exceptional['effect'])} to profit.")
    return sentences


def build_profit_walks(document: dict) -> dict:
    result = {"walks": {}, "warnings": []}
    try:
        extraction = extract_financial_statements(document)
    except Exception:
        result["warnings"].append("The financial statements could not be read, so no profit walk is available.")
        return result

    statements = extraction["statements"]
    if not statements:
        result["warnings"].append("No financial statements were recognised in this document.")
        return result

    for basis, parts in statements.items():
        pl = parts.get("profit_and_loss")
        if not pl:
            continue
        walk, missing = build_walk(pl["values"], pl["page"])
        if walk is None:
            result["warnings"].append(f"The {basis} profit walk could not be built: the statement is missing {', '.join(missing)}.")
            continue
        walk["unit"] = pl.get("unit")
        walk["periods"] = pl.get("periods", [])
        result["walks"][basis] = walk
    if not result["walks"] and not result["warnings"]:
        result["warnings"].append("No profit and loss statement was recognised in this document.")
    return result
