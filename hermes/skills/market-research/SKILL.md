---
name: market-research
description: Research and rank which country / city / niche combinations are least saturated and most worth prospecting for AR Medias (web design, branding, media). Use when Aryan asks "where should we prospect next", "rank markets", or before a new scrape campaign is planned.
---

# market-research

## Purpose
Turn a vague target ("dentists in Canada", "find me an under-served niche in the UK") into a ranked
shortlist of `country / city / niche` rows in the **Markets** tab, each with a saturation estimate,
an average-ticket estimate and a one-line why.

## Inputs
- From Aryan (Telegram): country, optional city/region, optional niche(s), optional "surprise me".
- Tools: Google Programmable Search (free tier), the GitHub Actions `scrape` workflow dispatched with
  `max_results=20` for small probe runs, public pages only.

## Procedure
1. Expand the request into ≤15 candidate `(city, niche)` pairs. Prefer niches with high
   lifetime customer value and visible marketing spend (clinics, law firms, real estate,
   home services, private schools, hospitality, B2B services).
2. For each pair run one probe: Maps count of businesses, share with no website, share with
   rating ≥4.3 and ≥50 reviews (high-ticket signal), count of local agencies ("web design
   <city>") as the saturation proxy.
3. Score: `opportunity = demand × ticket ÷ (1 + agency_saturation)`. Keep it simple, show the
   numbers, never pretend precision.
4. Write rows to **Markets** (`supabase/schema.sql`), status `proposed`.
5. Reply on Telegram with the top 5 as a short table and ask which to activate.

## Outputs (Markets table)
`market_id, country, city, niche, businesses_found, pct_no_website, pct_high_ticket,
agency_count, opportunity_score, rationale, status (proposed|active|paused|done), created_at`

## Rate limits
- ≤ 30 search queries and ≤ 5 probe scrapes per run. One run per request, never scheduled
  more than weekly. Random 3–10 s gaps between queries.

## Never do
- Never scrape or query LinkedIn, Instagram, Facebook groups or any logged-in surface.
- Never collect person-level data here. Markets only.
- Never activate a market by itself; Aryan picks.
- Never spend paid API credits; stop and report if a free quota is exhausted.
