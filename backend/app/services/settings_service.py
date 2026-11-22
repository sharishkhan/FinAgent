"""Read-only settings overview and a live AI connection test.

Never returns or logs the API key; it only reports whether one is set.
"""
import time

from .llm_service import LLMSummaryError, _generate_text, get_llm_config
from .persistence_service import get_database_path, get_storage_counts
from .sample_service import SAMPLE_PATH


def get_settings_overview() -> dict:
    config = get_llm_config()
    return {
        "success": True,
        "llm": {
            "provider": config["provider"],
            "model": config["model"],
            "key_configured": bool(config["api_key"]),
            "configured": config["configured"],
        },
        "storage": {"database_path": str(get_database_path().resolve()), "counts": get_storage_counts()},
        "sample_installed": SAMPLE_PATH.is_file(),
    }


def _classify(status_code: int) -> str:
    if status_code in (400, 401, 403):
        return "key_or_request"
    if status_code == 404:
        return "model"
    if status_code == 429:
        return "quota"
    if status_code >= 500:
        return "provider_down"
    return "error"


def check_llm_connection() -> dict:
    config = get_llm_config()
    base = {"provider": config["provider"], "model": config["model"]}
    if not config["configured"]:
        return {**base, "success": False, "status": "not_configured",
                "message": "No API key is set. Add LLM_API_KEY and LLM_MODEL to backend/.env, then restart the backend."}

    started = time.monotonic()
    try:
        _generate_text(config, "You are a connection test.", "Reply with the single word OK.")
    except LLMSummaryError as exc:
        return {**base, "success": False, "status": _classify(exc.status_code), "message": str(exc)}

    return {**base, "success": True, "status": "ok",
            "message": "Connected. The AI provider answered the test request.",
            "latency_ms": round((time.monotonic() - started) * 1000)}
