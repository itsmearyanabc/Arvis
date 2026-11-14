# ARVIS dashboard (Phase 7) — Next.js on Vercel, arvis.armedias.tech

Not built yet. This folder will hold a small Next.js (App Router) app:

- **Auth**: Supabase Auth, email+password, a single user (Aryan). RLS in `supabase/schema.sql`
  gives authenticated users full access and anon nothing.
- **Pages**: Leads (filter by market/status/score), Lead detail (audit, contacts, thread),
  Approvals (drafts awaiting `approved_by_aryan`, approve/edit/skip), Templates (edit +
  approve), Funnel (per-market scraped → verified → sent → replied → booked), Markets
  (activate/pause), Settings (caps, mailboxes).
- **API routes** (serverless, service key server-side only):
  - `GET /api/unsubscribe?token=` → adds email+domain to `unsubscribes`, stops sequences,
    shows a plain confirmation page. Token = HMAC of sequence_id.
  - `POST /api/webhooks/calcom` → inserts/updates `bookings`, pings the brain (Telegram via
    Hermes webhook or a `worker_runs` row the brain polls).
- **Link from armedias.com/admin**: a single `<a href="https://arvis.armedias.tech">` — no
  other change to that codebase.

Setup when the phase comes: `npx create-next-app@latest dashboard --ts --app`, add
`@supabase/supabase-js` and `@supabase/ssr`, import to Vercel with root directory `dashboard`,
env vars from `.env.example` (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY,
SUPABASE_SERVICE_KEY, UNSUBSCRIBE_SECRET), add the domain per `docs/dns.md`.
