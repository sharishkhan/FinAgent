import json
import os
import urllib.error
import urllib.request


class LLMSummaryError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def get_llm_config() -> dict:
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    api_base_url = os.getenv("LLM_API_BASE_URL", "").strip()

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "api_base_url": api_base_url,
        "configured": bool(api_key and model),
    }


def _build_prompt(document: dict) -> str:
    text = document["text"][:18000]

    return (
        "You are a careful financial research assistant summarizing a financial PDF. "
        "Use ONLY facts explicitly present in the provided document text. "
        "Do not invent figures, risks, conclusions, or financial information. "
        "Do not provide investment advice or recommendations. "
        "If information is not present, say that it is not stated in the document. "
        "Return a concise structured summary using exactly these sections:\n\n"
        "## Document Overview\n"
        "## Main Financial Themes\n"
        "## Important Reported Figures\n"
        "## Major Risks Mentioned\n"
        "## Key Takeaways\n\n"
        f"Filename: {document['filename']}\n\n"
        f"Document text:\n{text}"
    )


def _build_question_prompt(question: str, sources: list[dict], filename: str) -> str:
    passages = "\n\n".join(
        (
            f"Source {index} | Page {source['page']} | Chunk {source['chunk_id']}:\n"
            f"{source['excerpt']}"
        )
        for index, source in enumerate(sources, start=1)
    )

    return (
        "You are a financial document research assistant. Answer the question using "
        "ONLY the source passages below. Do not use outside knowledge and do not invent "
        "figures, dates, or citations. If the passages do not contain the answer, say "
        "clearly that the document does not provide it. When the passages contain both "
        "standalone and consolidated figures, say which one you are quoting. Cite the "
        "source page inline, for example (Page 12). In some Indian annual reports the "
        "rupee symbol is extracted as a stray letter such as H or I before a number; "
        "treat it as rupees. Keep the answer concise and do not give investment advice.\n\n"
        f"Filename: {filename}\n"
        f"Question: {question}\n\n"
        f"Source passages:\n{passages}"
    )


def _extract_json_object(text: str) -> dict:
    candidate = text.strip()

    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise LLMSummaryError("The AI provider returned an invalid tool plan.", 502)
        parsed = json.loads(candidate[start : end + 1])

    if not isinstance(parsed, dict):
        raise LLMSummaryError("The AI provider returned an invalid tool plan.", 502)

    return parsed


def _build_agent_tool_plan_prompt(question: str, sources: list[dict], filename: str) -> str:
    passages = "\n\n".join(
        (
            f"Source {index} | Page {source['page']} | Chunk {source['chunk_id']}:\n"
            f"{source['excerpt']}"
        )
        for index, source in enumerate(sources, start=1)
    )

    return (
        "You are planning bounded financial analysis tool calls for an uploaded PDF. "
        "Return ONLY valid JSON. Do not include markdown. "
        "You may choose only these calculation tools: calculate_revenue_growth and "
        "calculate_profit_margin. Do not choose tools unless all numeric inputs are "
        "explicitly present in the source passages or the user's question. Do not infer, "
        "estimate, annualize, normalize, or invent figures. If a calculation cannot be "
        "supported, return an empty tool_calls array and explain the limitation.\n\n"
        "JSON schema:\n"
        "{\n"
        '  "tool_calls": [\n'
        '    {"tool": "calculate_revenue_growth", "inputs": {"prior_revenue": 100, "current_revenue": 120, "prior_label": "2023 revenue", "current_label": "2024 revenue", "evidence": "short quote or source description"}},\n'
        '    {"tool": "calculate_profit_margin", "inputs": {"profit": 14, "revenue": 120, "profit_label": "net income", "revenue_label": "revenue", "evidence": "short quote or source description"}}\n'
        "  ],\n"
        '  "limitations": ["missing information, if any"]\n'
        "}\n\n"
        f"Filename: {filename}\n"
        f"Question: {question}\n\n"
        f"Source passages:\n{passages}"
    )


def _build_agent_final_prompt(
    question: str,
    sources: list[dict],
    calculations: list[dict],
    tool_trace: list[dict],
    filename: str,
) -> str:
    passages = "\n\n".join(
        (
            f"Source {index} | Page {source['page']} | Chunk {source['chunk_id']}:\n"
            f"{source['excerpt']}"
        )
        for index, source in enumerate(sources, start=1)
    )

    return (
        "You are a bounded financial analysis assistant. Answer using ONLY the "
        "retrieved passages and the verified calculation outputs below. Do not use "
        "outside knowledge. Do not invent financial facts, figures, dates, or citations. "
        "If evidence is missing, say so clearly. Keep the answer concise, cite source "
        "pages inline, and do not provide investment advice.\n\n"
        f"Filename: {filename}\n"
        f"Question: {question}\n\n"
        f"Retrieved passages:\n{passages}\n\n"
        f"Verified calculations:\n{json.dumps(calculations, ensure_ascii=True, indent=2)}\n\n"
        f"Executed tool trace:\n{json.dumps(tool_trace, ensure_ascii=True, indent=2)}"
    )


def _openai_compatible_text(config: dict, system_content: str, user_content: str, temperature: float = 0.1) -> str:
    api_base_url = config["api_base_url"] or "https://api.openai.com/v1"
    endpoint = f"{api_base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": system_content,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "temperature": temperature,
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LLMSummaryError("The AI analysis provider rejected the request.", exc.code) from exc
    except urllib.error.URLError as exc:
        raise LLMSummaryError("Could not connect to the AI analysis provider.") from exc
    except Exception as exc:
        raise LLMSummaryError("The AI analysis provider could not be reached.") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMSummaryError("The AI analysis provider returned an unexpected response.") from exc


def _gemini_text(config: dict, prompt: str, temperature: float = 0.1) -> str:
    model = config["model"]
    api_key = config["api_key"]

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent?key={api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LLMSummaryError("The Gemini analysis provider rejected the request.", exc.code) from exc
    except urllib.error.URLError as exc:
        raise LLMSummaryError("Could not connect to the Gemini API.") from exc
    except TimeoutError as exc:
        raise LLMSummaryError("The Gemini API request timed out.") from exc
    except Exception as exc:
        raise LLMSummaryError("The Gemini AI provider could not be reached.") from exc

    try:
        candidates = data["candidates"]
        if not candidates:
            raise LLMSummaryError("Gemini returned no analysis candidates.")

        parts = candidates[0]["content"]["parts"]
        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        if not text:
            raise LLMSummaryError("Gemini returned an empty analysis response.")

        return text
    except LLMSummaryError:
        raise
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMSummaryError("The Gemini provider returned an unexpected response.") from exc


def _generate_text(config: dict, system_content: str, user_content: str, temperature: float = 0.1) -> str:
    provider = config["provider"]

    if provider in {"openai", "openai-compatible"}:
        return _openai_compatible_text(
            config=config,
            system_content=system_content,
            user_content=user_content,
            temperature=temperature,
        )

    if provider == "gemini":
        return _gemini_text(
            config=config,
            prompt=f"{system_content}\n\n{user_content}",
            temperature=temperature,
        )

    raise LLMSummaryError(
        f"The configured LLM provider '{provider}' is not supported.",
        400,
    )

    return (
        "You are answering a question about an uploaded financial PDF. "
        "Use ONLY the source passages below. Do not use outside knowledge. "
        "Do not invent financial facts, figures, calculations, or citations. "
        "If the passages do not provide enough evidence, say: "
        "\"The uploaded document does not provide enough evidence to answer this question.\" "
        "Keep the answer concise and cite page numbers inline, for example: (page 3).\n\n"
        f"Filename: {filename}\n"
        f"Question: {question}\n\n"
        f"Source passages:\n{passages}"
    )


def _openai_compatible_summary(config: dict, document: dict) -> str:
    api_base_url = config["api_base_url"] or "https://api.openai.com/v1"
    endpoint = f"{api_base_url.rstrip('/')}/chat/completions"

    prompt = _build_prompt(document)

    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "You produce careful financial document summaries "
                    "without adding unsupported claims."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")

        print(
            f"[OpenAI HTTP Error] status={exc.code}",
            flush=True,
        )
        print(
            f"[OpenAI HTTP Body] {error_body}",
            flush=True,
        )

        raise LLMSummaryError(
            "The AI summary provider rejected the request.",
            exc.code,
        ) from exc

    except urllib.error.URLError as exc:
        print(
            f"[OpenAI URL Error] reason={repr(exc.reason)}",
            flush=True,
        )

        raise LLMSummaryError(
            "Could not connect to the AI summary provider."
        ) from exc

    except Exception as exc:
        print(
            f"[OpenAI Unexpected Error] type={type(exc).__name__}",
            flush=True,
        )
        print(
            f"[OpenAI Unexpected Error] message={repr(exc)}",
            flush=True,
        )

        raise LLMSummaryError(
            "The AI summary provider could not be reached."
        ) from exc

    try:
        return data["choices"][0]["message"]["content"].strip()

    except (KeyError, IndexError, TypeError) as exc:
        print(
            f"[OpenAI Response Error] {repr(exc)}",
            flush=True,
        )

        raise LLMSummaryError(
            "The AI summary provider returned an unexpected response."
        ) from exc


def _openai_compatible_answer(
    config: dict,
    question: str,
    sources: list[dict],
    filename: str,
) -> str:
    api_base_url = config["api_base_url"] or "https://api.openai.com/v1"
    endpoint = f"{api_base_url.rstrip('/')}/chat/completions"
    prompt = _build_question_prompt(question, sources, filename)

    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "You answer financial document questions only from "
                    "provided source passages and cite source pages."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.1,
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        raise LLMSummaryError(
            "The AI answer provider rejected the request.",
            exc.code,
        ) from exc

    except urllib.error.URLError as exc:
        raise LLMSummaryError(
            "Could not connect to the AI answer provider."
        ) from exc

    except Exception as exc:
        raise LLMSummaryError(
            "The AI answer provider could not be reached."
        ) from exc

    try:
        return data["choices"][0]["message"]["content"].strip()

    except (KeyError, IndexError, TypeError) as exc:
        raise LLMSummaryError(
            "The AI answer provider returned an unexpected response."
        ) from exc


def _gemini_summary(config: dict, document: dict) -> str:
    """
    Generate a financial-document summary using Google's Gemini REST API.

    No Gemini Python SDK is required. The request is made directly using
    Python's built-in urllib module.
    """

    model = config["model"]
    api_key = config["api_key"]

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent?key={api_key}"
    )

    prompt = _build_prompt(document)

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")

        print(
            f"[Gemini HTTP Error] status={exc.code}",
            flush=True,
        )
        print(
            f"[Gemini HTTP Body] {error_body}",
            flush=True,
        )

        try:
            error_data = json.loads(error_body)

            error_message = (
                error_data.get("error", {}).get("message")
                or "The Gemini provider rejected the request."
            )

        except Exception:
            error_message = "The Gemini provider rejected the request."

        raise LLMSummaryError(
            error_message,
            exc.code,
        ) from exc

    except urllib.error.URLError as exc:
        print(
            f"[Gemini URL Error] reason={repr(exc.reason)}",
            flush=True,
        )
        print(
            f"[Gemini URL Error] full={repr(exc)}",
            flush=True,
        )

        raise LLMSummaryError(
            "Could not connect to the Gemini API."
        ) from exc

    except TimeoutError as exc:
        print(
            f"[Gemini Timeout Error] {repr(exc)}",
            flush=True,
        )

        raise LLMSummaryError(
            "The Gemini API request timed out."
        ) from exc

    except Exception as exc:
        print(
            f"[Gemini Unexpected Error] type={type(exc).__name__}",
            flush=True,
        )
        print(
            f"[Gemini Unexpected Error] message={repr(exc)}",
            flush=True,
        )

        raise LLMSummaryError(
            "The Gemini AI provider could not be reached."
        ) from exc

    try:
        candidates = data["candidates"]

        if not candidates:
            print(
                "[Gemini Response Error] No candidates returned.",
                flush=True,
            )

            raise LLMSummaryError(
                "Gemini returned no summary candidates."
            )

        parts = candidates[0]["content"]["parts"]

        summary = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        if not summary:
            print(
                "[Gemini Response Error] Gemini returned empty text.",
                flush=True,
            )

            raise LLMSummaryError(
                "Gemini returned an empty summary."
            )

        return summary

    except LLMSummaryError:
        raise

    except (KeyError, IndexError, TypeError) as exc:
        print(
            f"[Gemini Response Error] type={type(exc).__name__}",
            flush=True,
        )
        print(
            f"[Gemini Response Error] message={repr(exc)}",
            flush=True,
        )

        raise LLMSummaryError(
            "The Gemini provider returned an unexpected response."
        ) from exc


def _gemini_answer(
    config: dict,
    question: str,
    sources: list[dict],
    filename: str,
) -> str:
    model = config["model"]
    api_key = config["api_key"]

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent?key={api_key}"
    )
    prompt = _build_question_prompt(question, sources, filename)

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        raise LLMSummaryError(
            "The Gemini answer provider rejected the request.",
            exc.code,
        ) from exc

    except urllib.error.URLError as exc:
        raise LLMSummaryError(
            "Could not connect to the Gemini API."
        ) from exc

    except TimeoutError as exc:
        raise LLMSummaryError(
            "The Gemini API request timed out."
        ) from exc

    except Exception as exc:
        raise LLMSummaryError(
            "The Gemini AI provider could not be reached."
        ) from exc

    try:
        candidates = data["candidates"]
        if not candidates:
            raise LLMSummaryError("Gemini returned no answer candidates.")

        parts = candidates[0]["content"]["parts"]
        answer = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        ).strip()

        if not answer:
            raise LLMSummaryError("Gemini returned an empty answer.")

        return answer

    except LLMSummaryError:
        raise

    except (KeyError, IndexError, TypeError) as exc:
        raise LLMSummaryError(
            "The Gemini provider returned an unexpected response."
        ) from exc


def generate_document_summary(document: dict) -> dict:
    config = get_llm_config()

    if not config["configured"]:
        return {
            "success": False,
            "configured": False,
            "status": "unavailable",
            "message": (
                "AI summary is not configured yet. "
                "Add an LLM API key to the backend environment "
                "to enable this feature."
            ),
        }

    provider = config["provider"]

    if provider in {"openai", "openai-compatible"}:
        summary = _openai_compatible_summary(
            config,
            document,
        )

    elif provider == "gemini":
        summary = _gemini_summary(
            config,
            document,
        )

    else:
        raise LLMSummaryError(
            f"The configured LLM provider '{provider}' is not supported.",
            400,
        )

    return {
        "success": True,
        "configured": True,
        "status": "generated",
        "provider": provider,
        "model": config["model"],
        "summary": summary,
        "disclaimer": "AI-generated summary. Not investment advice.",
    }


def generate_grounded_answer(
    question: str,
    sources: list[dict],
    filename: str,
) -> dict:
    config = get_llm_config()

    if not config["configured"]:
        return {
            "success": False,
            "configured": False,
            "status": "unavailable",
            "message": (
                "Document question answering requires an LLM API key "
                "configured in the backend environment."
            ),
        }

    provider = config["provider"]

    if provider in {"openai", "openai-compatible"}:
        answer = _openai_compatible_answer(
            config,
            question,
            sources,
            filename,
        )

    elif provider == "gemini":
        answer = _gemini_answer(
            config,
            question,
            sources,
            filename,
        )

    else:
        raise LLMSummaryError(
            f"The configured LLM provider '{provider}' is not supported.",
            400,
        )

    return {
        "success": True,
        "configured": True,
        "status": "answered",
        "provider": provider,
        "model": config["model"],
        "answer": answer,
        "disclaimer": "AI-generated answer grounded in retrieved document excerpts. Not investment advice.",
    }


def generate_analysis_tool_plan(
    question: str,
    sources: list[dict],
    filename: str,
) -> dict:
    config = get_llm_config()

    if not config["configured"]:
        return {
            "success": False,
            "configured": False,
            "status": "unavailable",
            "message": (
                "Agentic financial analysis requires an LLM API key "
                "configured in the backend environment."
            ),
        }

    prompt = _build_agent_tool_plan_prompt(
        question=question,
        sources=sources,
        filename=filename,
    )
    raw_plan = _generate_text(
        config=config,
        system_content=(
            "You produce strict JSON tool plans for bounded financial analysis. "
            "You never invent unsupported figures."
        ),
        user_content=prompt,
        temperature=0.0,
    )
    plan = _extract_json_object(raw_plan)

    tool_calls = plan.get("tool_calls", [])
    if not isinstance(tool_calls, list):
        raise LLMSummaryError("The AI provider returned an invalid tool plan.", 502)

    limitations = plan.get("limitations", [])
    if not isinstance(limitations, list):
        limitations = []

    return {
        "success": True,
        "configured": True,
        "status": "planned",
        "provider": config["provider"],
        "model": config["model"],
        "tool_calls": tool_calls,
        "limitations": [str(item) for item in limitations if str(item).strip()],
    }


def generate_agent_final_answer(
    question: str,
    sources: list[dict],
    calculations: list[dict],
    tool_trace: list[dict],
    filename: str,
) -> dict:
    config = get_llm_config()

    if not config["configured"]:
        return {
            "success": False,
            "configured": False,
            "status": "unavailable",
            "message": (
                "Agentic financial analysis requires an LLM API key "
                "configured in the backend environment."
            ),
        }

    prompt = _build_agent_final_prompt(
        question=question,
        sources=sources,
        calculations=calculations,
        tool_trace=tool_trace,
        filename=filename,
    )
    answer = _generate_text(
        config=config,
        system_content=(
            "You write concise, evidence-grounded financial analysis. "
            "You cite pages and disclose unavailable information."
        ),
        user_content=prompt,
        temperature=0.1,
    )

    return {
        "success": True,
        "configured": True,
        "status": "analyzed",
        "provider": config["provider"],
        "model": config["model"],
        "answer": answer,
        "disclaimer": "AI-generated financial analysis grounded in document evidence and verified tool outputs. Not investment advice.",
    }
