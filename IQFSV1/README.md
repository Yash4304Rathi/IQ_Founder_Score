# Founder-Scorer-IQ — LinkedIn prototype (IQFSV1)

Internal India Quotient prototype. Given a founder name (and optionally a
company name, pitch deck PDF, or exact LinkedIn URL), this tool:

1. Best-guesses the founder's LinkedIn profile via Apify + Google Search
   (or uses the URL you provide).
2. Scrapes that profile via an Apify LinkedIn actor.
3. Asks Claude for a short summary and a lightweight four-dimension
   scorecard: career signal, founder relevance, execution signal,
   credibility signal.
4. Shows which profile was used, lets you edit the URL if wrong, and keeps
   a local history of runs.

This is deliberately a narrow v1 — LinkedIn only. Company scraping and
other sources are explicitly deferred.

## Setup

```bash
cd IQFSV1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Environment variables (read from `../.env`):

- `ANTHROPIC_API_KEY`
- `APIFY_API_KEY`
- Optional: `ANTHROPIC_MODEL` (defaults to `claude-sonnet-4-5`)
- Optional: `APIFY_LINKEDIN_ACTOR` and `APIFY_LINKEDIN_INPUT_KEY` — choose
  which Apify LinkedIn actor to call. The two keys must be kept in sync with
  the actor's input schema. Known combos:

  | Actor | Input key | Price | Free-plan API |
  | --- | --- | --- | --- |
  | `dataweave/linkedin-profile-scraper` (default) | `urls` | $2 / 1000 | yes |
  | `sourabhbgp/linkedin-profile-scraper` | `profiles` | $2 / 1000 | yes |
  | `dev_fusion/Linkedin-Profile-Scraper` | `profileUrls` | $10 / 1000 | no (paid plan required) |

## Run

```bash
streamlit run app.py
```

Open the URL Streamlit prints.

## Inputs

- **Founder name** — required.
- **Company name** — optional; improves LinkedIn match accuracy.
- **Pitch deck PDF** — optional; used only for extra context.
- **LinkedIn URL** — optional; if provided, we skip matching.

## Output

- Profile actually used (with match confidence badge) and a way to edit the
  URL and re-run.
- Short founder summary.
- Four-dimension scorecard + overall LinkedIn-fit score + confidence.
- Strengths, concerns, missing information, diligence questions.
- Raw LinkedIn JSON and profile text sent to the LLM (for debugging).

## Files

- `app.py` — Streamlit UI and pipeline orchestration.
- `linkedin.py` — profile URL lookup + LinkedIn profile scraping (Apify).
- `deck.py` — PDF text extraction (pypdf).
- `scorer.py` — Claude-based summary + scorecard.
- `history.py` — JSON-file run history.

## Notes / caveats

- Scoring uses only LinkedIn; it is a screening signal, not a decision.
- Matching by founder name alone can pick the wrong profile. The UI always
  shows which profile was used and supports editing the URL.
- Apify actor IDs are hardcoded (`apify/google-search-scraper` and the
  LinkedIn profile actor `2SyF0bVxmgGr8IVCZ`). Swap if you move providers.
