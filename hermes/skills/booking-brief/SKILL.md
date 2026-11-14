---
name: booking-brief
description: When a meeting is booked on book.armedias.tech (Cal.com webhook or calendar poll), build a one-page brief for Aryan from everything ARVIS already knows about the lead, and send it to Telegram the evening before and 1 hour before the call. Use on booking events and on the daily 18:00 check.
---

# booking-brief

## Purpose
Aryan walks into every call already knowing the business, its site problems, its ad activity and
the exact email thread that got them there.

## Inputs
- Cal.com (`CALCOM_URL`, `CALCOM_API_KEY`): new bookings (webhook `BOOKING_CREATED`, or poll
  `/bookings` every 15 min as a fallback), reschedules and cancellations.
- Match attendee email → **Contacts** → **Leads**, **Audits**, **Sequences**, **Replies**.
  Unmatched attendee (referral or inbound) → brief from public website + Maps only.

## Procedure
1. On booking: write **Bookings** row (`booking_id, lead_id, attendee_name, attendee_email,
   start_at, tz, status=booked, source (cold_email|referral|inbound), calcom_uid`).
2. Build the brief (≤ 250 words):
   - Who: business, city, niche, decision-maker name/role, phone, rating/reviews.
   - Website: `audit_summary` + top 3 issues, CMS, copyright year.
   - Signals: runs Meta ads, `ticket_score`, `fit_score`.
   - Thread: the email they replied to, their reply, `reply_summary`.
   - Suggested angle: 2 bullets, drawn only from the facts above.
   - Links: website, Maps, Instagram/LinkedIn URLs for Aryan to open himself.
3. Telegram: immediately on booking ("Booked: X, Tue 14:00"), the full brief at 18:00 the day
   before, and a 1-hour reminder with the brief again.
4. After `start_at` + 2 h, ask Aryan on Telegram: `won / proposal / lost / no-show / reschedule`
   and store the answer in `Bookings.outcome`.

## Outputs (Bookings table) — see `supabase/schema.sql`.

## Rate limits
- Poll Cal.com ≤ every 15 min. One brief per booking per trigger.

## Never do
- Never contact the attendee by itself (no confirmation emails beyond Cal.com's own).
- Never put pricing, team size or rates in the brief's "suggested angle".
- Never visit Instagram/LinkedIn; link only.
- Never touch armedias.com's calendar or mailboxes.
