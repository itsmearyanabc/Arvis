---
name: scrape-leads
description: Dispatch the nightly Google Maps scrape (gosom/google-maps-scraper running in the GitHub Actions "scrape" workflow), watch it, and report the new leads it wrote to Supabase. Use nightly for every market with status=active, or when Aryan says "scrape <niche> in <city>".
---

# scrape-leads

## Purpose
The most important department. Builds the raw B2B lead pool, slowly and cleanly, from public
Google Maps listings only. The browser work runs on a GitHub Actions runner
(`.github/workflows/scrape.yml` → `workers/scrape/`), never on the VPS.

## Inputs
- **Markets** rows with `status=active` (or an explicit `city + niche` from Aryan).
- GitHub API (`GITHUB_TOKEN`, `GITHUB_REPO`): `POST /repos/{repo}/actions/workflows/scrape.yml/dispatches`
  with `inputs.market_id`. The worker builds `"<niche> in <city>, <country>"` plus 2–4 synonyms.
- Dedup key: Google `place_id`; fallback `normalized(name)+normalized(phone)`.

## Procedure
1. Pick the active market with the oldest `last_scraped_at`.
2. Dispatch with `arvisctl dispatch scrape --market <id>` (see `arvis-ops`). The GitHub schedule
   also fires it at 02:00 IST; dispatch only when Aryan asks or no run happened in 20 h.
3. Check later with `arvisctl runs`; on failure report the error line to Aryan.
4. The worker skips existing `place_id`s and consumer / private-person listings (no business
   category). Nothing else is filtered at this stage.
5. The worker computes:
   - `ticket_score` 0–100: reviews ≥50 (+25), rating ≥4.3 (+15), has website (+10),
     website issues flagged later by `audit-website` (+ up to 30), runs Meta ads
     (checked later by `enrich-verify`, +20).
   - `fit_score` 0–100: niche match, city match, business size signals, not a chain/franchise.
   - `contact_quality`: `named` if owner name found in listing/site, `generic` if only
     info@/contact form, `none`.
6. The worker upserts into `leads` with `source=google_maps`, `status=new`, storing
   `instagram_url` / `linkedin_url` / `facebook_url` if present (for Aryan to visit manually,
   never for automation), and updates `markets.last_scraped_at` / `businesses_found`.
7. The brain reads the `worker_runs` row and logs counts for `daily-report`.

## Outputs (Leads table)
See `supabase/schema.sql` → Leads. Required on insert: `lead_id, place_id, business_name, niche,
city, country, address, phone, website, rating, review_count, maps_url, source, fit_score,
ticket_score, contact_quality, status=new, scraped_at`.

## Rate limits
- One workflow run per night, ≤ 4 queries, ≤ 60 results per query, 2 browsers on the runner.
  GitHub free minutes: ~2,000/mo on a private repo; a run is ≤ 90 min, so ≤ 1/night.
- Back off ×2 on any error, give up after 5. Target ≤ 150 new leads/night.

## Never do
- Never scrape LinkedIn, Instagram, Facebook, Yelp-logged-in or any site behind a login.
- Never scrape residential / consumer listings; B2B only.
- Never run a browser or the scraper on the VPS. Dispatch only.
- Never use proxies, CAPTCHA solvers or stealth settings; if Google blocks the runner, stop and report.
- Never write to armedias.com's Supabase; Supabase only (ARVIS's own Supabase later).
- Never re-scrape a market more than once per 14 days.
