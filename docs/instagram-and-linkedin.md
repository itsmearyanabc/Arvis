# Why ARVIS does not automate Instagram or LinkedIn

Short version: it is against both platforms' terms, it gets accounts banned fast (including the
real AR Medias accounts if they are ever linked by device, IP, phone or payment method), and in
several countries scraping personal profile data is a privacy-law problem. None of that is worth
one extra lead for an agency that lives on reputation.

## What "automation" means here, and why separate accounts do not help
- **LinkedIn**: its User Agreement forbids scraping, bots, browser extensions that automate
  actions, and any use of data obtained that way. LinkedIn detects automation by behaviour (speed,
  patterns, headless browsers), by IP (data-centre ranges like a VPS are flagged immediately) and
  by account graph. A throwaway account is restricted within days; the real account that logs
  in from the same laptop or phone is next. LinkedIn has also sued scrapers and wins
  injunctions. Even "just viewing profiles" from a script is automation.
- **Instagram**: logged-in automation (follow/unfollow, DM bots, scraping followers, liking)
  violates Meta's terms. Detection is aggressive: action blocks, then checkpoints, then
  permanent disable, and Meta links accounts across devices and IPs. A VPS IP logging into a
  fresh account is the textbook ban signal. ARVIS lives on a VPS.
- **Personal data**: LinkedIn and Instagram profiles are *people*, not businesses. Collecting
  personal profile data without a lawful basis breaks GDPR (EU/UK), PIPEDA/CASL (Canada) and
  similar laws, and a complaint lands on AR Medias, not on a script.
- **Reputation**: every ban, every "why is your agency spamming my LinkedIn" post, costs more than
  a year of leads. 90% of AR Medias clients come from referrals. Nothing may put that at risk.

So: no scraping, no logged-in automation, no browser extensions, no "growth tools", no bought
profile data, on any account, ever. This is a hard rule for every ARVIS skill.

## What ARVIS does instead (all public, all B2B)
1. **Google Maps listings** via the self-hosted scraper: business name, category, address, phone,
   website, rating, reviews. Public business directory data about businesses.
2. **The business's own website**: contact / about / team pages, `mailto:` links, schema.org
   markup. If the owner publishes their name and email on their business site, it is a business
   contact.
3. **Public web search** (Brave Search API free tier): `"<business>"
   owner`, `site:<domain> @<domain>`. Only result snippets and the public pages they point to.
4. **Hunter.io free tier** for domain-pattern lookups on high-ticket leads only.
5. **Verification** with self-hosted Reacher so we only ever email addresses that exist.
6. **Meta Ad Library** (public, logged-out) to see whether a business runs ads: a budget signal.

ARVIS **may store** a business's public Instagram or LinkedIn URL found on its own website or
Maps listing. That link is for Aryan to open himself, as a human, from his own account, if he
wants to look before a call. ARVIS never fetches, visits or acts on those URLs.

## If Aryan ever wants social outreach
Do it by hand, from the real AR Medias accounts, a few per day, with real messages. ARVIS can
help by preparing a note per lead (what their site needs, what we'd say). The sending stays
human. The `ig-dm` / `ig-comment` style skills exist for drafting copy, not for automation.
