"""LinkedIn-only founder summary + light scorecard using Claude.

The prototype intentionally keeps scoring modest:
- four sub-scores (0-10) that LinkedIn data can reasonably support
- one overall LinkedIn-fit score (0-100) and a coarse grade
- a confidence score and explicit "missing information" list

The model is instructed to cite evidence from the profile for every score.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()

_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
_client: Optional[anthropic.Anthropic] = None


def _anthropic() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is missing. Add it to .env before running."
            )
        _client = anthropic.Anthropic(api_key=key)
    return _client


IQ_CONTEXT = """\
India Quotient (IQ) is an early-stage Indian VC fund investing at pre-seed,
seed, and pre-Series A. IQ leans toward founders with:
- deep founder-market fit and lived experience of the problem
- evidence of hustle, execution, and shipping things
- credibility signals (strong past employers, prior founding experience,
  meaningful technical or operator track record)
- India / Bharat insight where relevant

The prototype below only has access to a LinkedIn profile (and optionally a
short pitch deck excerpt). Do NOT overclaim — if the profile is thin, say so
and reflect that in `confidence_score` and `missing_information`.
"""

SYSTEM_PROMPT = (
    "You are an analyst at India Quotient. Read a LinkedIn profile and an "
    "optional pitch deck excerpt, and produce a LinkedIn-only founder "
    "assessment. You MUST output a single valid JSON object and nothing else. "
    "Every sub-score must cite concrete evidence from the profile text."
)

USER_TEMPLATE = """{context}

INPUTS
------
Founder name (as entered): {founder_name}
Company name (as entered): {company_name}
LinkedIn profile URL used: {linkedin_url}

LINKEDIN PROFILE
----------------
{profile_text}

PITCH DECK EXCERPT (optional — may be empty)
--------------------------------------------
{deck_text}

TASK
----
Return ONLY a JSON object with exactly these keys:

{{
  "summary": "2-3 sentence founder summary based only on the profile",
  "career_signal": {{
    "score": <0-10 integer>,
    "reasoning": "1-2 sentences citing specific roles / companies / progression"
  }},
  "founder_relevance": {{
    "score": <0-10 integer>,
    "reasoning": "whether the profile suggests builder/founder type (founding roles, shipping, entrepreneurship)"
  }},
  "execution_signal": {{
    "score": <0-10 integer>,
    "reasoning": "evidence of shipping, scope of responsibility, measurable outcomes"
  }},
  "credibility_signal": {{
    "score": <0-10 integer>,
    "reasoning": "education, employers, recognitions, notable credentials"
  }},
  "overall_linkedin_fit": <0-100 integer>,
  "grade": "Strong Yes" | "Lean Yes" | "Maybe" | "Lean No" | "Strong No",
  "confidence_score": <0-10 integer — how confident you are given the data available>,
  "strengths": ["3-5 concrete strengths supported by the profile"],
  "concerns": ["2-4 gaps or concerns — can include 'profile is thin'"],
  "missing_information": ["things you could NOT determine from LinkedIn alone"],
  "next_questions_for_diligence": ["3-5 sharp questions an IQ analyst should ask next"]
}}

Rules:
- Do not invent facts that are not in the profile or deck.
- If the profile is sparse, give low confidence and list what is missing.
- Keep reasoning short and evidence-based.
"""


def score_founder(
    founder_name: str,
    company_name: Optional[str],
    linkedin_url: str,
    profile_text: str,
    deck_text: Optional[str] = None,
) -> dict:
    """Run the LLM and return a parsed scorecard dict.

    Raises on transport errors; JSON parse failures return a minimal error dict
    so the UI can still render something.
    """
    prompt = USER_TEMPLATE.format(
        context=IQ_CONTEXT,
        founder_name=founder_name or "(not provided)",
        company_name=company_name or "(not provided)",
        linkedin_url=linkedin_url or "(not provided)",
        profile_text=profile_text or "(no profile data available)",
        deck_text=deck_text or "(no deck provided)",
    )

    message = _anthropic().messages.create(
        model=_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()

    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    """Parse the LLM response, tolerating stray code fences or prose."""
    if not raw:
        return _error_result("empty model response")

    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return _error_result("could not parse model JSON", raw=raw)


def _error_result(message: str, raw: str = "") -> dict:
    return {
        "summary": f"Scoring error: {message}.",
        "career_signal": {"score": 0, "reasoning": ""},
        "founder_relevance": {"score": 0, "reasoning": ""},
        "execution_signal": {"score": 0, "reasoning": ""},
        "credibility_signal": {"score": 0, "reasoning": ""},
        "overall_linkedin_fit": 0,
        "grade": "Maybe",
        "confidence_score": 0,
        "strengths": [],
        "concerns": [message],
        "missing_information": ["LLM response could not be parsed"],
        "next_questions_for_diligence": [],
        "_raw": raw,
    }
