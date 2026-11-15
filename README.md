# ARVIS — AR Medias operating system

ARVIS is the in-house agent that runs the non-sales side of AR Medias (armedias.com):
market research, lead scraping, website audits, email enrichment and verification,
personalised cold email with follow-ups, reply sorting, meeting booking, website
monitoring and daily/weekly Telegram reports. Aryan only attends meetings and closes.

The brain is **Hermes Agent** by Nous Research (<https://hermes-agent.nousresearch.com/docs>):
LLM loop, Telegram gateway, cron, skills. Everything ARVIS knows how to do lives in
`hermes/skills/*/SKILL.md`. Heavy work is pushed off the VPS to free, isolated workers.

## Architecture: multi-server, one brain (decided 2026-11-15)

```
                         ┌──────────────── Telegram (bot "ARVIS") ────────────────┐
                         │  Aryan commands, approves drafts, gets reports/alerts  │
                         └───────────────────────┬────────────────────────────────┘
                                                 │
 Hostinger VPS (1 vCPU / 3.8 GiB) — shared with armedias.com (PM2) — NEVER touched by ARVIS
 ┌───────────────────────────────────────────────┴────────────────────────────────┐
 │ user `arvis`, /opt/arvis, systemd slice CPUQuota=40% MemoryMax=1G, 2G swap     │
 │   BRAIN: Hermes gateway + cron + skills (idle < 300 MB, ~0 CPU)                 │
 │     - decides what to do, dispatches workers, drafts emails, sends via Zoho    │
 │     - never scrapes, never runs a browser, never serves a website              │
 │   Docker: reacher (email verification, 256 MB) — only container on the box    │
 └────────────┬───────────────────────────┬──────────────────────┬────────────────┘
              │ dispatch (GitHub API)     │ read/write            │ SMTP/IMAP
              ▼                           ▼                       ▼
 GitHub Actions (free)          Supabase free tier, Mumbai      Zoho Mail
   nightly workers:               ARVIS's OWN project             connect@armedias.tech
   - scrape  (gosom/google-       tables: markets, leads,         (SPF/DKIM/DMARC,
     maps-scraper in a runner)    audits, contacts, templates,    warm-up 2–3 wks)
   - audit   (site checks, PSI)   sequences, replies, unsubs,
   - enrich  (public web search)  bookings, mailboxes, monitors
   write results → Supabase          ▲
                                     │ reads (anon key + Aryan login)
 Vercel (free)                       │
   dashboard  arvis.armedias.tech ───┘   lead table, approvals, funnel, templates
   API routes: /unsubscribe, /webhooks/calcom
   armedias.com/admin gets only a LINK here (no change to that codebase)

 Off-box services (free): UptimeRobot (monitoring armedias.com + clients from outside,
   alerts → Telegram) · Cal.com hosted (book.armedias.tech via CNAME) · Google Programmable Search ·
   Hunter.io free · Gemini / Groq / OpenRouter :free LLMs
 Optional later: Render (single account) or Oracle Always-Free VM for a long-running worker
   if a job ever outgrows a GitHub Actions run.
```

**Why this split.** The VPS does only what must be stateful and always-on (Telegram, cron,
sending with pacing). Everything that burns CPU (headless Chrome, audits, search) runs on
GitHub's machines for ~1 hour a night and disappears. The database and dashboard are managed
services close to Aryan (Mumbai) and on a global edge. armedias.com never shares a browser,
a disk or a public port with ARVIS, and a compromised worker cannot reach the VPS.

## Hard rules (apply to every skill, every worker, every day)

**Legal / reputation**
- Strictly legal. Nothing that could harm the AR Medias name.
- No LinkedIn scraping or automation. No logged-in Instagram automation. Not even with
  separate accounts. No CAPTCHA solving, no proxies, no "stealth" browsers, no bot-detection
  evasion of any kind. See `docs/instagram-and-linkedin.md`.
- One account per service, used within its terms. No multi-account free-tier stacking.
- Email lookup only from: the business's own public website, Google Maps listings, public
  search (Google Programmable Search (free, 100 queries/day)), Hunter.io free tier. Verified with self-hosted Reacher.
- B2B targets only. Never consumer / personal addresses.
- CAN-SPAM / CASL compliant: real postal address in every email, working unsubscribe,
  honest subject and from-name, unsubscribes honoured immediately and forever.
- Cold email goes out from **connect@armedias.tech** (Zoho, SPF/DKIM/DMARC per `docs/dns.md`,
  2–3 week warm-up, DMARC `p=none` first). **Never** from armedias.com.

**Quality over quantity**
- Max **50 emails/day total** at first, grown slowly and only when reply rate holds.
- Every lead gets `fit_score`, `ticket_score` (reviews, rating, runs ads, site problems)
  and `contact_quality` (named / generic / none). Named decision-makers first.

**Copy rules (AR Medias house rules)**
- Never state team size, hourly rates or minimum project size. Pricing is custom per client.
- Templates are written or approved by Aryan. `approved_by_aryan` must be TRUE before any
  send until he lifts the gate.

**Pacing**: random gaps, exponential backoff, small nightly batches. Continuous but slow.

**Infrastructure**
- armedias.com (PM2) is never touched, restarted or loaded. The brain is tiny and capped.
- Supabase: ARVIS's own project (Mumbai). Never the armedias.com project.
- Free tiers everywhere; the only accepted costs are the Zoho mailbox and, if free LLMs
  rate-limit, ~$10/mo of an OpenRouter paid model.
- Aryan runs every VPS command himself. Claude never gets SSH access.

## Repository layout

```
README.md                    this file
.env.example                 every key, where to get it free
vps/01-create-user.sh        arvis user, /opt/arvis, slice caps, swapfile
vps/02-install-docker.sh     docker daemon.json (cgroup parent, log caps); docker already installed
vps/03-install-hermes.sh     Hermes install + Telegram gateway, as arvis
vps/04-install-brain.sh      venv + arvisctl (the brain's Supabase/GitHub hands) + daily-report cron
brain/arvisctl.py            stats · leads · markets · runs · dispatch · report (reads /opt/arvis/.env)
docker/docker-compose.yml    reacher only
supabase/schema.sql          all tables (run once in the Supabase SQL editor)
workers/                     Python workers run by GitHub Actions (scrape, audit, enrich)
.github/workflows/           nightly schedules + manual dispatch for each worker
hermes/skills/*/SKILL.md     one skill per department (the brain's playbooks)
hermes/cron.md               schedule for each skill
dashboard/                   Next.js app for Vercel (Phase 7); README with setup
docs/dns.md                  every DNS record: arvis., book., mail. subdomains
docs/instagram-and-linkedin.md  why no IG/LinkedIn automation, what we do instead
```

## Phase plan

| Phase | What | Gate (Aryan's proof) |
|---|---|---|
| 0 | This scaffold, pushed to GitHub | branch on GitHub |
| 1 | Supabase project (Mumbai) + schema; pause trezuh; `vps/01`→`03`; BotFather; Hermes answers on Telegram | pasted outputs + Telegram screenshot |
| 1b | In parallel: Zoho on armedias.tech (connect@), SPF/DKIM/DMARC, warm-up starts | DNS checks pass |
| 2 | GitHub Actions `scrape` worker → Supabase; brain dispatches it; `daily-report` on Telegram | rows in Supabase + report screenshot |
| 3 | `audit` + `enrich` workers, Reacher on VPS, UptimeRobot, Cal.com hosted on book. | rows + booking page loads |
| 4 | `draft-email` with approval gate on Telegram | approved drafts in Supabase |
| 5 | Warm-up done → `send-sequence` live, 50/day cap, follow-ups, unsubscribe endpoint | first replies reported |
| 6 | `inbox-triage`, `booking-brief` | booked meeting with brief |
| 7 | Vercel dashboard at arvis.armedias.tech, link from armedias.com/admin | dashboard screenshot |

Each phase starts only after the previous one is confirmed by pasted output or screenshot.
