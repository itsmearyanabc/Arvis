---
name: daily-report
description: Send Aryan the daily ARVIS report on Telegram at 08:30 (scraped / audited / verified / drafts awaiting approval / sent / replied / booked, with reply and booking rate) and a longer weekly report on Monday. Use on schedule or when Aryan says "report".
---

# daily-report

## Purpose
One message a day that tells Aryan what ARVIS did, what needs him, and whether the funnel is
healthy. No open rates, no vanity metrics.

## Inputs
All tables in `supabase/schema.sql`, `worker_runs`, UptimeRobot, the Hermes
cron log (failed jobs), free-tier quota usage (Brave, Hunter, Gemini, Groq, OpenRouter).

## Daily message (≤ 20 lines)
```
ARVIS daily — Thu 20 Nov
Scraped 118 (dentists Toronto) · Audited 40 · Verified 22 (named 9)
Drafts awaiting approval: 17  → reply "approve all" or "review"
Sent 31/50 (step1 18, fu 13) · Bounced 0 · Unsub 1
Replied 3 (interested 1, not_now 1, no 1) · Reply rate 7d: 4.1%
Booked 1 (Fri 11:00, Smile Dental) · Booking rate 7d: 1.2%
Mailboxes: m1 18/20 ok · m2 warming until 29 Nov
Monitors: all up · armedias.com 212 ms
Quota: Brave 41% · Hunter 12/25 · Gemini ok · Groq fallback used 2×
Issues: scraper job 2 failed (timeout) — retried ok
Needs you: 17 approvals · 1 interested reply (Smile Dental) · 1 brief tonight
```
Rates = replies ÷ step-1 sends in the last 7 days; bookings ÷ step-1 sends. Always show the
denominator somewhere.

## Weekly message (Monday 08:30, ≤ 40 lines)
Per-market funnel table (scraped → verified → sent → replied → booked), best/worst template by
reply rate, best niche, cap recommendation (only ever "hold" or "+10" per rules in
`send-sequence`), unsubscribe/bounce trend, uptime worst 3, quota forecast, and 3 suggested
next markets from `market-research`.

## Procedure
1. Pull counts for yesterday (local tz) and trailing 7 days from Supabase.
2. Compose with the template above; omit sections with nothing to say.
3. Send to Aryan's Telegram id. If Supabase is unreachable, send a one-line failure note instead.

## Outputs
Telegram message; a row in **Reports** (`date, scraped, audited, verified, drafts_pending,
sent, bounced, unsub, replied, interested, booked, reply_rate_7d, booking_rate_7d, issues`).

## Rate limits
- One daily, one weekly, plus on-demand. Never more than 3 unsolicited messages/day from this
  skill (alerts from other skills are separate).

## Never do
- Never report open rates or tracking-pixel data; none is collected.
- Never pad numbers or hide failures. Failed jobs are listed.
- Never send the report to anyone but Aryan's Telegram id.
