---
name: arvis-ops
description: How ARVIS answers any question about leads, emails, markets, scraping runs or the pipeline, and how it starts a scrape or audit. Use whenever Aryan asks "how many", "show me", "what did you scrape", "start a scrape for X", or asks for the daily report. Always run arvisctl; never answer from memory.
---

# arvis-ops

## Rule one
Every number or lead you tell Aryan comes from `arvisctl`, run in the terminal, in the same
turn. If `arvisctl` errors, paste the error line to Aryan. Never say "no leads yet" or make up
a figure without running it.

## Commands (installed at ~/.local/bin/arvisctl, reads /opt/arvis/.env)
| Aryan asks | Run |
|---|---|
| how many leads / emails scraped | `arvisctl stats` |
| show me leads (optionally with email / a market / a group) | `arvisctl leads --limit 10 --with-email` · `--market mk_un_london_dentist` · `--group "Healthcare"` |
| which markets / what's next tonight | `arvisctl markets --status active` |
| did last night's run work | `arvisctl runs --limit 10` |
| scrape <niche> in <city> now | find the id with `arvisctl markets`, then `arvisctl dispatch scrape --market <id>`; if no market exists, tell Aryan the city/niche is not seeded and ask whether to add it |
| run tonight's batch now | `arvisctl dispatch scrape --count 3` |
| audit sites now | `arvisctl dispatch audit --limit 40` |
| daily report | `arvisctl report` and send the text as-is |

Market ids look like `mk_<cc>_<city>_<niche>` (e.g. `mk_ca_toronto_dentist`). Niche groups:
Healthcare, Legal & Finance, Property, Home Services, Hospitality & Wellness, Education.

## How to answer
- Short. Numbers first, then one line of context. Paste `arvisctl leads` lines as they are;
  each already carries the source (Google Maps listing URL) and the email's source (the
  business's own website).
- A dispatch takes 2–10 minutes on GitHub Actions. Say so, and offer to check with
  `arvisctl runs` later. Do not poll in a loop.
- The nightly schedule (02:00 IST, 3 markets) runs on GitHub without you; `dispatch` is only
  for extra runs Aryan asks for.

## Never do
- Never scrape, fetch or open Google Maps, Instagram, LinkedIn or any website yourself from
  the VPS. Scraping happens only in the GitHub Actions workers.
- Never edit Supabase rows by hand except through documented commands.
- Never run more than one dispatch per request. Never dispatch more than 3 markets at once.
- Never reveal API keys or the contents of /opt/arvis/.env.
