---
name: monitor-site
description: Watch uptime, SSL expiry and response time for armedias.com, armedias.tech subdomains and client sites via UptimeRobot (free, off-box) and alert Aryan on Telegram. Use for weekly stats and in the daily report.
---

# monitor-site

## Purpose
Know before a client does. ARVIS shares armedias.com's VPS, so monitoring must come from
outside: UptimeRobot's free plan (50 monitors, 5-min checks) does the checking and posts
alerts straight to the ARVIS Telegram bot; this skill creates monitors and reads stats.

## Inputs
- UptimeRobot API (`UPTIMEROBOT_API_KEY`), monitors created once from the **Monitors** table:
  `url, type (http|keyword|ping), interval_s (300 default), keyword, owner (us|client:<name>)`.
- UptimeRobot's Telegram alert contact points at the ARVIS bot so alerts arrive even if Hermes
  is down.

## Procedure
1. Sync: for each **Monitors** row without `monitor_ext_id`, create the monitor via the
   UptimeRobot API (HTTP, 5-min interval, SSL expiry alerts on). Store `monitor_ext_id`.
2. On DOWN (after retries): Telegram alert with URL, status code, since-when. On UP: recovery
   message with downtime length.
3. Weekly: write uptime % and avg response time per monitor into **Monitors**; include the
   worst 3 in the weekly report. A client site with < 99.5% uptime or > 3 s avg is a natural
   upsell note for Aryan (hosting / performance project).
4. Also record our own: `arvis.armedias.tech`, `book.armedias.tech`, the cold `SEND_DOMAIN`
   landing page, and the ARVIS VPS itself.

## Outputs (Monitors table)
`monitor_id, monitor_ext_id, name, url, type, interval_s, owner, status, last_down_at,
uptime_7d_pct, avg_response_ms, ssl_expires_at, created_at`

## Rate limits
- Checks ≥ 5 min apart per site (armedias.com: 5 min, clients: 10 min). Never more often.
- Keyword checks fetch one page only.

## Never do
- Never load-test anything. One GET per interval.
- Never restart, deploy or SSH into anything. Alert only; Aryan acts.
- Never monitor sites we do not own or have a client relationship with.
