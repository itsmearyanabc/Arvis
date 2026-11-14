# enrich worker (Phase 3)

Finds a named decision-maker email for `status=audited` leads from public sources only
(business website pages, Brave Search API snippets, Hunter.io free tier for ticket_score ≥ 70),
then asks the brain to verify candidates through Reacher on the VPS (`POST /v0/check_email`,
reachable only from the VPS, so the worker writes candidates to `contacts` with
`email_status=unknown` and the brain's `enrich-verify` skill verifies them).
Rules and procedure: `hermes/skills/enrich-verify/SKILL.md`. Script lands in Phase 3.
