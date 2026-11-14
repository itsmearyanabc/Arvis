# ARVIS — AR Medias operating system

ARVIS is the in-house agent that runs the non-sales side of AR Medias (armedias.com):
market research, lead scraping, website audits, email enrichment and verification,
personalised cold email with follow-ups, reply sorting, meeting booking, website
monitoring and daily/weekly Telegram reports. Aryan only attends meetings and closes.

It is built on the open-source **Hermes Agent** by Nous Research
(<https://hermes-agent.nousresearch.com/docs>): Hermes provides the LLM loop, the
Telegram gateway, cron scheduling and the skills format. Everything ARVIS knows how
to do lives in `hermes/skills/*/SKILL.md` (agentskills.io format).

## Architecture

```
VPS #1 — existing Hostinger box (armedias.com under PM2, 1 vCPU / 3.8 GiB)
└── NOTHING from this repo runs here. Not touched, not loaded, not monitored from itself.

VPS #2 — dedicated ARVIS box (Ubuntu 24.04, ~2 vCPU / 8 GB)  ← decided 2026-11-15
├── nginx ............... fresh install; docker/nginx/arvis.conf serves
│                          arvis.armedias.tech / book.armedias.tech (certbot TLS)
└── arvis (Linux user, home /opt/arvis)
    ├── systemd slice "arvis.slice" ... CPUQuota/MemoryMax as sane limits (90% cores, 80% RAM)
    ├── Hermes Agent .................. gateway (Telegram bot "ARVIS") + cron + skills
    │       LLM: Gemini free tier → Groq / Cerebras / OpenRouter :free fallbacks
    └── Docker (docker/docker-compose.yml, all ports bound to 127.0.0.1)
        ├── scraper ....... gosom/google-maps-scraper  (lead source #1)
        ├── reacher ....... reacherhq/check-if-email-exists (email verification)
        ├── searxng ....... self-hosted meta-search (public web lookup, free)
        ├── uptime-kuma ... website monitoring (armedias.com, clients, our own) from OUTSIDE
        └── calcom ........ self-hosted booking (Phase 4, commented out until then)

Data flow
  Markets ─▶ scrape ─▶ Google Sheets (Leads) ─▶ audit + enrich/verify ─▶ draft (approval gate)
         ─▶ send sequence (new lookalike domain, Zoho) ─▶ inbox triage ─▶ booking brief
  Google Sheets is the system of record first; later a one-way push into ARVIS's own
  Supabase project (lead dashboard). ARVIS never has direct DB access to armedias.com's Supabase.
```

Control panel: the Telegram bot **ARVIS**. Aryan tells it which country / city / niche to
work; ARVIS can also research and rank less-saturated markets. Every day it reports
scraped / verified / sent / replied / booked (reply and booking rate, no open-rate pixels).

## Hard rules (apply to every skill, every day)

**Legal / reputation**
- Strictly legal. Nothing that could harm the AR Medias name.
- No LinkedIn scraping or automation. No logged-in Instagram automation. Not even with
  separate accounts. See `docs/instagram-and-linkedin.md`.
- Email lookup only from: the business's own public website, Google Maps listings, public
  search (Brave Search API free tier or self-hosted SearXNG), Hunter.io free tier.
  Verified with self-hosted Reacher. Never bought lists, never scraped social profiles.
- B2B targets only. Never consumer / personal addresses.
- CAN-SPAM / CASL compliant: real postal address in every email, working unsubscribe,
  honest subject and from-name, unsubscribes honoured immediately and forever.
- Cold email goes out from new lookalike domains (e.g. armedias.co) with Zoho mailboxes,
  SPF/DKIM/DMARC and a 2–3 week warm-up. **Never** from armedias.com or armedias.tech.

**Quality over quantity**
- Max **50 emails/day total** at first, grown slowly and only when reply rate holds.
- Every lead gets `fit_score`, `ticket_score` (review count/rating, runs ads per Meta Ad
  Library, bad/slow/no-SSL site = bigger project) and `contact_quality` (named / generic / none).
- Prefer named decision-makers (`john@` over `info@`, owner phone from Google Maps).

**Copy rules (AR Medias house rules)**
- Never state team size, hourly rates or minimum project size. Pricing is custom per client.
- Templates are written or approved by Aryan. `approved_by_aryan` must be TRUE before any
  send until he lifts the gate.

**Pacing**
- Everything is paced: random gaps, exponential backoff, small nightly batches.
  Continuous but slow. Nothing gets banned.

**Infrastructure**
- armedias.com (PM2, its own VPS) is never touched, restarted or loaded. SEO and responsiveness
  must not drop. ARVIS lives on a second, dedicated VPS; the only link is `armedias.com/admin`
  getting a plain link to the dashboard later.
- ARVIS runs as user `arvis` in `/opt/arvis` under `arvis.slice` caps on its own box.
- Free API tiers everywhere. The only accepted costs: domains, mailboxes, and optionally
  ~$10/mo of an OpenRouter paid model if free tiers rate-limit the 24/7 agent.
- Aryan runs every VPS command himself. Claude never gets SSH access.

## Repository layout

```
README.md                 this file
.env.example              every key, where to get it free
vps/01-create-user.sh     arvis user, /opt/arvis, systemd slice caps
vps/02-install-docker.sh  official Docker repo, arvis in docker group
vps/03-install-hermes.sh  Hermes install + Telegram gateway, as arvis
docker/docker-compose.yml scraper, reacher, searxng, uptime-kuma, (calcom)
docker/nginx/arvis.conf   separate server block for arvis./book.armedias.tech
hermes/skills/*/SKILL.md  one skill per department
hermes/cron.md            schedule for each skill
sheets/schema.md          Google Sheets tabs and columns
docs/instagram-and-linkedin.md  why no IG/LinkedIn automation, what we do instead
data/                     local scratch, git-ignored
```

## Phase plan

| Phase | What | Gate (Aryan's proof) |
|---|---|---|
| 0 | This scaffold | files committed |
| 1 | Buy ARVIS VPS; paste its report; run `vps/01`→`03`; BotFather bot; Hermes answers on Telegram | pasted outputs + Telegram screenshot |
| 1b | In parallel: buy lookalike domain (e.g. armedias.co) + Zoho mailboxes, set SPF/DKIM/DMARC, start warm-up | DNS checks pass |
| 2 | Docker scraper up; `scrape-leads` → Google Sheets; `daily-report` on Telegram | Sheet rows + daily report screenshot |
| 3 | Warm-up finishes (2–3 weeks from 1b); mailboxes registered in the Mailboxes tab | warm-up tool report |
| 4 | `audit-website`, `enrich-verify` (Reacher), Uptime Kuma, Cal.com on book.armedias.tech | Sheet rows, booking page loads |
| 5 | `draft-email` with approval gate on Telegram | approved drafts in Sheet |
| 6 | `send-sequence` live, 50/day cap, follow-ups, unsubscribe | first replies reported |
| 7 | `inbox-triage`, `booking-brief`, Supabase push, arvis.armedias.tech dashboard | booked meeting with brief |

Each phase starts only after the previous one is confirmed by pasted output or screenshot.
