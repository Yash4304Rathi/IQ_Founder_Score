"""Simple JSON-file history for prototype runs."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "scoring_history.json")


def load_history() -> list[dict]:
    if not os.path.exists(_HISTORY_PATH):
        return []
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_all(entries: list[dict]) -> None:
    with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def save_run(
    founder_name: str,
    company_name: str,
    linkedin_url: str,
    match_confidence: str,
    url_source: str,
    result: dict,
    profile: dict | None = None,
) -> dict:
    """Append a new run to history and return the stored entry."""
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "founder_name": founder_name,
        "company_name": company_name,
        "linkedin_url": linkedin_url,
        "url_source": url_source,
        "match_confidence": match_confidence,
        "overall_linkedin_fit": result.get("overall_linkedin_fit", 0),
        "grade": result.get("grade", ""),
        "summary": result.get("summary", ""),
        "result": result,
        "profile": profile or {},
    }
    entries = load_history()
    entries.append(entry)
    _save_all(entries)
    return entry


def delete_entry(entry_id: str) -> None:
    entries = [e for e in load_history() if e.get("id") != entry_id]
    _save_all(entries)
