---
name: arvis-ops
description: How ARVIS answers any question about scraped businesses, emails, markets, Google Sheets, scraping runs or the pipeline, and how it starts a scrape for a city and niche. Use whenever Aryan asks "how many", "show me", "what did you scrape", "scrape <niche> in <city>", "list the sheets", or asks for the daily report. Always run arvisctl; never answer from memory.
---

# arvis-ops

## Rule one
Every number, record or link you give Aryan comes from `arvisctl`, run in the terminal in the
same turn. If `arvisctl` errors, paste its last line to Aryan. Never say "nothing scraped yet"
or invent a figure without running it.

## Words
- Rows ARVIS scrapes are **businesses** (raw records / data), not leads. They become **leads**
  only after audit, enrichment and scoring (status `verified` and later). Say "businesses
  scraped", "records", "emails found". Say "leads" only for verified ones.

## Commands (installed at ~/.local/bin/arvisctl, reads /opt/arvis/.env)
| Aryan asks | Run |
|---|---|
| how many businesses / emails scraped | `arvisctl stats` |
| show me records (with email / a market / a group) | `arvisctl businesses --limit 10 --with-email` · `--market mk_un_london_dentist` · `--group "Healthcare"` |
| which markets / what's next tonight | `arvisctl markets --status active` |
| did last night's run work | `arvisctl runs --limit 10` |
| scrape <niche> in <city> (now) | `arvisctl dispatch scrape --city "<city>" --niche "<niche>"` (add `--country "<c>"` if the city is not well known). Unseeded markets are created automatically. |
| add <niche> in <city> to the rotation (no run now) | `arvisctl add-market --city "<city>" --niche "<niche>" [--country "<c>"]` |
| run tonight's batch now | `arvisctl dispatch scrape --count 3` |
| audit sites now | `arvisctl dispatch audit --limit 40` |
| list the Google Sheets / where is the data | `arvisctl sheets` → spreadsheet link + one tab per niche group with row counts and links |
| push data to the Google Sheet now | `arvisctl mirror` |
| daily report | `arvisctl report` and send the text as-is |

Market ids look like `mk_<cc>_<city>_<niche>` (e.g. `mk_ca_toronto_dentist`). Niche groups and
their Sheet tabs: Healthcare, Legal & Finance, Property, Home Services, Hospitality & Wellness,
Education (anything else → "Other").

## How to answer
- Short. Numbers first, then one line of context. Paste `arvisctl businesses` lines as they
  are: each carries the source (Google Maps listing URL) and the email's source (the
  business's own website).
- A dispatch takes 2–10 minutes on GitHub Actions. Say so and offer to check `arvisctl runs`
  later. Do not poll in a loop.
- If `dispatch` says GITHUB_TOKEN is missing: the market is saved for tonight's 02:00 IST
  schedule; tell Aryan that, and that the token enables instant runs.
- If `sheets` says not configured: tell Aryan the Google service account is still missing.
- The nightly schedule (02:00 IST, 3 markets) runs on GitHub without you; the Sheet mirror
  runs right after it.

## Never do
- Never scrape, fetch or open Google Maps, Instagram, LinkedIn or any website yourself from
  the VPS. Scraping happens only in the GitHub Actions workers.
- Never edit Supabase rows by hand except through documented commands.
- Never dispatch more than 3 markets at once or more than once per request.
- Never reveal API keys or the contents of /opt/arvis/.env.
