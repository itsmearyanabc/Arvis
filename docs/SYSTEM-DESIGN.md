# ARVIS — system design v2 (2026-11-19)

Status: **approved 2026-11-19.** Phase A (guard) and B (AI layer) built and tested locally; rollout via `vps/10-update-ai-and-guard.sh`. C–E pending.

## 1. What ARVIS is for

AR Medias (armedias.com, New Delhi, founder-led) builds websites, mobile apps, e-commerce, CRM/ERP,
custom software and AI automation, plus maintenance, for businesses in India, UAE, USA, Canada,
Australia, Japan, China and Russia. 200+ projects. Positioning on the site: one team for every layer,
founder-led, fixed written scope, client owns everything, works in the client's time zone, fast + SEO built in.

ARVIS's job: do everything except the sales call.
1. Find businesses that need what AR Medias sells (outbound).
2. Catch every enquiry from armedias.com instantly and prepare Aryan for it (inbound).
3. Keep Aryan informed on Telegram and in one panel; never embarrass the brand.

## 2. As built today

```
                     Telegram (@Arvis_si_bot)          arvis.armedias.com (dashboard)
                              │                                    │ Cloudflare proxy
 Hostinger VPS (1 vCPU, 3.8 GB) — shared with armedias.com, camel, originx-*
 ┌────────────────────────────┴────────────────────────────────────┴───────────────┐
 │ user "arvis", capped: CPU 40 %, RAM 1 GB (+ Reacher 256 MB), CPU weight 50        │
 │  Hermes gateway ──► arvis-router :8090 ──► free LLMs (Gemini, Groq, …)            │
 │       │  skills + arvisctl (reads/writes Supabase, starts GitHub jobs)            │
 │  dashboard :3100 (Next.js, pre-built on GitHub)     Reacher :8081 (email verify)  │
 │  Hermes cron: 06:30 verify · 08:30 report · hourly dashboard update               │
 └───────────────────────────────────────────────────────────────────────────────────┘
          │ dispatch                                   ▲ read/write
          ▼                                            │
 GitHub Actions (free, public repo)               Supabase (Mumbai)        Google Sheet
  02:00 scrape (Maps, 3 markets) ─────────────────► leads, markets, … ───► "Arvis Data"
  04:30 audit (Playwright) · 05:30 enrich · dashboard build                (one tab per market)
```

What is good and stays: heavy work never runs on the VPS; Supabase is the single source of truth;
owner-only database access; noindex dashboard behind Cloudflare; approval before any email.

## 3. Problems found (and status)

| # | Problem | Evidence | Status |
|---|---|---|---|
| 1 | Nightly "scrape" emails you a failure | 10 failed runs since 15 Nov; scraping succeeded, only the Sheet copy failed: the GOOGLE_SHEET_ID secret holds the id twice | **Fixed + proven** (runs 44388294557 → 44389244508 green, rows in Sheet) |
| 2 | Rate limits while chatting | free tiers; router only reacts after a 429; chat and background jobs share one queue | design §5 |
| 3 | ARVIS only sells "websites" | audit looks only at site problems; niches/countries don't match armedias.com | design §6 |
| 4 | No link to the website's enquiries | form goes to info@ only | design §7 |
| 5 | "Must never slow armedias.com" relies on static caps only | 40 % CPU cap, no reaction if the site is slow | design §4 |

## 4. VPS protection (hard guarantee)

Rule: **the VPS runs only always-on, lightweight services. Anything heavy runs on GitHub's machines.**

| On the VPS (light) | Memory | CPU when idle |
|---|---|---|
| Hermes gateway | 200–450 MB | ~0 (waits for Telegram) |
| arvis-router | ~60 MB | ~0 |
| dashboard (Node) | ~100–150 MB, cap 300 MB | 0 unless you open it |
| Reacher (Docker) | cap 256 MB | short bursts, 60 checks/night |
| **Total ARVIS ceiling** | **1 GB + 256 MB** (kernel-enforced) | **40 % of 1 vCPU** (kernel-enforced) |

New: **website guard** (root systemd timer, every 30 s, a few ms of CPU):
- measures armedias.com's local response time and the machine's load;
- if the site answers slower than 800 ms or load > 0.8: drops ARVIS to **CPU 10 %** and pauses
  non-urgent ARVIS jobs; restores 40 % after 5 calm minutes;
- logs every throttle to the brain log so you can see it in the dashboard.

Never on the VPS: builds, browsers/Playwright, scraping, bulk crawling, local AI models (Ollama).

## 5. AI layer: smart and not rate-limited (free, no card)

1. **Two lanes.** *Conversation* (you on Telegram) always goes first and gets the strongest model with
   room. *Background* (reports, verification, drafting batches) waits its turn and uses lighter models.
   A background job can never make your chat hit a limit.
2. **Budget before calling.** The router tracks each provider's requests and tokens per minute and per
   day against its published free limits and picks one that has room, instead of waiting for a 429.
3. **More free capacity.** Every Gemini model has its own free quota, so the same key gives several
   separate buckets (3.8 Flash, 2.5 Flash, Flash-Lite variants). Added: **Cloudflare Workers AI** (you
   already have the account; Llama 3.3 70B and others, daily free allowance), **GitHub Models** (GPT-4.1,
   free with your GitHub account; needs one token permission). Groq stays for short requests,
   OpenRouter free as last resort.
4. **Smaller requests.** Hermes sends 21 tool definitions with every message; ARVIS needs ~6. Trimming
   tools and old history roughly halves tokens per message, so every free quota lasts twice as long.
5. **Quality floor.** Writing emails and research use only the strongest models (Gemini 3.8 Flash,
   GPT-4.1); tiny models are allowed only for sorting/classifying.

Honest limit: free models are good but not Claude-level, and quotas are per day. If you ever want
"never think about it", one switch adds a paid model as the last fallback (off by default).

## 6. Business brain: sell everything AR Medias does

- **Business profile skill** built from armedias.com: services, industries, countries, positioning,
  proof (200+ projects, founder-led, you own everything), house rules (no prices/rates/team size/minimums).
- **Service matcher** per business, from what ARVIS measured:

| Signal found | Lead with | Angle |
|---|---|---|
| no website | Website Development | they're invisible to people searching |
| slow / outdated / no SSL | Website rebuild + speed + SEO | measured speed / year / SSL |
| no online booking or enquiry form, many reviews | booking system / custom software | busy business losing enquiries |
| runs Meta/Google ads, weak site | conversion-focused rebuild | paying for traffic the site loses |
| shop on Shopify/Wix, growing reviews | E-commerce / custom store | scaling past the template |
| multi-location / large team signals | CRM or ERP | systems for growing operations |
| repetitive enquiries (FAQ-heavy, phone-only) | AI & workflow automation | AI receptionist / auto-replies |

- **Markets aligned to your site**: industries = Real estate, Healthcare, Education, Retail & e-commerce,
  plus local services that buy websites; countries = India, UAE, USA, Canada, Australia first.
- Each business row gets `best_service`, `angle`, and the evidence, visible in the dashboard and Sheet.

## 7. Website connection (armedias.com ⇄ ARVIS)

1. **Inbound enquiries.** When the armedias.com contact form is saved, the website server also sends
   the enquiry to `arvis.armedias.com/api/inbound` (signed, 2-second timeout, fire-and-forget, after the
   form's own handling, so visitors never wait). ARVIS then, within a minute:
   Telegram alert → researches the company (site audit, size signals) → drafts a reply for your approval
   → shows it in the dashboard's Inbound page.
2. **/admin button** to the ARVIS dashboard. Nothing else in the website changes.
Both website changes are made in the website's own session; ARVIS never edits armedias.com code.

## 8. Reliability and noise

- Secondary steps (Sheet copy) can never fail a run; real failures alert once on Telegram, not by email.
- Morning report adds a health line: last night's runs, throttles, AI provider usage.
- Public repo keeps GitHub Actions free and unlimited (a private repo would cap at 2,000 min/month).

## 9. Delivery plan (each phase ends with a test you can see)

| Phase | Build | Acceptance test |
|---|---|---|
| A | website guard + VPS update | guard log shows readings; armedias.com response unchanged — **built; 8/8 simulated scenarios pass** |
| B | AI lanes, budgets, new providers, tool trim | 30 Telegram messages in 10 min with 0 failures; AI page shows spread — **built; local: cold start 39 s→14 s, 20/20 burst, 2 lanes, hedging; tool list logged for the trim** |
| C | business profile + service matcher + market realignment | every business shows best service + angle |
| D | inbound from armedias.com | test enquiry → Telegram alert + brief within 60 s |
| E | email (after Zoho + warm-up) | mail-tester ≥ 9/10, first approved send |

## 10. Decisions needed from Aryan

1. Approve this design (or change parts).
2. Which 2–3 services should outbound lead with? (default: Website Development, AI automation, CRM)
3. Which countries first? (default: UAE, USA, Canada, Australia, India)
4. Yes/no: send website enquiries to ARVIS (§7)?
5. Two free keys: Cloudflare Workers AI API token; GitHub token with "Models: Read".
