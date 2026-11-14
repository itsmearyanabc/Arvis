---
name: draft-email
description: Fill one of Aryan's approved cold-email templates with the lead's real audit findings and queue it for approval. Use for Leads with status=verified, or when Aryan says "draft for <business>". Never invents pricing, team size, hourly rates or minimum project size.
---

# draft-email

## Purpose
Produce a short, specific, honest first email + 2 follow-ups for a verified lead, from a template
Aryan has approved, personalised only with facts ARVIS actually measured. Nothing goes out until
`approved_by_aryan=TRUE` (while `REQUIRE_APPROVAL=true`).

## Inputs
- **Leads** with `status=verified`, `contact_quality` in (`named`, `generic`), batch ≤ 25/run,
  highest `ticket_score` first, round-robin across active markets.
- **Templates** table: rows with `approved=TRUE`. Each template has `step` (1, 2, 3), `subject`,
  `body` with placeholders `{first_name|there}`, `{business}`, `{city}`, `{top_issue}`,
  `{audit_summary}`, `{proof_point}`, `{sender_name}`, `{booking_link}`, `{postal_address}`,
  `{unsubscribe_link}`.
- **Audits** row for the lead (for `{top_issue}`, `{audit_summary}`).

## Procedure
1. Choose template set by niche if one exists, else `default`.
2. Fill placeholders. `{top_issue}` must come from the Audits row verbatim-ish; if the audit has
   no issue, use the `no_issue` template variant (compliment + one question), never make one up.
3. Subject: ≤ 6 words, honest, no "RE:", no fake urgency, no ALL CAPS, no emojis.
4. Body: ≤ 120 words for step 1, ≤ 60 for steps 2–3. One ask: a 15-min call via `{booking_link}`.
5. Footer (mandatory, from `.env`): sender real name, AR Medias, `{postal_address}`, plain
   "Reply STOP or click here to unsubscribe" with `{unsubscribe_link}`.
6. Run the house-rules check (below). If it fails, fix or discard; log why.
7. Write **Sequences** row: `sequence_id, lead_id, contact_email, mailbox, step1_subject,
   step1_body, step2_body, step3_body, status=draft, approved_by_aryan=FALSE, drafted_at`.
8. Post a Telegram digest: "N drafts ready. Reply `approve <ids>` / `approve all` / `edit <id>:
   <note>` / `skip <id>`." Aryan's `approve` sets `approved_by_aryan=TRUE`, `approved_at`.

## House-rules check (hard fail if any triggers)
- Mentions team size, headcount, "our team of N", hourly rate, day rate, "starting at",
  "from $", minimum project, "budget of at least".
- Any claim not traceable to the Audits row or the approved template text.
- Any pricing number at all. Pricing is custom per client; say so only if asked.
- Missing postal address or unsubscribe line.
- From-domain is armedias.com (must be a `SEND_DOMAIN` mailbox).

## Outputs (Sequences table) — see `supabase/schema.sql`.

## Rate limits
- ≤ 25 drafts per run, one run per day. Drafts older than 14 days without approval expire
  (`status=expired`) so stale audits are never sent.

## Never do
- Never send. This skill only drafts.
- Never invent facts, pricing, team size, rates, minimums, client names or results.
- Never use a template that is not `approved=TRUE`.
- Never draft to `contact_quality=none`, to consumer addresses, or to anyone in **Unsubscribes**.
- Never draft twice to the same domain within 90 days.
