---
name: scrape-leads
description: Scrape Google Maps business listings for an active market with the self-hosted gosom/google-maps-scraper, score them, and append new leads to the Leads sheet. Use nightly for every market with status=active, or when Aryan says "scrape <niche> in <city>".
---

# scrape-leads

## Purpose
The most important department. Builds the raw B2B lead pool, slowly and cleanly, from public
Google Maps listings only.

## Inputs
- **Markets** rows with `status=active` (or an explicit `city + niche` from Aryan).
- `SCRAPER_URL` (gosom web API). Query template: `"<niche> in <city>, <country>"` plus 2–4
  synonym queries per niche (e.g. "dentist", "dental clinic", "orthodontist").
- Dedup key: Google `place_id`; fallback `normalized(name)+normalized(phone)`.

## Procedure
1. Pick the active market with the oldest `last_scraped_at`.
2. Submit ONE job to the scraper API (2 headless browsers max), depth ≤ 2, max results per
   query ≤ 60.
3. Poll the job, with exponential backoff (30 s → 5 min).
4. For each result: skip if `place_id` exists in **Leads**. Skip if it looks like a consumer /
   private person listing (no business category, residential address).
5. Compute:
   - `ticket_score` 0–100: reviews ≥50 (+25), rating ≥4.3 (+15), has website (+10),
     website issues flagged later by `audit-website` (+ up to 30), runs Meta ads
     (checked later by `enrich-verify`, +20).
   - `fit_score` 0–100: niche match, city match, business size signals, not a chain/franchise.
   - `contact_quality`: `named` if owner name found in listing/site, `generic` if only
     info@/contact form, `none`.
6. Append to **Leads** with `source=google_maps`, `status=new`, store `instagram_url` /
   `linkedin_url` / `facebook_url` if present on the listing (for Aryan to visit manually, never
   for automation).
7. Update `Markets.last_scraped_at`, `Markets.businesses_found`.
8. Log counts for `daily-report`.

## Outputs (Leads tab)
See `sheets/schema.md` → Leads. Required on insert: `lead_id, place_id, business_name, niche,
city, country, address, phone, website, rating, review_count, maps_url, source, fit_score,
ticket_score, contact_quality, status=new, scraped_at`.

## Rate limits
- ≤ 3 jobs per night, ≤ 4 queries each, ≤ 60 results per query, 2 browsers, window
  02:00–05:00 local.
- Random 20–90 s gap between queries inside a job. Back off ×2 on any error, give up after 5.
- Target ≤ 150 new leads/night. Quality over quantity; we only need ~50 sends/day.

## Never do
- Never scrape LinkedIn, Instagram, Facebook, Yelp-logged-in or any site behind a login.
- Never scrape residential / consumer listings; B2B only.
- Never run the scraper outside the nightly window unless Aryan asks for a one-off.
- Never write to armedias.com's Supabase; Google Sheets only (ARVIS's own Supabase later).
- Never re-scrape a market more than once per 14 days.
