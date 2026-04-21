"""Founder-Scorer-IQ — LinkedIn-only prototype (IQFSV1).

Flow:
1. Analyst enters founder name (required) plus optional company, pitch deck,
   and LinkedIn URL override.
2. If a LinkedIn URL is provided, we use it directly. Otherwise we best-guess
   the profile via Google search over `linkedin.com/in`.
3. We scrape the profile, optionally parse the deck for context, and ask
   Claude for a short summary plus a 4-dimension light scorecard.
4. The report clearly shows which LinkedIn profile was used and lets the
   analyst edit the URL and re-run.
"""

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
    page_title="Founder-Scorer-IQ — LinkedIn prototype",
    page_icon="IQ",
    layout="wide",
)

GRADE_COLORS = {
    "Strong Yes": "green",
    "Lean Yes": "blue",
    "Maybe": "orange",
    "Lean No": "red",
    "Strong No": "red",
}

GRADE_MARKERS = {
    "Strong Yes": "[++]",
    "Lean Yes": "[+]",
    "Maybe": "[~]",
    "Lean No": "[-]",
    "Strong No": "[--]",
}

MATCH_BADGE = {
    "high": ("green", "High-confidence match"),
    "medium": ("orange", "Medium-confidence match — please verify"),
    "low": ("red", "Low-confidence match — please verify or paste URL"),
    "analyst": ("blue", "Analyst-provided URL"),
}


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
    """Scrape + score. Returns a dict ready to render and persist."""
    profile = scrape_linkedin_profile(linkedin_url) if linkedin_url else {}
    profile_text = summarize_profile_for_prompt(profile)

    has_profile_data = bool(profile) and not profile.get("_scrape_error")
    if has_profile_data:
        result = score_founder(
            founder_name=founder_name,
            company_name=company_name,
            linkedin_url=linkedin_url,
            profile_text=profile_text,
            deck_text=deck_text or None,
        )
    else:
        result = None

    return {
        "founder_name": founder_name,
        "company_name": company_name,
        "linkedin_url": linkedin_url,
        "url_source": url_source,
        "match": match_meta
        or {
            "match_confidence": "analyst" if url_source == "analyst" else "low",
            "title": "",
            "snippet": "",
            "candidates": [],
            "query": "",
        },
        "profile": profile,
        "profile_text": profile_text,
        "deck_text": deck_text,
        "result": result,
    }


with st.sidebar:
    st.title("History")
    history = load_history()
    if not history:
        st.caption("No runs yet.")
    else:
        for entry in reversed(history[-20:]):
            grade = entry.get("grade", "")
            marker = GRADE_MARKERS.get(grade, "")
            result = entry.get("result") or {}
            is_failed = not result
            header = (
                f"[scrape failed] {entry.get('founder_name', '')}"
                if is_failed
                else f"{marker} {entry.get('founder_name', '')} — "
                     f"{entry.get('overall_linkedin_fit', 0)}/100"
            )
            with st.expander(header):
                st.caption(entry.get("timestamp", "")[:16].replace("T", " "))
                if entry.get("company_name"):
                    st.caption(f"Company: {entry['company_name']}")
                if entry.get("linkedin_url"):
                    st.markdown(f"[LinkedIn profile]({entry['linkedin_url']})")
                if is_failed:
                    st.warning("LinkedIn scrape failed for this run.")
                else:
                    st.write(entry.get("summary", ""))
                if st.button("Delete", key=f"del_{entry['id']}"):
                    delete_entry(entry["id"])
                    st.rerun()

st.title("Founder-Scorer-IQ")
st.caption(
    "India Quotient internal prototype — LinkedIn-only founder assessment. "
    "Enter a founder name; optionally add company, pitch deck, or a LinkedIn URL."
)
st.caption(f"LinkedIn provider: `{provider_name()}` (set via `LINKEDIN_PROVIDER` in .env)")

with st.form("founder_form"):
    col1, col2 = st.columns(2)
    with col1:
        founder_name = st.text_input(
            "Founder name *",
            placeholder="e.g. Nikhil Kamath",
        )
        company_name = st.text_input(
            "Company name (optional)",
            placeholder="e.g. Zerodha",
        )
    with col2:
        linkedin_url_in = st.text_input(
            "LinkedIn URL (optional)",
            placeholder="https://linkedin.com/in/...",
            help=(
                "If you already know the exact profile, paste it here. "
                "Otherwise we'll try to find the best match."
            ),
        )
        deck_file = st.file_uploader(
            "Pitch deck PDF (optional)",
            type=["pdf"],
            help="Used only as extra context for matching and summary.",
        )

    submitted = st.form_submit_button(
        "Analyze founder", type="primary", use_container_width=True
    )

if submitted:
    if not founder_name.strip():
        st.error("Founder name is required.")
    else:
        _reset_run_state()

        deck_text = ""
        if deck_file is not None:
            with st.status("Reading pitch deck...", expanded=False):
                deck_text = extract_deck_text(deck_file.getvalue())
                if not deck_text:
                    st.warning("Could not extract text from the PDF.")

        with st.status("Resolving LinkedIn profile...", expanded=True) as status:
            chosen_url = linkedin_url_in.strip()
            if chosen_url:
                match_meta = {
                    "match_confidence": "analyst",
                    "title": "",
                    "snippet": "",
                    "candidates": [],
                    "query": "",
                }
                url_source = "analyst"
                st.write("Using analyst-provided URL.")
            else:
                st.write("Searching LinkedIn via Google...")
                match = find_linkedin_url(
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
                    st.write("Scoring against IQ context...")
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
                "Couldn't auto-find a LinkedIn profile. Paste the URL directly "
                "in the form and try again."
            )

def _render_edit_url_panel(run: dict) -> None:
    """Shared 'Not the right profile?' expander for any run (success or failure)."""
    match_meta = run["match"]
    with st.expander("Not the right profile? Edit the URL and re-analyze.", expanded=not run["result"]):
        new_url = st.text_input(
            "Corrected LinkedIn URL",
            value=run["linkedin_url"],
            key="override_url",
        )
        candidates = match_meta.get("candidates") or []
        if candidates:
            st.caption("Other candidates from the search:")
            for c in candidates:
                st.markdown(f"- [{c}]({c})")
        if st.button("Re-analyze with this URL", type="secondary"):
            with st.status("Re-analyzing...", expanded=True) as status:
                st.write(f"Scraping profile: {new_url}")
                new_run = _run_pipeline(
                    founder_name=run["founder_name"],
                    company_name=run["company_name"],
                    linkedin_url=new_url.strip(),
                    deck_text=run.get("deck_text", ""),
                    url_source="analyst",
                    match_meta={
                        "match_confidence": "analyst",
                        "title": "",
                        "snippet": "",
                        "candidates": [],
                        "query": "",
                    },
                )
                scrape_err = new_run["profile"].get("_scrape_error")
                if scrape_err:
                    status.update(label="Scrape failed", state="error")
                else:
                    status.update(label="Re-analysis complete", state="complete")
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


run = st.session_state.get("last_run")
if run:
    result = run["result"]
    match_meta = run["match"]

    st.divider()
    st.subheader("LinkedIn profile used")

    badge_color, badge_label = MATCH_BADGE.get(
        match_meta.get("match_confidence", "low"),
        ("gray", "Unknown match"),
    )
    st.markdown(f":{badge_color}[**{badge_label}**]")
    st.markdown(f"[{run['linkedin_url']}]({run['linkedin_url']})")
    prov = run["profile"].get("_provider") or provider_name()
    st.caption(f"Scraped via: `{prov}`")
    if match_meta.get("title"):
        st.caption(match_meta["title"])
    if match_meta.get("snippet"):
        st.caption(match_meta["snippet"])

    scrape_error = run["profile"].get("_scrape_error")

    if scrape_error:
        st.divider()
        st.subheader("Unable to scrape LinkedIn profile")
        st.error(
            "We found a likely profile but couldn't pull its data. "
            "No score has been generated — scoring with zero data would be misleading."
        )
        diag_col1, diag_col2 = st.columns(2)
        with diag_col1:
            st.markdown("**URL tried**")
            st.code(run["profile"].get("_scrape_url", run["linkedin_url"]))
            st.markdown("**Actor error**")
            st.code(scrape_error, language="text")
        with diag_col2:
            st.markdown("**Apify run**")
            st.write(f"Status: `{run['profile'].get('_run_status', 'unknown')}`")
            run_id = run["profile"].get("_run_id")
            if run_id:
                st.markdown(
                    f"[Open in Apify console](https://console.apify.com/actors/runs/{run_id})"
                )
        st.caption(
            "Common causes: the Apify LinkedIn actor needs an active payment "
            "method on your account, the profile is private, or the actor is "
            "being rate-limited. Try editing the URL below, or swap the actor "
            "via the `APIFY_LINKEDIN_ACTOR` env var."
        )

        _render_edit_url_panel(run)

        with st.expander("Raw actor response"):
            st.json(run["profile"])
    else:
        _render_edit_url_panel(run)

        st.divider()

        score = result.get("overall_linkedin_fit", 0)
        grade = result.get("grade", "N/A")
        grade_color = GRADE_COLORS.get(grade, "gray")
        confidence = result.get("confidence_score", 0)

        top1, top2, top3 = st.columns([1, 1, 2])
        with top1:
            st.metric("LinkedIn fit", f"{score}/100")
        with top2:
            st.markdown("**Grade**")
            st.markdown(f":{grade_color}[**{grade}**]")
            st.caption(f"Confidence: {confidence}/10")
        with top3:
            st.markdown("**Summary**")
            st.write(result.get("summary", ""))

        st.info(
            "This score uses only LinkedIn (plus any provided deck text). "
            "Treat it as a screening signal, not an investment decision."
        )

        st.divider()
        st.subheader("Scorecard")
        dims = {
            "Career signal": result.get("career_signal", {}),
            "Founder relevance": result.get("founder_relevance", {}),
            "Execution signal": result.get("execution_signal", {}),
            "Credibility signal": result.get("credibility_signal", {}),
        }
        cols = st.columns(4)
        for col, (name, data) in zip(cols, dims.items()):
            with col:
                st.metric(name, f"{data.get('score', 0)}/10")
                st.caption(data.get("reasoning", ""))

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Strengths")
            for s in result.get("strengths", []) or []:
                st.markdown(f"- {s}")
        with c2:
            st.subheader("Concerns")
            for c in result.get("concerns", []) or []:
                st.markdown(f"- {c}")

        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Missing information")
            for m in result.get("missing_information", []) or []:
                st.markdown(f"- {m}")
        with c4:
            st.subheader("Diligence questions")
            for i, q in enumerate(result.get("next_questions_for_diligence", []) or [], 1):
                st.markdown(f"**{i}.** {q}")

        with st.expander("Raw LinkedIn data"):
            st.json(run["profile"])
        if run.get("deck_text"):
            with st.expander("Extracted pitch deck text"):
                st.text(run["deck_text"])
        with st.expander("Profile text sent to Claude"):
            st.text(run["profile_text"])
