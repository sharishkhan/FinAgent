from __future__ import annotations

from .financial_tools_service import FinancialToolError, execute_financial_tool
from .guards import check_question_guards
from .llm_service import (
    LLMSummaryError,
    generate_agent_final_answer,
    generate_analysis_tool_plan,
)

MAX_TOOL_CALLS = 4
MAX_QUESTION_CHARACTERS = 1200
APPROVED_AGENT_TOOLS = {
    "search_document",
    "calculate_revenue_growth",
    "calculate_profit_margin",
}


class AgentAnalysisError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _normalize_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise AgentAnalysisError("A non-empty analysis question is required.", 400)

    normalized = question.strip()
    if len(normalized) > MAX_QUESTION_CHARACTERS:
        raise AgentAnalysisError(
            f"Analysis question must be {MAX_QUESTION_CHARACTERS} characters or fewer.",
            400,
        )

    return normalized


def _execute_tool_trace(tool_name: str, inputs: dict, document: dict) -> dict:
    trace_item = {
        "tool": tool_name,
        "inputs": inputs if isinstance(inputs, dict) else {},
        "status": "error",
    }

    try:
        output = execute_financial_tool(tool_name, trace_item["inputs"], document)
    except FinancialToolError as exc:
        trace_item["error"] = str(exc)
        return trace_item

    trace_item["status"] = "success"
    trace_item["output"] = output
    return trace_item


def _collect_sources(tool_trace: list[dict]) -> list[dict]:
    sources = []
    seen = set()

    for trace in tool_trace:
        if trace.get("tool") != "search_document" or trace.get("status") != "success":
            continue

        for source in trace.get("output", {}).get("sources", []):
            source_key = source.get("chunk_id") or (source.get("page"), source.get("excerpt"))
            if source_key in seen:
                continue
            seen.add(source_key)
            sources.append(source)

    return sources


def _collect_calculations(tool_trace: list[dict]) -> list[dict]:
    calculations = []

    for trace in tool_trace:
        if trace.get("status") != "success":
            continue
        if trace.get("tool") not in {"calculate_revenue_growth", "calculate_profit_margin"}:
            continue
        calculations.append(trace.get("output", {}))

    return calculations


def _build_findings(sources: list[dict], calculations: list[dict]) -> list[str]:
    findings = []

    for calculation in calculations:
        if calculation.get("metric") == "revenue_growth":
            findings.append(
                (
                    f"Revenue growth calculated from {calculation.get('prior_label')} "
                    f"to {calculation.get('current_label')}: "
                    f"{calculation.get('growth_percentage')}%."
                )
            )
        elif calculation.get("metric") == "profit_margin":
            findings.append(
                (
                    f"Profit margin calculated using {calculation.get('profit_label')} "
                    f"and {calculation.get('revenue_label')}: "
                    f"{calculation.get('margin_percentage')}%."
                )
            )

    if sources:
        pages = sorted({source["page"] for source in sources})
        findings.append(f"Relevant document evidence was retrieved from page(s): {', '.join(str(page) for page in pages)}.")

    return findings


def _validated_calculation_calls(plan: dict) -> tuple[list[dict], list[str]]:
    limitations = list(plan.get("limitations", []))
    calls = []

    for item in plan.get("tool_calls", []):
        if len(calls) >= MAX_TOOL_CALLS - 1:
            limitations.append("Additional tool calls were skipped because the bounded tool-call limit was reached.")
            break

        if not isinstance(item, dict):
            limitations.append("A malformed tool call was ignored.")
            continue

        tool_name = item.get("tool")
        inputs = item.get("inputs", {})

        if tool_name not in APPROVED_AGENT_TOOLS:
            limitations.append(f"Unapproved tool '{tool_name}' was ignored.")
            continue

        if tool_name == "search_document":
            limitations.append("Additional document searches from the model plan were skipped after the grounding search.")
            continue

        calls.append({"tool": tool_name, "inputs": inputs if isinstance(inputs, dict) else {}})

    return calls, limitations


def analyze_document_with_agent(document: dict, question: str) -> dict:
    normalized_question = _normalize_question(question)
    tool_trace = []
    limitations = []

    guard_result = check_question_guards(document, normalized_question)
    if guard_result is not None:
        guard_name, guard_message = guard_result
        return {
            "success": True,
            "status": "insufficient_evidence",
            "document_id": document["document_id"],
            "question": normalized_question,
            "answer": guard_message,
            "findings": [],
            "calculations": [],
            "source_pages": [],
            "sources": [],
            "tools_executed": [],
            "limitations": [f"Question declined by the '{guard_name}' guard before any document search."],
            "disclaimer": "Agentic financial analysis is document-grounded and not investment advice.",
        }

    search_trace = _execute_tool_trace(
        "search_document",
        {"query": normalized_question, "limit": 6},
        document,
    )
    tool_trace.append(search_trace)

    sources = _collect_sources(tool_trace)
    source_pages = sorted({source["page"] for source in sources})

    if not sources:
        answer = "The uploaded document does not provide enough evidence to answer this analysis question."
        return {
            "success": True,
            "status": "insufficient_evidence",
            "document_id": document["document_id"],
            "question": normalized_question,
            "answer": answer,
            "findings": [],
            "calculations": [],
            "source_pages": [],
            "sources": [],
            "tools_executed": tool_trace,
            "limitations": [
                "No relevant document passages were retrieved for the analysis question."
            ],
            "disclaimer": "Agentic financial analysis is document-grounded and not investment advice.",
        }

    try:
        plan = generate_analysis_tool_plan(
            question=normalized_question,
            sources=sources,
            filename=document["filename"],
        )
    except LLMSummaryError as exc:
        raise AgentAnalysisError(str(exc), exc.status_code) from exc

    if not plan.get("configured"):
        return {
            **plan,
            "document_id": document["document_id"],
            "question": normalized_question,
            "answer": plan.get("message"),
            "findings": _build_findings(sources, []),
            "calculations": [],
            "source_pages": source_pages,
            "sources": sources,
            "tools_executed": tool_trace,
            "limitations": ["The LLM provider is not configured for agentic analysis."],
            "disclaimer": "Agentic financial analysis requires backend LLM configuration. Not investment advice.",
        }

    calculation_calls, plan_limitations = _validated_calculation_calls(plan)
    limitations.extend(plan_limitations)

    for call in calculation_calls:
        tool_trace.append(_execute_tool_trace(call["tool"], call["inputs"], document))

    calculations = _collect_calculations(tool_trace)

    try:
        final_answer = generate_agent_final_answer(
            question=normalized_question,
            sources=sources,
            calculations=calculations,
            tool_trace=tool_trace,
            filename=document["filename"],
        )
    except LLMSummaryError as exc:
        raise AgentAnalysisError(str(exc), exc.status_code) from exc

    if not final_answer.get("configured"):
        return {
            **final_answer,
            "document_id": document["document_id"],
            "question": normalized_question,
            "answer": final_answer.get("message"),
            "findings": _build_findings(sources, calculations),
            "calculations": calculations,
            "source_pages": source_pages,
            "sources": sources,
            "tools_executed": tool_trace,
            "limitations": limitations + ["The LLM provider is not configured for final analysis."],
            "disclaimer": "Agentic financial analysis requires backend LLM configuration. Not investment advice.",
        }

    failed_calculations = [
        f"{trace['tool']}: {trace.get('error')}"
        for trace in tool_trace
        if trace.get("status") == "error" and trace.get("tool") != "search_document"
    ]
    limitations.extend(failed_calculations)

    return {
        "success": True,
        "configured": True,
        "status": "analyzed",
        "document_id": document["document_id"],
        "question": normalized_question,
        "answer": final_answer["answer"],
        "findings": _build_findings(sources, calculations),
        "calculations": calculations,
        "source_pages": source_pages,
        "sources": sources,
        "tools_executed": tool_trace,
        "limitations": limitations,
        "provider": final_answer.get("provider") or plan.get("provider"),
        "model": final_answer.get("model") or plan.get("model"),
        "disclaimer": final_answer.get(
            "disclaimer",
            "AI-generated financial analysis grounded in document evidence and verified tool outputs. Not investment advice.",
        ),
    }
