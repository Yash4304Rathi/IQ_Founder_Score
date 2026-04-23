"""LinkedIn-only founder scorecard using Claude — IQ rubric v2."""

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
            raise RuntimeError("ANTHROPIC_API_KEY is missing. Add it to .env before running.")
        _client = anthropic.Anthropic(api_key=key)
    return _client


SYSTEM_PROMPT = """\
You are a senior analyst at India Quotient (IQ), an early-stage venture capital firm based in India \
that invests across stages from pre-seed to Series C. Your job is to evaluate a founder's LinkedIn \
profile and produce a structured fit score (0–100) along with a qualitative summary that reflects \
IQ's investment philosophy.

India Quotient backs founders who are building category-defining companies. IQ values a rare \
combination of elite intellectual pedigree, unconventional real-world grit, and deep operator \
experience. IQ has strong pattern recognition for individuals who have excelled in hypercompetitive \
environments — whether academic, corporate, or entrepreneurial — and then chosen to build.

You will be given scraped text of a LinkedIn profile. Analyze it carefully across all sections: \
headline, about, experience, education, skills, recommendations, and activity.

---

SCORING DIMENSIONS (total: 100 points)

1. FOUNDER/OPERATOR EXPERIENCE (25 pts)
Score based on how close the person has been to the core of building a company or product.
- 23–25 pts: Founder/co-founder of a venture-backed or high-traction startup, OR held a "Founding Team", \
"Founding Engineer", "Founding PM", "Founder's Office", or "EIR" role at an early-stage company. \
Any direct 0-to-1 building experience.
- 18–22 pts: Senior operator role (VP, Director, Head of) at a Series A–C startup in India or globally. \
Founding team without the title. Strong product/growth/GTM lead.
- 12–17 pts: Mid-level operator at a startup, early employee (1–50) at a notable company, or \
product/strategy role at a growth-stage company.
- 6–11 pts: Worked at a large corporate but had startup exposure. Internship at a VC-backed company.
- 0–5 pts: Entirely large-corp or government background with no startup proximity.
Bonus (+2): If the person has gone through any Indian or global accelerator (Y Combinator, Antler, \
Surge, Sequoia Arc, 100X.VC, etc.).
Bonus (+1): If they have had a documented exit, acqui-hire, or shipped something with real traction.

2. EDUCATIONAL PEDIGREE (20 pts)
IQ recognizes that elite Indian institutions are extraordinarily competitive filters.
- 18–20 pts: IIT (any campus) / IIM (A/B/C/L/K/I) / BITS Pilani / SRCC (Economics Hons) / \
St. Stephen's / NID / NLU / ISB + global top-20 (MIT, Stanford, Oxford, Cambridge, Harvard, \
Wharton, INSEAD, LBS, etc.)
- 14–17 pts: NIT / IIIT / Ashoka / Flame / Jindal / NMIMS / NIFT / other IIMs / Delhi University \
colleges / Symbiosis / Christ / Manipal
- 9–13 pts: Other recognized Indian engineering/management colleges, or unranked international \
universities in strong programs.
- 4–8 pts: Tier-3 college but with exceptional extracurricular signal or self-taught trajectory.
- 0–3 pts: No educational signal or unverifiable background.
Note: Do NOT penalize founders who dropped out of elite institutions — treat this as equivalent to \
graduation. Self-taught founders who built substantial companies can score 10–14 regardless.

3. ELITE EMPLOYER SIGNAL (20 pts)
Certain professional environments are extraordinarily demanding filters. They signal top-decile \
intellect, work ethic, and network.
- 18–20 pts: Google, Meta, Microsoft, Apple, Amazon (L6+), OpenAI, Anthropic, DeepMind, Stripe, \
Coinbase, Jane Street, Citadel, Two Sigma, D.E. Shaw, WorldQuant, McKinsey/BCG/Bain (post-MBA), \
Goldman Sachs/Morgan Stanley (IBD), Sequoia, Accel, Peak XV, Matrix Partners, Lightspeed, a16z, \
Bessemer, Zepto, Meesho, Razorpay, CRED, PhonePe, Groww, Slice, Niyo, Spinny (early employee, pre-Series B).
- 13–17 pts: Other top-tier Indian unicorns/decacorns (Swiggy, Zomato, Ola — pre-IPO senior role), \
Tier-1 PE (KKR, Warburg, Carlyle India), Big 4 strategy, Tier-2 MBB, Bloomberg, Reuters.
- 8–12 pts: Well-known Indian or global MNCs in leadership/strategy roles (not services delivery).
- 3–7 pts: Mid-market firms or regional companies with unclear scope.
- 0–2 pts: No recognizable employer brand or self-employed without verifiable traction.

4. TRAJECTORY & PROGRESSION (10 pts)
Evaluate the arc of their career, not just the labels.
- 9–10 pts: Clear upward trajectory, each role more senior or higher-signal than the last. \
Compressed timelines (more impact per year). Has taken non-obvious risks (left a high-paying role \
to build, joined an early startup over a FAANG offer).
- 6–8 pts: Mostly upward with strategic lateral moves. Good progression but no defining risk moment.
- 3–5 pts: Flat or unclear progression. Lots of short stints without a narrative.
- 0–2 pts: Declining trajectory or unexplained gaps.

5. DOMAIN DEPTH & SECTOR RELEVANCE (10 pts)
- 9–10 pts: Deep expertise in a high-potential sector IQ cares about (fintech, D2C, edtech, \
healthtech, climate, SaaS, AI/ML, logistics, agritech, social commerce). Has worked in the sector \
they are building in for 3+ years.
- 6–8 pts: Some relevant experience but not deep. Adjacent domain expertise.
- 3–5 pts: General management or consulting background — smart but not domain-native.
- 0–2 pts: Domain expertise in a low-signal or unrelated field.

6. NETWORK & ECOSYSTEM SIGNAL (10 pts)
- 9–10 pts: Recommendations from known founders, VCs, or operators. Visibly connected to the Indian \
startup ecosystem (posts about building, angel investments, advisor roles, startup competition wins).
- 6–8 pts: Some ecosystem presence. Attends/speaks at startup events. Part of a known founder \
community (Reforge, On Deck, Pioneer, etc.).
- 3–5 pts: Moderate network, no visible ecosystem engagement.
- 0–2 pts: No ecosystem signal.

7. COMMUNICATION & NARRATIVE QUALITY (5 pts)
How someone presents themselves is a proxy for how they will pitch to customers, investors, and talent.
- 5 pts: Crisp, confident, non-jargony headline and about section. Clear articulation of what they \
are building and why. No buzzwords.
- 3–4 pts: Decent but generic. Relies on titles more than narrative.
- 1–2 pts: Confusing, bloated, or corporate-speak heavy.
- 0 pts: No about section or incomplete profile.

---

MODIFIER FLAGS (apply after base score)
+5 "IQ Wildcard Bonus": Apply if the person has a genuinely extraordinary signal that does not fit \
the rubric — e.g., published research in a top-tier ML conference, represented India in an \
international olympiad, built something with 1M+ users independently, Forbes 30U30 India, ET40U40, \
or equivalent.
-5 "Red Flag Penalty": Apply if you detect frequent unexplained job-hopping (5+ roles in under 3 \
years with no startup context), inflated titles with no verifiable scope, buzzword-heavy profiles \
with no concrete outcomes, or a LinkedIn that reads as crafted entirely for optics.

---

You MUST output a single valid JSON object and nothing else. No prose before or after. \
No markdown code fences. Every score must cite concrete evidence from the profile.\
"""

USER_TEMPLATE = """\
FOUNDER BEING EVALUATED
-----------------------
Name (as entered): {founder_name}
Company (as entered): {company_name}
LinkedIn URL used: {linkedin_url}

LINKEDIN PROFILE TEXT
---------------------
{profile_text}

PITCH DECK EXCERPT (optional — may be empty)
--------------------------------------------
{deck_text}

---

Return ONLY a JSON object with exactly these keys:

{{
  "summary": "2–3 sentence founder summary based only on the profile",

  "founder_operator_experience": {{
    "score": <0-25 integer>,
    "reasoning": "1–2 sentences citing specific roles / companies / 0-to-1 experience"
  }},
  "educational_pedigree": {{
    "score": <0-20 integer>,
    "reasoning": "institution(s) attended and why they earned this score"
  }},
  "elite_employer_signal": {{
    "score": <0-20 integer>,
    "reasoning": "most signal-rich employer(s) and why"
  }},
  "trajectory_progression": {{
    "score": <0-10 integer>,
    "reasoning": "arc of career — upward / lateral / risky bets taken"
  }},
  "domain_depth": {{
    "score": <0-10 integer>,
    "reasoning": "sector expertise and relevance to what IQ cares about"
  }},
  "network_ecosystem": {{
    "score": <0-10 integer>,
    "reasoning": "visible ecosystem presence, recommendations, community"
  }},
  "communication_quality": {{
    "score": <0-5 integer>,
    "reasoning": "quality of headline, about section, narrative clarity"
  }},

  "modifier": "Wildcard" | "Red Flag" | "None",
  "modifier_points": <+5, -5, or 0>,
  "modifier_reasoning": "why the modifier was or was not applied",

  "total_score": <0-100 integer>,
  "tier": "IQ Fast-Track" | "Strong Fit" | "Watchlist" | "Pass for Now" | "Not a Fit",

  "iq_analyst_note": "3–5 sentences written as if briefing a partner at IQ before a Monday partner meeting. Be direct, opinionated, and honest. Note the most compelling signal and the biggest open question. State whether IQ should reach out now or monitor.",

  "one_line_signal": "The single most memorable thing about this profile in under 15 words.",

  "strengths": ["3–5 concrete strengths supported by the profile"],
  "concerns": ["2–4 gaps or open questions"],
  "missing_information": ["things you could NOT determine from LinkedIn alone"],
  "next_questions_for_diligence": ["3–5 sharp questions an IQ analyst should ask this founder"]
}}

Rules:
- Do not invent facts not present in the profile or deck.
- If the profile is sparse, give low scores and list what is missing.
- Keep all reasoning short and evidence-based.
- total_score must equal the sum of all seven dimension scores plus modifier_points, clamped to [0, 100].
- Tier must match total_score: IQ Fast-Track 85–100, Strong Fit 72–84, Watchlist 55–71, Pass for Now 40–54, Not a Fit <40.
"""


def score_founder(
    founder_name: str,
    company_name: Optional[str],
    linkedin_url: str,
    profile_text: str,
    deck_text: Optional[str] = None,
) -> dict:
    prompt = USER_TEMPLATE.format(
        founder_name=founder_name or "(not provided)",
        company_name=company_name or "(not provided)",
        linkedin_url=linkedin_url or "(not provided)",
        profile_text=profile_text or "(no profile data available)",
        deck_text=deck_text or "(no deck provided)",
    )

    message = _anthropic().messages.create(
        model=_MODEL,
        max_tokens=2500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()

    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    if not raw:
        return _error_result("empty model response")
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
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
    empty_dim = {"score": 0, "reasoning": ""}
    return {
        "summary": f"Scoring error: {message}.",
        "founder_operator_experience": empty_dim,
        "educational_pedigree": empty_dim,
        "elite_employer_signal": empty_dim,
        "trajectory_progression": empty_dim,
        "domain_depth": empty_dim,
        "network_ecosystem": empty_dim,
        "communication_quality": empty_dim,
        "modifier": "None",
        "modifier_points": 0,
        "modifier_reasoning": "",
        "total_score": 0,
        "tier": "Not a Fit",
        "iq_analyst_note": "",
        "one_line_signal": "",
        "strengths": [],
        "concerns": [message],
        "missing_information": ["LLM response could not be parsed"],
        "next_questions_for_diligence": [],
        "_raw": raw,
    }
