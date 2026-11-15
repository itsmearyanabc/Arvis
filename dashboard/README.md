# ARVIS dashboard — Next.js 15 on Vercel, arvis.armedias.tech

The operating panel: see everything ARVIS has in Supabase, with a live "brain log" and a
neural-network header that reacts to activity. Single user (Aryan), Supabase Auth
email+password. RLS in `supabase/schema.sql` gives `authenticated` full access and `anon`
nothing, so the browser only ever holds the publishable key.

**It never scrapes, sends email or calls third parties.** Workers run on GitHub Actions, the
brain on the VPS; this app reads and edits ARVIS's own database. armedias.com/admin will only
link here.

## Pages
| Route | What |
|---|---|
| `/` Today | Tiles (leads, with email, named, new 24h, markets scraped/active, runs ok/failed), leads-per-day for 30 days, per-group table, latest worker runs, brain animation |
| `/leads` | Server-side paginated table (50/page). Filters: group, niche, market, has email, contact quality, status, min ticket score, business-name search. Columns: score, quality, email + source, website, phone, Instagram, status, Google Maps link. Click a row → drawer with the full lead, audits and contacts |
| `/markets` | All markets with group, status, lead count, last scraped; Pause/Activate toggle; "Add a market" form (country, city, niche from the six groups) → inserts into `markets` with the same `mk_<cc>_<city>_<niche>` id as `seed_markets.py` |
| `/runs` | `worker_runs` (last 100: worker, status, input, counts, error, duration) and the live brain log: `brain_events` streamed over Supabase Realtime, filter by source, follow mode |
| `/settings` | Which env vars and integrations are configured (flags only, never values) |
| `/login` | Supabase Auth email+password |

Header + Today page: `components/BrainCanvas.tsx`, plain canvas + `requestAnimationFrame`.
Five hub nodes = sources (brain, scrape, audit, mirror, telegram). Pulse rate scales with
`brain_events` in the last 10 minutes; a hub glows for 60 s after its source logs; idle state
breathes slowly. No chart or animation libraries.

## API routes (server-side, service key)
- `GET /api/unsubscribe?token=<sequence_id>.<hmac_sha256_hex(sequence_id, UNSUBSCRIBE_SECRET)>`
  → verifies the token, upserts `unsubscribes` (email + domain, reason `request`), sets the
  sequence to `stopped_unsub` and the lead to `unsubscribed`, shows a plain confirmation page.
  Token helper: `lib/unsubscribe.ts` (`makeUnsubscribeToken`). The brain must use the same
  `UNSUBSCRIBE_SECRET` when it builds links (Phase 3).
- `POST /api/webhooks/calcom` → stub for Phase 4. Upserts `bookings` on `calcom_uid`, links the
  lead by attendee email, verifies `x-cal-signature-256` when `CALCOM_WEBHOOK_SECRET` is set.

## Brain log plumbing
- `supabase/migrations_002_brain_events.sql` creates `brain_events` (id, ts, source, level,
  message, data), RLS, and adds it to the `supabase_realtime` publication. Run it once in the
  SQL editor; until then the Runs page says "table missing" and the animation stays idle.
- `workers/common/events.py` → `log_event(source, level, message, data)`; never raises.
  Called from `workers/scrape/upload.py` (start/finish) and `brain/arvisctl.py` (every command).

## Local development
```bash
cd dashboard && npm install
cp .env.example .env.local   # fill from the repo-root .env (SUPABASE_URL / ANON / SERVICE keys)
npm run dev                  # http://localhost:3000
npm run build                # must pass before pushing
```
Create your login once: Supabase → Authentication → Users → **Add user** → email + password,
tick "Auto confirm". (Or `node scripts/create-user.mjs you@example.com` with `.env.local` set;
it prompts for the password.)

## Deploy to Vercel (one time)
1. vercel.com → **Add New → Project** → import `itsmearyanabc/Arvis`.
2. **Root Directory**: `dashboard` (Edit → pick the folder). Framework preset: Next.js. Leave
   build command `next build`.
3. **Environment Variables** (Production + Preview), values from the repo-root `.env`:
   - `NEXT_PUBLIC_SUPABASE_URL` = `SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = `SUPABASE_ANON_KEY` (publishable key)
   - `SUPABASE_SERVICE_KEY` = `SUPABASE_SERVICE_KEY` (secret key, server only)
   - `UNSUBSCRIBE_SECRET` = `openssl rand -hex 24`
   - `NEXT_PUBLIC_SITE_URL` = `https://arvis.armedias.tech`
   - optional later: `CALCOM_WEBHOOK_SECRET`
4. Deploy. First deploy gives `<project>.vercel.app`; log in there to check.
5. **Domain**: Project → Settings → Domains → add `arvis.armedias.tech`. At Hostinger (DNS for
   armedias.tech) add `CNAME  arvis  →  cname.vercel-dns.com` (TTL 3600). Vercel issues the
   certificate once DNS resolves (minutes to an hour).
6. Supabase → Authentication → URL Configuration → Site URL `https://arvis.armedias.tech`.
7. armedias.com/admin: one link `<a href="https://arvis.armedias.tech">ARVIS</a>`, nothing else.

Every push to `main` that touches `dashboard/` redeploys automatically. Vercel's free tier is
enough: the app is server-rendered on demand with no cron and no outbound calls.

## Layout
```
app/(app)/            authenticated pages (layout = header + nav + brain)
app/login, app/auth   sign in / sign out
app/api/              unsubscribe + calcom webhook (service key)
components/           BrainCanvas, BrainLog, LeadsTable (+drawer), AddMarketForm, Tile, BarChart, StatusPill, Nav
lib/supabase/         browser / server / admin clients, middleware session refresh
lib/niches.ts         mirror of workers/common/niches.py (keep in sync)
lib/unsubscribe.ts    HMAC token helpers
```
