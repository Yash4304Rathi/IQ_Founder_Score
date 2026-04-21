"""Pitch deck parsing helper.

Only used for context enrichment in the prototype: if a pitch deck is uploaded,
we extract plain text so the scorer and profile matcher can use it. We keep
this deliberately small — no slide-by-slide structural parsing yet.
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional

from pypdf import PdfReader


def extract_text(file_bytes: bytes, max_chars: int = 15000) -> str:
    """Extract concatenated text from a pitch deck PDF (best-effort)."""
    if not file_bytes:
        return ""
    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception:
        return ""

    chunks: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            chunks.append(txt.strip())

    text = "\n\n".join(chunks).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (truncated)"
    return text


def short_context_hint(deck_text: str, max_chars: int = 1200) -> Optional[str]:
    """Return a condensed snippet from the deck text to help the profile
    matcher (e.g. a few early lines mentioning company/sector).
    """
    if not deck_text:
        return None
    snippet = deck_text.strip().replace("\n", " ")
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars]
    return snippet
