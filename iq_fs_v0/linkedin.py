"""LinkedIn profile lookup and scraping for Founder-Scorer-IQ prototype.

Two entry points:
- `find_linkedin_url`: best-guess a LinkedIn profile URL from a founder name
  (plus optional company / deck context) via Apify Google Search.
- `scrape_linkedin_profile`: pull a full structured profile from a URL via
  whichever provider is configured (`LINKEDIN_PROVIDER=linkdapi` or `apify`).
"""

from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urlparse

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

_APIFY_KEY = os.getenv("APIFY_API_KEY")
_LINKDAPI_KEY = os.getenv("LINKDAPI_API_KEY")
_PROVIDER = (os.getenv("LINKEDIN_PROVIDER") or "linkdapi").strip().lower()

_GOOGLE_SEARCH_ACTOR = os.getenv(
    "APIFY_GOOGLE_ACTOR",
    "apify/google-search-scraper",
)
_LINKEDIN_PROFILE_ACTOR = os.getenv(
    "APIFY_LINKEDIN_ACTOR",
    "dataweave/linkedin-profile-scraper",
)
_LINKEDIN_INPUT_KEY = os.getenv("APIFY_LINKEDIN_INPUT_KEY", "urls")

_LINKEDIN_PROFILE_RE = re.compile(r"linkedin\.com/in/[^/?#\s]+", re.IGNORECASE)


def provider_name() -> str:
    """Which LinkedIn provider is currently configured (for UI display)."""
    return _PROVIDER


def _client() -> ApifyClient:
    if not _APIFY_KEY:
        raise RuntimeError(
            "APIFY_API_KEY is missing. Add it to .env before running."
        )
    return ApifyClient(_APIFY_KEY)


def _normalize_linkedin_url(url: str) -> str:
    """Strip tracking params and normalize to https://www.linkedin.com/in/<slug>/."""
    url = url.strip()
    if not url:
        return url
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")

    parsed = urlparse(url)
    match = _LINKEDIN_PROFILE_RE.search(parsed.netloc + parsed.path)
    if not match:
        return url
    slug_path = match.group(0)
    slug = slug_path.split("/in/", 1)[-1].rstrip("/")
    return f"https://www.linkedin.com/in/{slug}/"


def find_linkedin_url(
    founder_name: str,
    company_name: Optional[str] = None,
    extra_context: Optional[str] = None,
) -> dict:
    """Best-effort lookup of a founder's LinkedIn profile URL.

    Returns a dict with:
      - url: matched profile URL (or empty string if nothing found)
      - title, snippet: details from the search result for analyst confirmation
      - match_confidence: "high" | "medium" | "low"
      - candidates: up to 5 alternate profile URLs in case the top pick is wrong
      - query: exact query string used
    """
    founder_name = (founder_name or "").strip()
    if not founder_name:
        return {
            "url": "",
            "title": "",
            "snippet": "",
            "match_confidence": "low",
            "candidates": [],
            "query": "",
        }

    parts = [f'"{founder_name}"']
    if company_name:
        parts.append(f'"{company_name.strip()}"')
    if extra_context:
        parts.append(extra_context.strip())
    parts.append("site:linkedin.com/in")
    query = " ".join(parts)

    run_input = {
        "queries": query,
        "maxPagesPerQuery": 1,
        "resultsPerPage": 10,
        "countryCode": "in",
        "languageCode": "en",
    }

    run = _client().actor(_GOOGLE_SEARCH_ACTOR).call(run_input=run_input)
    items = list(_client().dataset(run["defaultDatasetId"]).iterate_items())

    organic: list[dict] = []
    for item in items:
        organic.extend(item.get("organicResults") or [])

    seen: set[str] = set()
    profile_hits: list[dict] = []
    for result in organic:
        url = result.get("url") or ""
        if "linkedin.com/in/" not in url.lower():
            continue
        normalized = _normalize_linkedin_url(url)
        if normalized in seen:
            continue
        seen.add(normalized)
        profile_hits.append(
            {
                "url": normalized,
                "title": result.get("title") or "",
                "snippet": result.get("description") or "",
            }
        )

    if not profile_hits:
        return {
            "url": "",
            "title": "",
            "snippet": "",
            "match_confidence": "low",
            "candidates": [],
            "query": query,
        }

    top = profile_hits[0]
    confidence = _score_match_confidence(
        founder_name=founder_name,
        company_name=company_name,
        hit=top,
    )

    return {
        "url": top["url"],
        "title": top["title"],
        "snippet": top["snippet"],
        "match_confidence": confidence,
        "candidates": [h["url"] for h in profile_hits[1:6]],
        "query": query,
    }


def _score_match_confidence(
    founder_name: str,
    company_name: Optional[str],
    hit: dict,
) -> str:
    """Heuristic confidence based on name/company presence in title + snippet."""
    haystack = f"{hit.get('title', '')} {hit.get('snippet', '')}".lower()
    name_parts = [p for p in founder_name.lower().split() if len(p) > 2]
    name_hits = sum(1 for p in name_parts if p in haystack)

    name_ok = name_hits >= max(1, len(name_parts) - 1)
    company_ok = (
        bool(company_name)
        and company_name.strip().lower() in haystack
    )

    if name_ok and company_ok:
        return "high"
    if name_ok or company_ok:
        return "medium"
    return "low"


def _extract_username(url: str) -> str:
    """Return the LinkedIn slug (the `<slug>` in `/in/<slug>/`)."""
    parsed = urlparse(url)
    match = _LINKEDIN_PROFILE_RE.search(parsed.netloc + parsed.path)
    if not match:
        return ""
    return match.group(0).split("/in/", 1)[-1].rstrip("/")


def scrape_linkedin_profile(linkedin_url: str) -> dict:
    """Scrape a LinkedIn profile and return raw profile data.

    Dispatches to whichever provider `LINKEDIN_PROVIDER` is set to:
    `linkdapi` (default) or `apify`. On any failure returns a dict with a
    `_scrape_error` key so the UI can surface the problem instead of silently
    treating it as an empty profile.
    """
    if not linkedin_url:
        return {"_scrape_error": "no linkedin url provided"}

    url = _normalize_linkedin_url(linkedin_url)

    if _PROVIDER == "linkdapi":
        return _scrape_via_linkdapi(url)
    if _PROVIDER == "apify":
        return _scrape_via_apify(url)
    return {"_scrape_error": f"unknown LINKEDIN_PROVIDER '{_PROVIDER}'"}


_LINKDAPI_FULL_URL = "https://linkdapi.com/api/v1/profile/full"


def _scrape_via_linkdapi(url: str) -> dict:
    """Scrape via LinkdAPI's `get_full_profile` endpoint (direct HTTP).

    We call the documented endpoint with httpx instead of the official SDK so
    we don't pin the project to Python >= 3.10.
    """
    if not _LINKDAPI_KEY:
        return {
            "_scrape_error": "LINKDAPI_API_KEY is missing from .env",
            "_scrape_url": url,
            "_provider": "linkdapi",
        }

    username = _extract_username(url)
    if not username:
        return {
            "_scrape_error": f"could not extract username from url '{url}'",
            "_scrape_url": url,
            "_provider": "linkdapi",
        }

    try:
        import httpx
    except ImportError:
        return {
            "_scrape_error": "httpx not installed (run `pip install -r requirements.txt`)",
            "_scrape_url": url,
            "_provider": "linkdapi",
        }

    try:
        resp = httpx.get(
            _LINKDAPI_FULL_URL,
            params={"username": username},
            headers={"X-linkdapi-apikey": _LINKDAPI_KEY},
            timeout=60.0,
        )
    except Exception as exc:
        return {
            "_scrape_error": f"linkdapi request failed: {exc}",
            "_scrape_url": url,
            "_provider": "linkdapi",
        }

    if resp.status_code != 200:
        body_preview = resp.text[:500] if resp.text else ""
        return {
            "_scrape_error": f"linkdapi HTTP {resp.status_code}: {body_preview}",
            "_scrape_url": url,
            "_provider": "linkdapi",
            "_status_code": resp.status_code,
        }

    try:
        response = resp.json()
    except Exception as exc:
        return {
            "_scrape_error": f"linkdapi returned non-JSON: {exc}",
            "_scrape_url": url,
            "_provider": "linkdapi",
        }

    if not isinstance(response, dict):
        return {
            "_scrape_error": f"unexpected linkdapi response type {type(response).__name__}",
            "_scrape_url": url,
            "_provider": "linkdapi",
            "_raw_response": str(response)[:1000],
        }

    if response.get("success") is False:
        return {
            "_scrape_error": (
                response.get("message") or "linkdapi reported success=false"
            ),
            "_scrape_url": url,
            "_provider": "linkdapi",
            "_status_code": response.get("statusCode"),
            "_raw_response": response,
        }

    data = response.get("data")
    if not isinstance(data, dict) or not data:
        return {
            "_scrape_error": "linkdapi returned no profile data",
            "_scrape_url": url,
            "_provider": "linkdapi",
            "_raw_response": response,
        }

    data["_provider"] = "linkdapi"
    data["_scrape_url"] = url
    data["_username"] = username
    return data


def _scrape_via_apify(url: str) -> dict:
    """Scrape via an Apify LinkedIn actor, as configured by env vars."""
    run_input = {_LINKEDIN_INPUT_KEY: [url]}

    try:
        run = _client().actor(_LINKEDIN_PROFILE_ACTOR).call(run_input=run_input)
    except Exception as exc:
        return {
            "_scrape_error": f"actor call failed: {exc}",
            "_scrape_url": url,
            "_provider": "apify",
        }

    status = run.get("status")
    dataset_id = run.get("defaultDatasetId")
    run_id = run.get("id")

    items: list[dict] = []
    if dataset_id:
        try:
            items = list(_client().dataset(dataset_id).iterate_items())
        except Exception as exc:
            return {
                "_scrape_error": f"dataset read failed: {exc}",
                "_scrape_url": url,
                "_run_id": run_id,
                "_run_status": status,
                "_provider": "apify",
            }

    if items:
        first = items[0]
        if isinstance(first, dict):
            actor_error = None
            if first.get("succeeded") is False:
                actor_error = first.get("error") or "actor reported succeeded=false"
            elif first.get("error") and not _looks_like_profile(first):
                actor_error = str(first.get("error"))
            elif not _looks_like_profile(first):
                actor_error = "actor returned item with no profile fields"

            if actor_error:
                return {
                    "_scrape_error": actor_error,
                    "_scrape_url": url,
                    "_run_id": run_id,
                    "_run_status": status,
                    "_raw_item": first,
                    "_provider": "apify",
                }

            first.setdefault("_run_id", run_id)
            first.setdefault("_run_status", status)
            first.setdefault("_scrape_url", url)
            first.setdefault("_provider", "apify")
            return first

    return {
        "_scrape_error": "actor returned zero items",
        "_scrape_url": url,
        "_provider": "apify",
        "_run_id": run_id,
        "_run_status": status,
    }


def _looks_like_profile(item: dict) -> bool:
    """Heuristic: does this dataset item actually contain LinkedIn profile data?"""
    profile_fields = (
        "fullName",
        "name",
        "firstName",
        "headline",
        "experiences",
        "experience",
        "educations",
        "education",
        "about",
        "summary",
        "publicIdentifier",
        "linkedinUrl",
    )
    return any(item.get(f) for f in profile_fields)


_NOISE_KEYS = {
    "profilePicture", "backgroundImage", "img_400_400", "img_200_200",
    "photo", "avatar", "pictureUrl", "profilePictureUrl", "backgroundCoverImage",
    "publicProfileUrl", "memberUrn", "entityUrn", "dashEntityUrn", "objectUrn",
    "trackingId", "versionTag", "paging", "metadata", "$anti_abuse_metadata",
}

_SKIP_URL_PREFIXES = ("https://media.licdn", "https://static.licdn", "data:image")


def _clean_value(val):
    """Recursively strip noise from a scraped profile value."""
    if isinstance(val, dict):
        return {
            k: _clean_value(v)
            for k, v in val.items()
            if k not in _NOISE_KEYS and v not in (None, "", [], {})
        }
    if isinstance(val, list):
        cleaned = [_clean_value(i) for i in val]
        return [i for i in cleaned if i not in (None, "", [], {})]
    if isinstance(val, str):
        if any(val.startswith(p) for p in _SKIP_URL_PREFIXES):
            return None
        return val
    return val


def _fmt_date(d) -> str:
    if not isinstance(d, dict):
        return ""
    import calendar
    y, m = d.get("year"), d.get("month")
    if y and m:
        return f"{calendar.month_abbr[m]} {y}"
    return str(y) if y else ""


def _exp_sort_key(exp: dict) -> tuple:
    tp = exp.get("timePeriod") or {}
    sd = tp.get("startDate") or exp.get("startDate") or {}
    return (sd.get("year") or 0, sd.get("month") or 0)


def summarize_profile_for_prompt(profile: dict, max_chars: int = 10000) -> str:
    """Convert a raw scraped profile into high-fidelity text for the LLM.

    Strategy: strip all noise (images, URLs, tracking IDs) then render every
    meaningful field so Claude gets the full picture — especially experience
    titles, dates, descriptions, education, recommendations, and activity.
    """
    if not profile:
        return "(no profile data available)"
    if profile.get("_scrape_error"):
        return f"(profile scrape failed: {profile['_scrape_error']})"

    lines: list[str] = []

    # ── Identity ──────────────────────────────────────────────────────────────
    name = (
        profile.get("fullName") or profile.get("name")
        or f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
    )
    if name:   lines.append(f"Name: {name}")
    if profile.get("headline"):  lines.append(f"Headline: {profile['headline']}")
    loc = profile.get("addressWithCountry") or profile.get("location") or profile.get("geoLocationName")
    if loc:    lines.append(f"Location: {loc}")
    about = profile.get("about") or profile.get("summary")
    if about:  lines.append(f"\nAbout:\n{str(about)[:2000]}")

    followers   = profile.get("followers") or profile.get("followerCount")
    connections = profile.get("connections") or profile.get("connectionsCount")
    if followers:   lines.append(f"Followers: {followers}")
    if connections: lines.append(f"Connections: {connections}")

    # ── Experience ────────────────────────────────────────────────────────────
    exps = profile.get("experiences") or profile.get("experience") or []
    if exps:
        try:
            exps = sorted(exps, key=_exp_sort_key, reverse=True)
        except Exception:
            pass
        lines.append("\nExperience:")
        for exp in exps:
            title   = exp.get("title") or exp.get("position") or ""
            company = exp.get("companyName") or exp.get("company") or ""
            tp      = exp.get("timePeriod") or {}
            start   = _fmt_date(tp.get("startDate") or exp.get("startDate"))
            end     = _fmt_date(tp.get("endDate")   or exp.get("endDate")) or "Present"
            dur     = exp.get("duration") or exp.get("dateRange") or ""
            size    = exp.get("companyStaffCountRange") or exp.get("employeeCount") or ""
            loc_exp = exp.get("locationName") or exp.get("location") or ""

            date_str = f"{start} – {end}" if start else end
            if dur: date_str += f" ({dur})"

            line = f"  [{date_str}]  {title}  @  {company}"
            if size:    line += f"  |  size: {size}"
            if loc_exp: line += f"  |  {loc_exp}"
            lines.append(line)

            desc = (exp.get("description") or "")[:600]
            if desc:
                lines.append(f"    {desc.strip()}")

    # ── Education ─────────────────────────────────────────────────────────────
    edus = profile.get("educations") or profile.get("education") or []
    if edus:
        lines.append("\nEducation:")
        for edu in edus:
            school = edu.get("schoolName") or edu.get("school") or ""
            degree = edu.get("degree") or edu.get("degreeName") or ""
            field  = edu.get("fieldOfStudy") or ""
            tp     = edu.get("timePeriod") or {}
            start  = _fmt_date(tp.get("startDate") or edu.get("startDate"))
            end    = _fmt_date(tp.get("endDate")   or edu.get("endDate"))
            dates  = f"{start}–{end}" if start and end else edu.get("dateRange") or edu.get("duration") or ""
            detail = ", ".join(p for p in [degree, field] if p)
            line   = f"  {school}"
            if detail: line += f" — {detail}"
            if dates:  line += f" ({dates})"
            lines.append(line)
            activities = edu.get("activities") or edu.get("description") or ""
            if activities:
                lines.append(f"    Activities: {str(activities)[:300]}")

    # ── Certifications ────────────────────────────────────────────────────────
    certs = profile.get("certifications") or profile.get("licenseAndCertificates") or []
    if certs:
        lines.append("\nCertifications:")
        for c in certs[:8]:
            name_c  = c.get("name") or c.get("title") or ""
            issuer  = c.get("authority") or c.get("issuer") or ""
            lines.append(f"  {name_c}" + (f" — {issuer}" if issuer else ""))

    # ── Honors & Awards ───────────────────────────────────────────────────────
    honors = profile.get("honors") or profile.get("honorsAndAwards") or []
    if honors:
        lines.append("\nHonors / Awards:")
        for h in honors[:8]:
            t = h.get("title") or h.get("name") or ""
            i = h.get("issuer") or ""
            lines.append(f"  {t}" + (f" — {i}" if i else ""))

    # ── Publications / Patents ────────────────────────────────────────────────
    pubs = profile.get("publications") or []
    if pubs:
        lines.append("\nPublications:")
        for p in pubs[:5]:
            lines.append(f"  {p.get('name') or p.get('title') or ''}")

    patents = profile.get("patents") or []
    if patents:
        lines.append("\nPatents:")
        for p in patents[:5]:
            lines.append(f"  {p.get('title') or p.get('name') or ''}")

    # ── Volunteer / Causes ────────────────────────────────────────────────────
    vol = profile.get("volunteer") or profile.get("volunteerExperiences") or []
    if vol:
        lines.append("\nVolunteer:")
        for v in vol[:4]:
            role = v.get("role") or v.get("title") or ""
            org  = v.get("companyName") or v.get("organization") or ""
            lines.append(f"  {role} @ {org}".strip(" @"))

    # ── Skills ────────────────────────────────────────────────────────────────
    skills = profile.get("skills") or []
    if skills:
        skill_names = []
        for s in skills[:20]:
            n = s.get("name") if isinstance(s, dict) else str(s)
            if n: skill_names.append(n)
        if skill_names:
            lines.append(f"\nSkills: {', '.join(skill_names)}")

    # ── Recommendations ───────────────────────────────────────────────────────
    recs = profile.get("recommendations") or profile.get("receivedRecommendations") or []
    if recs:
        lines.append("\nRecommendations received:")
        for r in recs[:4]:
            rec_text  = r.get("caption") or r.get("description") or r.get("text") or ""
            rec_from  = r.get("authorFullName") or r.get("recommenderName") or r.get("name") or ""
            rec_title = r.get("authorTitle") or r.get("recommenderTitle") or ""
            if rec_text:
                lines.append(f"  From {rec_from}" + (f" ({rec_title})" if rec_title else "") + ":")
                lines.append(f"    \"{str(rec_text)[:400]}\"")

    # ── Languages ─────────────────────────────────────────────────────────────
    langs = profile.get("languages") or []
    if langs:
        lang_names = [l.get("name") if isinstance(l, dict) else str(l) for l in langs]
        lines.append(f"\nLanguages: {', '.join(l for l in lang_names if l)}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (truncated)"
    return text
