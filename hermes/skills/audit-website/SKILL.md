---
name: audit-website
description: Dispatch and read the nightly website audit (GitHub Actions "audit" workflow, workers/audit/audit.py) that checks speed, mobile, SSL, SEO basics and design age to size the project and feed personalisation. Use for leads with status=new, or when Aryan says "audit <url>".
---

# audit-website

## Purpose
Find the concrete, true thing we can say in the first email ("your site takes 7 s on mobile and
has no SSL") and raise `ticket_score` for leads whose site is a bigger job.

## Inputs
- **Leads** rows with `status=new` and non-empty `website`, oldest first, batch ≤ 40/run.
- Runs in GitHub Actions (`.github/workflows/audit.yml`): plain HTTP fetch of the homepage,
  Google PageSpeed Insights API (free), SSL via the HTTPS handshake. Nothing runs on the VPS;
  the brain dispatches the workflow (or a single-URL variant for "audit <url>") and reads
  the `audits` rows afterwards.

## Checks (each → boolean/number + one plain-English finding)
- `ssl_ok`, `https_redirect`, `mobile_score` (PSI 0–100), `perf_score`, `lcp_s`,
- `has_title`, `has_meta_desc`, `h1_count`, `img_alt_missing_pct`,
- `cms` (WordPress / Wix / Squarespace / custom / unknown), `copyright_year`, `looks_outdated`
  (year ≤ current-3 OR no viewport meta OR table layout),
- `broken_links_sampled` (≤ 10 internal links tested),
- `contact_email_on_site`, `contact_form`, `booking_widget`,
- `pixels`: `meta_pixel`, `google_tag` (spend signal).

## Procedure
1. Fetch homepage (timeout 15 s, 1 retry). If it fails twice → `site_status=down`, which is
   itself a strong lead signal; record and move on.
2. Run checks, write a row to **Audits**, write `audit_summary` (≤ 2 sentences, factual,
   no insults) and `top_issue` back to **Leads**.
3. Adjust `Leads.ticket_score`: no site +30, down +25, no SSL +20, mobile <50 +15,
   outdated +15, cap 100. Set `Leads.status=audited`.

## Outputs (Audits table)
`audit_id, lead_id, website, checked_at, site_status, ssl_ok, mobile_score, perf_score, lcp_s,
cms, copyright_year, looks_outdated, has_title, has_meta_desc, broken_links_sampled,
contact_email_on_site, meta_pixel, google_tag, top_issue, audit_summary`

## Rate limits
- ≤ 40 sites/run, ≤ 3 requests per site, 5–20 s random gap between sites. PSI API: ≤ 25/run.
- Respect `robots.txt` Disallow for the pages we fetch. Honest User-Agent `ARVIS-audit (armedias.com)`.

## Never do
- Never crawl beyond 3 pages per site. Never submit forms. Never hit login/admin paths.
- Never store page content, only the findings.
- Never claim an issue we did not measure; every `top_issue` must map to a check above.
