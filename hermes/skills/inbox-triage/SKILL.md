---
name: inbox-triage
description: Read replies arriving in the cold-email mailboxes (IMAP), classify each one, stop sequences, process unsubscribes, and alert Aryan immediately for interested replies. Use every 30 minutes during business hours.
---

# inbox-triage

## Purpose
Make sure no interested reply waits, no "stop" is ignored, and no follow-up goes to someone who
already answered.

## Inputs
- IMAP for every mailbox in `.env` (`ZOHO_IMAP_*`, `MAILBOX_n_*`), folder INBOX, unseen only.
- **Sequences** (match by `In-Reply-To` / `References` / sender email) and **Contacts**.

## Categories
`interested` · `question` · `not_now` (asks to follow up later, with a date if given) ·
`not_interested` · `unsubscribe` (STOP, remove, unsubscribe, do not contact) · `auto_reply`
(OOO, auto-responder) · `bounce` · `wrong_person` (gives another contact) · `spam_complaint`
(angry / threatens to report) · `other`.

## Procedure
1. Fetch unseen messages (≤ 100/run). Match to a sequence; unmatched → `other`, keep.
2. Classify with the LLM using subject + first 1,500 chars. Store `reply_summary` (≤ 25 words)
   and `suggested_action`.
3. Write **Replies** row; set `Sequences.status=stopped_reply` for every matched sequence
   except `auto_reply` (park 7 days) and `bounce` (mark bounced + **Unsubscribes**).
4. `unsubscribe` / `spam_complaint` / `not_interested` → add email **and domain** to
   **Unsubscribes** immediately. `spam_complaint` → also pause the mailbox and alert Aryan.
5. `interested` / `question` / `wrong_person` → Telegram alert within the same run, with the
   reply text, lead name, website, `audit_summary`, and a one-tap suggested answer **as a draft
   for Aryan**. ARVIS does not reply by itself unless Aryan has enabled `AUTO_REPLY=true` for
   that category (Phase 7, off by default).
6. `not_now` with a date → **Sequences** `status=snoozed`, `resume_at` = that date, reminder
   to Aryan the day before.
7. Mark messages seen. Never delete.

## Outputs (Replies tab)
`reply_id, sequence_id, lead_id, mailbox, from_email, received_at, category, reply_summary,
suggested_action, telegram_alerted, handled_by_aryan, handled_at`

## Rate limits
- IMAP poll every 30 min 08:00–20:00, hourly otherwise. ≤ 100 messages per run.

## Never do
- Never auto-reply to anyone without the explicit `AUTO_REPLY` flag for that category.
- Never ignore or "reinterpret" an unsubscribe; any plausible opt-out counts.
- Never delete mail. Never move Aryan's personal/armedias.com mail; these mailboxes are the cold
  domain's only.
- Never forward reply content anywhere except Aryan's Telegram and the Sheet.
