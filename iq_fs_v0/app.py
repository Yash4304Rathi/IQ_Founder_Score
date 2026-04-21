"""Founder-Scorer-IQ — LinkedIn-only prototype (iq_fs_v0)."""

from __future__ import annotations

import streamlit as st

from deck import extract_text as extract_deck_text, short_context_hint
from history import delete_entry, load_history, save_run
from linkedin import (
    find_linkedin_url,
    provider_name,
    scrape_linkedin_profile,
    summarize_profile_for_prompt,
)
from scorer import score_founder

st.set_page_config(
    page_title="IQ Founder Score",
    page_icon="◈",
    layout="wide",
)

# ── Design tokens ──────────────────────────────────────────────────────────────
ACCENT       = "#D4720A"
ACCENT_LIGHT = "#FEF3E8"
ACCENT_MID   = "#F59E42"
TEXT         = "#111111"
TEXT_MUTED   = "#717171"
TEXT_LIGHT   = "#AAAAAA"
BG           = "#FFFFFF"
SURFACE      = "#F7F6F4"
BORDER       = "#E5E3DF"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: {TEXT};
    -webkit-font-smoothing: antialiased;
}}
.main .block-container {{
    padding: 2.5rem 3rem 5rem;
    max-width: 1180px;
}}
.stApp {{ background-color: {BG}; }}

/* ── Top header bar (force white) ── */
header[data-testid="stHeader"] {{
    background-color: {BG} !important;
    border-bottom: 1px solid {BORDER} !important;
}}
header[data-testid="stHeader"] * {{
    color: {TEXT} !important;
}}
header[data-testid="stHeader"] button {{
    color: {TEXT} !important;
    background: transparent !important;
    border-color: {BORDER} !important;
}}
/* Deploy button text */
.stDeployButton span, .stDeployButton p {{
    color: {TEXT} !important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {SURFACE};
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] > div {{
    padding: 1.75rem 1.25rem;
}}

/* ── Headings ── */
h1 {{
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    color: {TEXT} !important;
    line-height: 1.2 !important;
    margin-bottom: 0.15rem !important;
}}
h2 {{
    font-size: 0.65rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: {TEXT_MUTED} !important;
    margin-top: 2.5rem !important;
    margin-bottom: 0.75rem !important;
}}
h3 {{
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: {TEXT} !important;
    letter-spacing: -0.01em !important;
}}
p, .stMarkdown p {{
    font-size: 0.88rem !important;
    line-height: 1.65 !important;
    color: {TEXT} !important;
}}
.stCaption, small {{
    color: {TEXT_MUTED} !important;
    font-size: 0.76rem !important;
    line-height: 1.5 !important;
}}

/* ── Divider ── */
hr {{
    border: none !important;
    border-top: 1px solid {BORDER} !important;
    margin: 2rem 0 !important;
}}

/* ── Form submit button ── */
.stFormSubmitButton > button {{
    background-color: {ACCENT} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 3px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.65rem 1.75rem !important;
    transition: opacity 0.15s ease !important;
    box-shadow: none !important;
}}
.stFormSubmitButton > button:hover {{ opacity: 0.85 !important; }}

/* ── Secondary button ── */
.stButton > button {{
    background-color: transparent !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 3px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.1rem !important;
    transition: border-color 0.15s ease, color 0.15s ease !important;
    box-shadow: none !important;
}}
.stButton > button:hover {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
}}
.stButton > button[kind="primary"] {{
    background-color: {ACCENT} !important;
    color: #FFFFFF !important;
    border: none !important;
}}
.stButton > button[kind="primary"]:hover {{ opacity: 0.85 !important; }}

/* ── Inputs ── */
.stTextInput > div > div > input {{
    border: 1px solid {BORDER} !important;
    border-radius: 3px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 0.7rem !important;
    background-color: {BG} !important;
    color: {TEXT} !important;
    box-shadow: none !important;
    caret-color: {ACCENT} !important;
}}
.stTextInput > div > div > input:focus,
.stTextInput > div > div > input:active {{
    border-color: {ACCENT} !important;
    background-color: {BG} !important;
    color: {TEXT} !important;
    box-shadow: 0 0 0 3px {ACCENT_LIGHT} !important;
    outline: none !important;
}}
/* Kill the dark navy focus overlay Streamlit injects */
.stTextInput > div[data-focused="true"] > div,
.stTextInput > div > div:focus-within {{
    background-color: {BG} !important;
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px {ACCENT_LIGHT} !important;
}}
.stTextInput label, .stFileUploader label {{
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: {TEXT_MUTED} !important;
}}
/* ── File uploader — force light ── */
[data-testid="stFileUploader"] {{
    background-color: {BG} !important;
    border-radius: 3px !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    background-color: {SURFACE} !important;
    border: 1px dashed {BORDER} !important;
    border-radius: 3px !important;
    color: {TEXT} !important;
}}
[data-testid="stFileUploaderDropzone"] * {{
    color: {TEXT} !important;
    fill: {TEXT_MUTED} !important;
}}
[data-testid="stFileUploaderDropzone"] button {{
    background-color: {BG} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 3px !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}}
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span {{
    color: {TEXT_MUTED} !important;
    font-size: 0.75rem !important;
}}

/* ── Metrics ── */
[data-testid="metric-container"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 4px !important;
    padding: 1rem 1.1rem 0.9rem !important;
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.62rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.11em !important;
    text-transform: uppercase !important;
    color: {TEXT_MUTED} !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    color: {TEXT} !important;
    letter-spacing: -0.025em !important;
    line-height: 1.1 !important;
}}

/* ── Expander ── */
.streamlit-expanderHeader {{
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: {TEXT_MUTED} !important;
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 3px !important;
    padding: 0.55rem 0.9rem !important;
}}
.streamlit-expanderContent {{
    border: 1px solid {BORDER} !important;
    border-top: none !important;
    border-radius: 0 0 3px 3px !important;
    padding: 0.75rem !important;
}}

/* ── Alert boxes ── */
.stAlert {{
    border-radius: 3px !important;
    font-size: 0.84rem !important;
    line-height: 1.55 !important;
}}

/* ── Status widget (processing bar) — force light ── */
[data-testid="stStatusWidget"],
div[data-testid="stStatusWidget"],
.stStatus, [class*="StatusWidget"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 4px !important;
    color: {TEXT} !important;
    font-size: 0.84rem !important;
}}
[data-testid="stStatusWidget"] *,
.stStatus *, [class*="StatusWidget"] * {{
    color: {TEXT} !important;
    background-color: transparent !important;
}}
/* The collapsible header row of the status widget */
[data-testid="stStatusWidget"] > div:first-child {{
    background-color: {SURFACE} !important;
    border-radius: 4px !important;
    padding: 0.6rem 0.9rem !important;
}}
/* Spinner/icon color */
[data-testid="stStatusWidget"] svg {{
    stroke: {ACCENT} !important;
    fill: none !important;
}}
/* "complete" state - green check is OK, just fix background */
[data-testid="stStatusWidget"][data-state="complete"],
[data-testid="stStatusWidget"][data-state="error"] {{
    background-color: {SURFACE} !important;
}}

/* ── Hide "Press Enter to submit form" hint ── */
.stTextInput [data-testid="InputInstructions"],
small[data-testid="InputInstructions"] {{
    display: none !important;
}}

/* ── Form wrapper card ── */
[data-testid="stForm"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 5px !important;
    padding: 1.5rem !important;
}}

/* ── Sidebar delete buttons — compact ── */
[data-testid="stSidebar"] .stButton > button {{
    padding: 0.25rem 0.6rem !important;
    font-size: 0.65rem !important;
    margin-top: 0.35rem !important;
    color: {TEXT_MUTED} !important;
    border-color: {BORDER} !important;
    width: 100% !important;
}}

/* ── Score badge ── */
.iq-score-badge {{
    display: inline-flex;
    flex-direction: column;
    align-items: flex-start;
    background-color: {ACCENT};
    color: white;
    padding: 0.85rem 1.4rem;
    border-radius: 4px;
    min-width: 120px;
}}
.iq-score-num {{
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1;
}}
.iq-score-denom {{
    font-size: 0.75rem;
    font-weight: 500;
    opacity: 0.75;
    letter-spacing: 0.03em;
    margin-top: 0.1rem;
}}

/* ── Pill / badge ── */
.iq-pill {{
    display: inline-block;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    padding: 0.22rem 0.65rem;
    border-radius: 20px;
}}
.iq-pill-orange {{
    background: {ACCENT_LIGHT};
    color: {ACCENT};
    border: 1px solid #E8A66533;
}}
.iq-pill-green {{
    background: #EDFAF2;
    color: #166534;
    border: 1px solid #16653433;
}}
.iq-pill-yellow {{
    background: #FEFCE8;
    color: #854D0E;
    border: 1px solid #854D0E33;
}}
.iq-pill-red {{
    background: #FFF1F1;
    color: #991B1B;
    border: 1px solid #991B1B33;
}}
.iq-pill-blue {{
    background: #EFF6FF;
    color: #1E40AF;
    border: 1px solid #1E40AF33;
}}
.iq-pill-gray {{
    background: {SURFACE};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
}}

/* ── Section label ── */
.iq-section-label {{
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {TEXT_MUTED};
    padding-bottom: 0.55rem;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 0.9rem;
}}

/* ── List items ── */
.iq-list-item {{
    font-size: 0.86rem;
    line-height: 1.6;
    color: {TEXT};
    padding: 0.45rem 0;
    border-bottom: 1px solid {BORDER};
    display: flex;
    gap: 0.6rem;
    align-items: flex-start;
}}
.iq-list-item:last-child {{ border-bottom: none; }}
.iq-list-dot {{
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background-color: {ACCENT};
    flex-shrink: 0;
    margin-top: 0.5rem;
}}
.iq-list-num {{
    font-size: 0.7rem;
    font-weight: 700;
    color: {ACCENT};
    flex-shrink: 0;
    width: 1.2rem;
    padding-top: 0.1rem;
}}

/* ── Card container ── */
.iq-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.6rem;
}}

/* ── Wordmark ── */
.iq-wordmark {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
}}
.iq-wordmark-badge {{
    background: {ACCENT};
    color: white;
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    padding: 0.18rem 0.5rem;
    border-radius: 2px;
    text-transform: uppercase;
}}
.iq-wordmark-title {{
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {TEXT_MUTED};
}}

/* ── Confidence URL row ── */
.iq-url-row {{
    font-size: 0.82rem;
    color: {TEXT_MUTED};
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.25rem;
}}
.iq-url-row a {{
    color: {ACCENT} !important;
    text-decoration: none !important;
    font-weight: 500;
}}
.iq-url-row a:hover {{ text-decoration: underline !important; }}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
GRADE_COLORS = {
    "Strong Yes": "iq-pill-green",
    "Lean Yes":   "iq-pill-green",
    "Maybe":      "iq-pill-yellow",
    "Lean No":    "iq-pill-red",
    "Strong No":  "iq-pill-red",
}
GRADE_MARKERS = {
    "Strong Yes": "++",
    "Lean Yes":   "+",
    "Maybe":      "~",
    "Lean No":    "−",
    "Strong No":  "−−",
}
CONFIDENCE_PILL = {
    "high":    ("iq-pill-green",  "High confidence"),
    "medium":  ("iq-pill-yellow", "Medium confidence — verify"),
    "low":     ("iq-pill-red",    "Low confidence — verify"),
    "analyst": ("iq-pill-blue",   "Analyst-provided URL"),
}


def _pill(label: str, css_class: str = "iq-pill-orange") -> str:
    return f'<span class="iq-pill {css_class}">{label}</span>'


def _section(label: str) -> None:
    st.markdown(f'<div class="iq-section-label">{label}</div>', unsafe_allow_html=True)


def _reset_run_state() -> None:
    for key in ("last_run", "override_url", "profile", "match"):
        st.session_state.pop(key, None)


def _run_pipeline(
    founder_name: str,
    company_name: str,
    linkedin_url: str,
    deck_text: str,
    url_source: str,
    match_meta: dict | None = None,
) -> dict:
    profile = scrape_linkedin_profile(linkedin_url) if linkedin_url else {}
    profile_text = summarize_profile_for_prompt(profile)
    has_profile_data = bool(profile) and not profile.get("_scrape_error")
    result = (
        score_founder(
            founder_name=founder_name,
            company_name=company_name,
            linkedin_url=linkedin_url,
            profile_text=profile_text,
            deck_text=deck_text or None,
        )
        if has_profile_data
        else None
    )
    return {
        "founder_name": founder_name,
        "company_name": company_name,
        "linkedin_url": linkedin_url,
        "url_source": url_source,
        "match": match_meta or {
            "match_confidence": "analyst" if url_source == "analyst" else "low",
            "title": "", "snippet": "", "candidates": [], "query": "",
        },
        "profile": profile,
        "profile_text": profile_text,
        "deck_text": deck_text,
        "result": result,
    }


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="iq-section-label" style="margin-top:0">Run History</div>',
        unsafe_allow_html=True,
    )
    history = load_history()
    if not history:
        st.caption("No runs yet.")
    else:
        for entry in reversed(history[-20:]):
            grade   = entry.get("grade", "")
            result  = entry.get("result") or {}
            failed  = not result
            score   = entry.get("overall_linkedin_fit", "—")
            name    = entry.get("founder_name", "Unknown")
            company = entry.get("company_name", "")
            ts      = entry.get("timestamp", "")[:10]
            url     = entry.get("linkedin_url", "")
            grade_cls = GRADE_COLORS.get(grade, "iq-pill-gray")

            score_display = (
                f'<span style="color:#991B1B;font-weight:700">Failed</span>'
                if failed
                else f'<span style="font-size:1.1rem;font-weight:700;letter-spacing:-0.02em">{score}</span>'
                     f'<span style="font-size:0.7rem;color:{TEXT_MUTED}">/100</span>'
            )
            grade_badge = (
                "" if failed
                else f'<span class="iq-pill {grade_cls}" style="font-size:0.58rem">{grade}</span>'
            )
            company_line = f'<div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:0.1rem">{company}</div>' if company else ""
            url_line = (
                f'<div style="font-size:0.72rem;margin-top:0.25rem">'
                f'<a href="{url}" target="_blank" style="color:{ACCENT};text-decoration:none">LinkedIn ↗</a>'
                f'</div>'
                if url else ""
            )

            st.markdown(
                f"""
                <div style="
                    background:{BG};
                    border:1px solid {BORDER};
                    border-radius:4px;
                    padding:0.7rem 0.8rem;
                    margin-bottom:0.5rem;
                ">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem">
                        <div style="font-size:0.85rem;font-weight:600;color:{TEXT};line-height:1.2">{name}</div>
                        <div style="text-align:right;flex-shrink:0">{score_display}</div>
                    </div>
                    {company_line}
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.4rem">
                        {grade_badge}
                        <span style="font-size:0.68rem;color:{TEXT_LIGHT}">{ts}</span>
                    </div>
                    {url_line}
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Delete", key=f"del_{entry['id']}"):
                delete_entry(entry["id"])
                st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="iq-wordmark">
        <span class="iq-wordmark-badge">IQ</span>
        <span class="iq-wordmark-title">India Quotient · Internal Tool</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("Founder Score")
st.caption(
    "LinkedIn-only founder assessment. Enter a founder name — optionally add "
    "company, pitch deck, or a known LinkedIn URL."
)

st.divider()

# ── Input form ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="iq-section-label">New Analysis</div>',
    unsafe_allow_html=True,
)
with st.form("founder_form"):
    col1, col2 = st.columns(2, gap="large")
    with col1:
        founder_name = st.text_input(
            "Founder name *",
            placeholder="e.g. Nikhil Kamath",
        )
        company_name = st.text_input(
            "Company name",
            placeholder="e.g. Zerodha",
        )
    with col2:
        linkedin_url_in = st.text_input(
            "LinkedIn URL",
            placeholder="https://linkedin.com/in/…",
            help="If you know the exact profile, paste it here. Otherwise we find it automatically.",
        )
        deck_file = st.file_uploader(
            "Pitch deck PDF",
            type=["pdf"],
            help="Optional — used only as extra context for summary and matching.",
        )
    submitted = st.form_submit_button(
        "Analyze Founder", type="primary", use_container_width=True
    )

# ── Pipeline trigger ──────────────────────────────────────────────────────────
if submitted:
    if not founder_name.strip():
        st.error("Founder name is required.")
    else:
        _reset_run_state()
        deck_text = ""
        if deck_file is not None:
            with st.status("Reading pitch deck…", expanded=False):
                deck_text = extract_deck_text(deck_file.getvalue())
                if not deck_text:
                    st.warning("Could not extract text from the PDF.")

        with st.status("Resolving LinkedIn profile…", expanded=True) as status:
            chosen_url = linkedin_url_in.strip()
            if chosen_url:
                match_meta  = {"match_confidence": "analyst", "title": "", "snippet": "", "candidates": [], "query": ""}
                url_source  = "analyst"
                st.write("Using analyst-provided URL.")
            else:
                st.write("Searching LinkedIn via Google…")
                match      = find_linkedin_url(
                    founder_name=founder_name.strip(),
                    company_name=(company_name.strip() or None),
                    extra_context=short_context_hint(deck_text),
                )
                chosen_url = match["url"]
                match_meta = match
                url_source = "auto"
                if not chosen_url:
                    status.update(label="No LinkedIn profile found", state="error")

            if chosen_url:
                st.write(f"Scraping profile: {chosen_url}")
                run = _run_pipeline(
                    founder_name=founder_name.strip(),
                    company_name=company_name.strip(),
                    linkedin_url=chosen_url,
                    deck_text=deck_text,
                    url_source=url_source,
                    match_meta=match_meta,
                )
                scrape_error = run["profile"].get("_scrape_error")
                if scrape_error:
                    st.error(f"LinkedIn scrape failed: {scrape_error}")
                    status.update(label="Scrape failed", state="error")
                else:
                    st.write("Scoring with Claude…")
                    status.update(label="Analysis complete", state="complete")

                st.session_state["last_run"] = run
                save_run(
                    founder_name=run["founder_name"],
                    company_name=run["company_name"],
                    linkedin_url=run["linkedin_url"],
                    match_confidence=run["match"].get("match_confidence", ""),
                    url_source=run["url_source"],
                    result=run["result"] or {},
                    profile=run["profile"],
                )

        if not st.session_state.get("last_run"):
            st.warning(
                "Couldn't auto-find a LinkedIn profile. "
                "Paste the URL directly in the form and try again."
            )


def _render_edit_url_panel(run: dict) -> None:
    match_meta = run["match"]
    with st.expander(
        "Not the right profile? Edit URL and re-analyze.",
        expanded=not run["result"],
    ):
        new_url    = st.text_input("Corrected LinkedIn URL", value=run["linkedin_url"], key="override_url")
        candidates = match_meta.get("candidates") or []
        if candidates:
            st.caption("Other candidates:")
            for c in candidates:
                st.markdown(
                    f'<div class="iq-url-row">→ <a href="{c}" target="_blank">{c}</a></div>',
                    unsafe_allow_html=True,
                )
        if st.button("Re-analyze with this URL", type="secondary"):
            with st.status("Re-analyzing…", expanded=True) as status:
                st.write(f"Scraping profile: {new_url}")
                new_run = _run_pipeline(
                    founder_name=run["founder_name"],
                    company_name=run["company_name"],
                    linkedin_url=new_url.strip(),
                    deck_text=run.get("deck_text", ""),
                    url_source="analyst",
                    match_meta={"match_confidence": "analyst", "title": "", "snippet": "", "candidates": [], "query": ""},
                )
                scrape_err = new_run["profile"].get("_scrape_error")
                status.update(
                    label="Scrape failed" if scrape_err else "Re-analysis complete",
                    state="error" if scrape_err else "complete",
                )
            save_run(
                founder_name=new_run["founder_name"],
                company_name=new_run["company_name"],
                linkedin_url=new_run["linkedin_url"],
                match_confidence="analyst",
                url_source="analyst",
                result=new_run["result"] or {},
                profile=new_run["profile"],
            )
            st.session_state["last_run"] = new_run
            st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
run = st.session_state.get("last_run")
if run:
    result     = run["result"]
    match_meta = run["match"]
    confidence = match_meta.get("match_confidence", "low")
    pill_cls, pill_label = CONFIDENCE_PILL.get(confidence, ("iq-pill-gray", "Unknown"))

    st.divider()

    # Profile used row
    _section("LinkedIn Profile Used")
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap; margin-bottom:0.4rem;">
            {_pill(pill_label, pill_cls)}
            <div class="iq-url-row">
                <a href="{run['linkedin_url']}" target="_blank">{run['linkedin_url']}</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    prov = run["profile"].get("_provider") or provider_name()
    st.caption(f"Provider: {prov}  ·  Source: {run['url_source']}")
    if match_meta.get("title"):
        st.caption(match_meta["title"])

    scrape_error = run["profile"].get("_scrape_error")

    # ── Scrape failed ──────────────────────────────────────────────────────────
    if scrape_error:
        st.divider()
        _section("Scrape Error")
        st.error(
            "We found a likely profile but couldn't retrieve its data. "
            "No score has been generated."
        )
        c1, c2 = st.columns(2)
        with c1:
            st.caption("URL attempted")
            st.code(run["profile"].get("_scrape_url", run["linkedin_url"]))
            st.caption("Error")
            st.code(scrape_error, language="text")
        with c2:
            st.caption("Actor status")
            st.write(f"`{run['profile'].get('_run_status', 'unknown')}`")
            run_id = run["profile"].get("_run_id")
            if run_id:
                st.markdown(
                    f'<div class="iq-url-row"><a href="https://console.apify.com/actors/runs/{run_id}" '
                    f'target="_blank">Open in Apify ↗</a></div>',
                    unsafe_allow_html=True,
                )
        _render_edit_url_panel(run)
        with st.expander("Raw actor response"):
            st.json(run["profile"])

    else:
        # ── Success ────────────────────────────────────────────────────────────
        _render_edit_url_panel(run)
        st.divider()

        score      = result.get("overall_linkedin_fit", 0)
        grade      = result.get("grade", "—")
        grade_cls  = GRADE_COLORS.get(grade, "iq-pill-gray")
        conf_score = result.get("confidence_score", 0)
        summary    = result.get("summary", "")

        # Top row — score + grade + summary
        s_col, g_col, sum_col = st.columns([1, 1, 3], gap="large")

        with s_col:
            _section("LinkedIn Fit")
            st.markdown(
                f"""
                <div class="iq-score-badge">
                    <span class="iq-score-num">{score}</span>
                    <span class="iq-score-denom">out of 100</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with g_col:
            _section("Grade")
            st.markdown(
                f"""
                <div style="margin-bottom:0.5rem">{_pill(grade, grade_cls)}</div>
                <div style="font-size:0.76rem; color:{TEXT_MUTED};">
                    Confidence&nbsp;&nbsp;
                    <strong style="color:{TEXT};">{conf_score}/10</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with sum_col:
            _section("Summary")
            st.markdown(
                f'<p style="margin:0">{summary}</p>',
                unsafe_allow_html=True,
            )

        st.caption(
            "Score is based on LinkedIn data only. "
            "Treat as a screening signal — not an investment decision."
        )

        st.divider()

        # Scorecard dimensions
        _section("Scorecard")
        dims = {
            "Career Signal":      result.get("career_signal", {}),
            "Founder Relevance":  result.get("founder_relevance", {}),
            "Execution Signal":   result.get("execution_signal", {}),
            "Credibility Signal": result.get("credibility_signal", {}),
        }
        for col, (name, data) in zip(st.columns(4, gap="medium"), dims.items()):
            with col:
                st.metric(name, f"{data.get('score', 0)}/10")
                st.caption(data.get("reasoning", ""))

        st.divider()

        # Strengths + Concerns
        str_col, con_col = st.columns(2, gap="large")

        with str_col:
            _section("Strengths")
            items = result.get("strengths") or []
            if items:
                html = "".join(
                    f'<div class="iq-list-item"><span class="iq-list-dot"></span>{s}</div>'
                    for s in items
                )
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("None identified.")

        with con_col:
            _section("Concerns")
            items = result.get("concerns") or []
            if items:
                html = "".join(
                    f'<div class="iq-list-item"><span class="iq-list-dot" style="background:#991B1B"></span>{c}</div>'
                    for c in items
                )
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("None identified.")

        st.divider()

        # Missing info + Diligence questions
        mis_col, dil_col = st.columns(2, gap="large")

        with mis_col:
            _section("Missing Information")
            items = result.get("missing_information") or []
            if items:
                html = "".join(
                    f'<div class="iq-list-item"><span class="iq-list-dot" style="background:{TEXT_MUTED}"></span>{m}</div>'
                    for m in items
                )
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("Nothing flagged.")

        with dil_col:
            _section("Diligence Questions")
            items = result.get("next_questions_for_diligence") or []
            if items:
                html = "".join(
                    f'<div class="iq-list-item">'
                    f'<span class="iq-list-num">{i}.</span>{q}'
                    f'</div>'
                    for i, q in enumerate(items, 1)
                )
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.caption("No questions generated.")

        st.divider()

        # Debug expanders
        with st.expander("Raw LinkedIn data"):
            st.json(run["profile"])
        if run.get("deck_text"):
            with st.expander("Extracted pitch deck text"):
                st.text(run["deck_text"])
        with st.expander("Profile text sent to Claude"):
            st.text(run["profile_text"])
