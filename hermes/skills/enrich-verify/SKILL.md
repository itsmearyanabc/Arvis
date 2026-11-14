---
name: enrich-verify
description: Find a decision-maker email for an audited lead from public sources only (the business's own site, Google Maps listing, public web search, Hunter.io free tier) and verify it with self-hosted Reacher. Use for Leads with status=audited, or when Aryan says "find the email for <business>".
---

# enrich-verify

## Purpose
Turn a business into a real, verified, preferably named contact. Named `john@` beats `info@`.
A lead with no verifiable email is parked, not guessed at.

## Inputs
- **Leads** rows with `status=audited`, batch ≤ 30/run, highest `ticket_score` first.
- Sources, in order, stop when a named contact is found:
  1. Business website: /contact, /about, /team, footer, `mailto:` links, schema.org JSON-LD
     (`founder`, `employee`), WHOIS is **not** used (privacy-redacted and off-limits).
  2. Google Maps listing fields already scraped (owner replies to reviews often sign a name).
  3. Public web search (Brave API → SearXNG fallback): `"<business name>" owner`, `"<business
     name>" founder`, `site:<domain> @<domain>`. Public result snippets only.
  4. Hunter.io free tier: domain search (25/mo) — only for leads with `ticket_score ≥ 70`.
- Pattern guess: if a named person is known and the domain pattern is visible from another
  address (e.g. `first@`, `first.last@`), generate ≤ 3 candidates and let Reacher decide.
- Verification: `REACHER_URL` `/v0/check_email`. Accept `is_reachable=safe`; `risky` only if
  catch-all AND named; reject `invalid` / `unknown`.
- Ads signal: Meta Ad Library public search page (`facebook.com/ads/library`, logged-out, by
  page name) → `runs_meta_ads` boolean, +20 `ticket_score`.

## Procedure
1. For each lead gather candidates with the source order above. Record `email_source`.
2. Verify each candidate with Reacher (sequential, 5–15 s gaps). Keep the best verified one.
3. Write a **Contacts** row: `contact_name, role, email, email_status, email_source,
   contact_quality (named|generic|none), phone, verified_at`.
4. Update **Leads**: `contact_quality`, `primary_email`, `status=verified` or `status=parked`
   (reason `no_email` / `invalid_only`). Parked leads are retried once after 30 days.
5. Record `runs_meta_ads`, `instagram_url`, `linkedin_url` (URLs only, for Aryan, never visited by
   ARVIS with an account).

## Outputs (Contacts tab + Leads updates) — see `sheets/schema.md`.

## Rate limits
- ≤ 30 leads/run, ≤ 10 search queries per lead, ≤ 3 Reacher checks per lead.
- Hunter: hard monthly budget 25 searches / 50 verifications; stop at 80% and report.
- Reacher checks spaced 5–15 s; the same mail server never more than 10 checks/hour.
- If outbound SMTP (port 25) is blocked on the VPS, Reacher returns `unknown` for everything:
  detect this (≥ 20 consecutive unknowns) → stop, report to Aryan, use Hunter verification only.

## Never do
- Never scrape LinkedIn, Instagram, Facebook profiles, or any logged-in page. Storing a public
  profile URL for Aryan is fine; fetching or automating it is not.
- Never buy, download or import lead lists.
- Never use personal addresses (gmail/yahoo/hotmail/icloud) unless it is the business's own
  published business contact; mark these `contact_quality=generic`.
- Never mark an email `verified` without a Reacher `safe` (or catch-all+named `risky`) result.
- Never email anyone from this skill; it only finds and verifies.
