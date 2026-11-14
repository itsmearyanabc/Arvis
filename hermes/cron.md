# ARVIS cron schedule (Hermes cron)

Times are the VPS local time zone (check with `timedatectl`); the report should land at 08:30
Aryan's time. Shared 1 vCPU box with armedias.com: heavy jobs (scraper, audits) run only in the
02:00–06:30 window when the site is quietest, and the scraper container is started and stopped
by its job so it holds no RAM during the day.

| When | Skill | Notes |
|---|---|---|
| `0 2 * * *` | scrape-leads | nightly; `docker compose --profile scrape up -d scraper` → 1 job, 1 browser, ≤ 100 new leads → `stop scraper` by 05:00 |
| `0 5 * * *` | audit-website | ≤ 40 sites, after scraping |
| `30 6 * * *` | enrich-verify | ≤ 30 leads; Reacher spaced 5–15 s |
| `0 7 * * *` | draft-email | ≤ 25 drafts → Telegram "approve" digest |
| `30 8 * * *` | daily-report | daily; Monday run also sends the weekly |
| `0 9-16 * * 1-4` + `0 9-11 * * 5` | send-sequence | hourly inside the send window, cap-aware |
| `*/30 8-20 * * *` + `0 21-7 * * *` | inbox-triage | 30 min in business hours, hourly otherwise |
| `*/15 * * * *` | booking-brief (poll) | Cal.com fallback poll; webhook is instant |
| `0 18 * * *` | booking-brief (eve) | briefs for tomorrow's meetings |
| `0 8 * * 1` | monitor-site | UptimeRobot (free, off-box) does the checking and alerts Telegram directly; this job only pulls weekly stats |
| `0 9 * * 1` | market-research | weekly only if Aryan asked for "suggest markets"; otherwise on demand |
| `0 3 * * 0` | housekeeping | expire drafts > 14 d, retry parked leads > 30 d, rotate logs, backup Sheet → `/opt/arvis/data/backups` |

## Rules
- Every scheduled run adds a random 0–10 min jitter before starting.
- A skill never overlaps itself: if the previous run is still going, skip and log.
- Any skill that hits 3 consecutive failures disables its own schedule and alerts Aryan.
- Free-tier quota ≥ 80% → the skill switches to the next fallback provider or stops and reports.

## Phase gating (what is actually enabled when)
| Phase | Enabled jobs |
|---|---|
| 1 | daily-report (heartbeat only), monitor-site (our own sites) |
| 2 | + scrape-leads |
| 3 | (domains/warm-up: nothing new scheduled, warm-up runs via Zoho / warm-up tool) |
| 4 | + audit-website, enrich-verify, monitor-site (clients), booking page |
| 5 | + draft-email (approval gate on) |
| 6 | + send-sequence |
| 7 | + inbox-triage, booking-brief, market-research weekly |
