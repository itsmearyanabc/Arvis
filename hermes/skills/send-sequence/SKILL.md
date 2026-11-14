---
name: send-sequence
description: Send approved cold-email sequences (step 1 + up to 2 follow-ups) from the warmed-up connect@armedias.tech Zoho mailbox, with a hard 50/day cap, per-mailbox caps, random gaps, stop-on-reply and unsubscribe handling. Use on the daily send schedule only.
---

# send-sequence

## Purpose
The only skill that sends email. It is deliberately slow, capped and boring.

## Inputs
- **Sequences** rows with `approved_by_aryan=TRUE` (unless `REQUIRE_APPROVAL=false`) and
  `status` in (`approved`, `step1_sent`, `step2_sent`) whose next step is due.
- Mailboxes from `.env` (`MAILBOX_n_*`), each with `DAILY_CAP` (start 20) and `warmup_until`
  date in the **Mailboxes** tab; a mailbox before `warmup_until` sends 0 cold emails.
- `DAILY_SEND_CAP` (global, start 50), `POSTAL_ADDRESS`, `SEND_DOMAIN`.
- **Unsubscribes** and **Replies** tabs (stop conditions).

## Sequence timing
- Step 1: day 0. Step 2: day 3–4 (random). Step 3: day 8–10 (random). Then `status=done_no_reply`.
- Send window: 09:00–16:30 in the **lead's** local time zone, Mon–Thu only (Fri before noon ok).
- Follow-ups go in the same thread (`In-Reply-To` / `References` of step 1).

## Procedure (one run per hour inside the window)
1. Refresh stop lists: any `lead_id` with a row in **Replies** (any category) or whose email /
   domain is in **Unsubscribes** → `status=stopped_reply` / `stopped_unsub`. Skip them.
2. Compute remaining budget: `min(DAILY_SEND_CAP − sent_today, Σ mailbox remaining caps)`.
   Also cap this run at `ceil(budget / hours_left_in_window)` so sends spread across the day.
3. Pick due rows: follow-ups first (they are cheap and warm), then new step-1s, highest
   `ticket_score` first, max 1 email per recipient domain per day, round-robin mailboxes.
4. For each: final house-rules check (same list as `draft-email`), ensure footer has postal
   address + unsubscribe link, add `List-Unsubscribe` and `List-Unsubscribe-Post` headers.
5. Send via Zoho SMTP (TLS, port 465). Random gap 90–420 s between sends. On SMTP 4xx: back off
   ×2 (max 30 min) and retry ≤ 3. On 5xx: mark `bounced`, add to **Unsubscribes** (reason
   `bounce`), never retry.
6. Update **Sequences**: `stepN_sent_at`, `status`, `mailbox`, `message_id`.
7. Bounce guard: if bounces ≥ 5% of today's sends, or any spam-complaint reply, **stop all
   sending**, set `Mailboxes.paused=TRUE`, alert Aryan on Telegram.

## Outputs
**Sequences** updates; counters for `daily-report`: sent (by step), bounced, stopped.

## Rate limits (hard)
- Global ≤ `DAILY_SEND_CAP` (50) per day across all mailboxes. Raise only by Aryan, ≤ +10/week,
  only if reply rate ≥ 3% and bounce rate < 2% for the previous 7 days.
- Per mailbox ≤ `MAILBOX_n_DAILY_CAP` (20 start → 40 max). 0 before `warmup_until`.
- Per recipient domain ≤ 1/day, ≤ 3 lifetime without a reply.
- Random 90–420 s between sends. Never bursts.

## Never do
- Never send from armedias.com. Only `SEND_DOMAIN` (armedias.tech) Zoho mailboxes listed in `mailboxes`.
- Never send without `approved_by_aryan=TRUE` while `REQUIRE_APPROVAL=true`.
- Never send to anyone who replied, unsubscribed, bounced, or to consumer addresses.
- Never send step 2/3 if the thread has any reply (even an auto-reply → park for 7 days).
- Never exceed caps "just this once". Never send on weekends or outside the window.
- Never use open-tracking pixels or link cloaking. Reply and booking are the only metrics.
- Never change subject lines or copy from the approved draft.
