#!/usr/bin/env python3
"""arvisctl — the brain's hands. Hermes (ARVIS) runs this to read live data from Supabase and to
dispatch GitHub Actions workers. Every answer about leads/emails/markets MUST come from here, never
from memory. Reads /opt/arvis/.env (or ARVIS_ENV) for SUPABASE_URL, SUPABASE_SERVICE_KEY,
GITHUB_TOKEN, GITHUB_REPO.

Wording: rows in the `leads` table are scraped BUSINESSES (raw data) until audit/enrich/score turn
them into leads (status verified+). Speak of "businesses scraped", "records", "emails found".

  arvisctl stats                      totals: businesses scraped, with email, named/generic, last 24h, per group
  arvisctl businesses [--limit N] [--market ID] [--with-email] [--group NAME]   (alias: leads)
  arvisctl markets [--status active]  markets with record counts and last scrape
  arvisctl add-market --country C --city CITY --niche NICHE [--new-sheet | --color #HEX] [--label "task name"]
                                      seed a new market (idempotent). Sheet allocation for this TASK:
                                      --new-sheet  → its own Google Sheet (created + shared with Aryan)
                                      --color      → rows highlighted in that colour on the shared Sheet
                                      (neither → next free palette colour on the shared Sheet)
  arvisctl runs [--limit N]           recent worker runs (scrape/audit) with counts
  arvisctl dispatch scrape [--market ID | --city CITY --niche NICHE [--country C]] [--count N]
                                      start a scrape on GitHub Actions now (needs GITHUB_TOKEN); unseeded
                                      city/niche is added as a market first
  arvisctl dispatch audit [--limit N]
  arvisctl sheets                     list the Google Sheet tabs with counts + links
  arvisctl sheets-layout market|city|group   reorganise ALL tabs: per city+niche (default), per city, or per niche group
  arvisctl mirror                     push new records to the Google Sheet now
  arvisctl verify [--limit N]         verify unknown contact emails with self-hosted Reacher (5–15 s apart);
                                      marks leads verified / parked. Runs nightly 06:30 IST (Hermes cron, no LLM).
  arvisctl email draft --to ADDR --subject S --body B [--name N]   store a one-off email, print it EXACTLY
  arvisctl email send --id ID --confirm                            send it — only after Aryan said "send"
  arvisctl email check                                             DNS + mailbox readiness for sending
  arvisctl report                     the daily Telegram report text
Output is plain text meant to be pasted to Aryan; add --json for machine output."""
import os, sys, json, time, argparse, datetime as dt, collections, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "workers"))

def load_env():
    path = os.environ.get("ARVIS_ENV")
    candidates = [path] if path else ["/opt/arvis/.env", os.path.join(ROOT, ".env")]
    for p in candidates:
        if p and os.path.exists(p):
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break
load_env()
from common.db import db, now_iso
from common.niches import group_of, GROUPS, normalize_niche, normalize_country
from common.events import log_event

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
def now(): return dt.datetime.now(dt.timezone.utc)
def ago(h): return (now() - dt.timedelta(hours=h)).isoformat()

def count(table, **filters):
    q = db().table(table).select("lead_id" if table == "leads" else "*", count="exact", head=True)
    for k, v in filters.items():
        if v is None: q = q.is_(k, None)
        elif isinstance(v, tuple): q = getattr(q, v[0])(k, v[1])
        else: q = q.eq(k, v)
    return q.execute().count or 0

def cmd_stats(a):
    total = count("leads"); with_email = count("leads", primary_email=("neq", ""))  # neq also excludes nulls
    named = count("leads", contact_quality="named"); generic = count("leads", contact_quality="generic")
    last24 = count("leads", scraped_at=("gte", ago(24))); last24_email = len([r for r in db().table("leads").select("lead_id").gte("scraped_at", ago(24)).neq("primary_email", "").execute().data])
    rows = db().table("leads").select("niche,city,primary_email").execute().data
    by_group = collections.Counter(group_of(r["niche"]) for r in rows)
    by_group_email = collections.Counter(group_of(r["niche"]) for r in rows if r["primary_email"])
    markets_active = count("markets", status="active"); markets_done = count("markets", last_scraped_at=("neq", "1970-01-01"))
    out = {"leads_total": total, "leads_with_email": with_email, "named": named, "generic": generic,
           "last_24h_leads": last24, "last_24h_with_email": last24_email,
           "markets_active": markets_active, "markets_scraped": markets_done,
           "by_group": {g: {"leads": by_group[g], "with_email": by_group_email[g]} for g in sorted(by_group)}}
    if a.json: return print(json.dumps(out, indent=2))
    print(f"Businesses scraped: {total} total, {with_email} with an email found ({named} named, {generic} generic).")
    print(f"Last 24h: {last24} new businesses, {last24_email} with email.")
    print(f"Markets: {markets_active} active, {markets_done} scraped at least once.")
    for g, v in out["by_group"].items(): print(f"  {g}: {v['leads']} businesses, {v['with_email']} emails")
    print("(These are raw scraped records; they become leads after audit, enrichment and scoring.)")

def cmd_leads(a):
    q = db().table("leads").select("business_name,niche,city,country,phone,website,primary_email,email_source,contact_quality,rating,review_count,ticket_score,maps_url,instagram_url,status").order("review_count", desc=True).limit(a.limit)
    if a.market: q = q.eq("market_id", a.market)
    if a.with_email: q = q.neq("primary_email", "")
    try:
        rows = q.execute().data
    except Exception as e:  # email_source column not migrated yet
        if "email_source" not in str(e): raise
        q2 = db().table("leads").select("business_name,niche,city,country,phone,website,primary_email,contact_quality,rating,review_count,ticket_score,maps_url,instagram_url,status").order("review_count", desc=True).limit(a.limit)
        if a.market: q2 = q2.eq("market_id", a.market)
        if a.with_email: q2 = q2.neq("primary_email", "")
        rows = q2.execute().data
    if a.group: rows = [r for r in rows if group_of(r["niche"]) == a.group]
    if a.json: return print(json.dumps(rows, indent=2))
    for r in rows:
        print(f"- {r['business_name']} ({r['niche']}, {r['city']}) ★{r['rating']} / {r['review_count']} reviews"
              f" | {r['primary_email'] or 'no email'} [{r['contact_quality']}]"
              f" | {r['phone'] or '-'} | {r['website'] or '-'} | source: Google Maps {r['maps_url'] or ''}"
              + (f" | IG: {r['instagram_url']}" if r.get('instagram_url') else ""))

def cmd_markets(a):
    ms = db().table("markets").select("market_id,country,city,niche,status,last_scraped_at,businesses_found").order("last_scraped_at", desc=True, nullsfirst=False).execute().data
    if a.status: ms = [m for m in ms if m["status"] == a.status]
    counts = collections.Counter(r["market_id"] for r in db().table("leads").select("market_id").execute().data)
    if a.json: return print(json.dumps([{**m, "leads": counts[m["market_id"]]} for m in ms], indent=2))
    for m in ms:
        last = m["last_scraped_at"][:16].replace("T", " ") if m["last_scraped_at"] else "never"
        print(f"- {m['market_id']}: {m['niche']} in {m['city']} [{m['status']}] leads={counts[m['market_id']]} last={last}")

def cmd_runs(a):
    rs = db().table("worker_runs").select("*").order("started_at", desc=True).limit(a.limit).execute().data
    if a.json: return print(json.dumps(rs, indent=2))
    for r in rs:
        print(f"- {r['started_at'][:16]} {r['worker']} {r['status']} {json.dumps(r.get('counts') or r.get('input') or {})}" + (f" ERROR {r['error'][:120]}" if r.get('error') else ""))

import re as _re
def _slug(x): return _re.sub(r"[^a-z0-9]+", "_", (x or "").lower()).strip("_")
COUNTRY_GUESS = {"toronto": "Canada", "vancouver": "Canada", "montreal": "Canada", "calgary": "Canada", "london": "United Kingdom",
                 "manchester": "United Kingdom", "birmingham": "United Kingdom", "sydney": "Australia", "melbourne": "Australia",
                 "dubai": "United Arab Emirates", "abu dhabi": "United Arab Emirates", "new york": "United States",
                 "los angeles": "United States", "chicago": "United States", "singapore": "Singapore", "dublin": "Ireland"}

def _sheet_alloc(a, mid):
    """Decide where this task's records go in Google Sheets. Returns dict of market columns to set."""
    from common.sheets import PALETTE, create_sheet
    label = getattr(a, "label", None) or mid
    if getattr(a, "new_sheet", False):
        sid = create_sheet(label)   # a dedicated TAB in the shared spreadsheet (Google forbids SA-owned files)
        return {"sheet_id": sid, "sheet_color": None, "task_label": label}
    color = getattr(a, "color", None)
    if not color:
        used = [m["sheet_color"] for m in db().table("markets").select("sheet_color").neq("sheet_color", "").execute().data]
        color = next((c for c in PALETTE if c not in used), PALETTE[hash(mid) % len(PALETTE)])
    return {"sheet_id": None, "sheet_color": color, "task_label": label}

def add_market(country, city, niche, a=None):
    niche = normalize_niche(niche); city = (city or "").strip()
    country = normalize_country(country) if country else COUNTRY_GUESS.get(city.lower())
    if not country: sys.exit(f"Which country is {city} in? Re-run with --country.")
    mid = f"mk_{_slug(country)[:2]}_{_slug(city)}_{_slug(niche)}"
    exists = db().table("markets").select("market_id,status").eq("market_id", mid).execute().data
    extra = {}
    if a is not None and (getattr(a, "new_sheet", False) or getattr(a, "color", None) or getattr(a, "label", None) or not exists):
        try: extra = _sheet_alloc(a, mid)
        except SystemExit as e: print(f"note: {e}"); extra = {}
        except Exception as e: print("note: sheet allocation skipped (run supabase/migrations_003_market_sheets.sql)"); extra = {}
    if exists:
        upd = {**extra}
        if exists[0]["status"] != "active": upd["status"] = "active"
        if upd:
            try: db().table("markets").update(upd).eq("market_id", mid).execute()
            except Exception: db().table("markets").update({k: v for k, v in upd.items() if k == "status"}).eq("market_id", mid).execute()
        return mid, False
    row = {"market_id": mid, "country": country, "city": city.title(), "niche": niche.lower(), "status": "active",
           "rationale": f"group: {group_of(niche)}; added on request {now().date()}", **extra}
    try: db().table("markets").insert(row).execute()
    except Exception:  # migration 003 not applied yet: insert without sheet columns
        for k in ("sheet_id", "sheet_color", "task_label"): row.pop(k, None)
        db().table("markets").insert(row).execute()
    return mid, True

def cmd_add_market(a):
    mid, created = add_market(a.country, a.city, a.niche, a)
    m = db().table("markets").select("*").eq("market_id", mid).single().execute().data
    where = (f"its own tab '{m.get('task_label')}' in the ARVIS Data sheet" if m.get("sheet_id") else f"the group tab, highlighted {m.get('sheet_color') or 'no colour'}") if "sheet_id" in m else "the shared Sheet (run migration 003 for colours)"
    print(f"market {mid} {'added' if created else 'already existed'} (group: {group_of(a.niche)}). Records go to {where}. "
          f"It joins the nightly rotation; `arvisctl dispatch scrape --market {mid}` runs it now.")

def cmd_dispatch(a):
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPO", "itsmearyanabc/Arvis")
    inputs = {}
    if a.worker == "scrape":
        if a.city and a.niche and not a.market:
            a.market, created = add_market(a.country, a.city, a.niche, a)
            print(f"market {a.market} {'added' if created else 'found'}")
        if a.market: inputs["market_id"] = a.market
        if a.count: inputs["count"] = str(a.count)
    if not tok: sys.exit("GITHUB_TOKEN missing in /opt/arvis/.env — cannot start a run now. The market is saved and the nightly schedule (02:00 IST) will pick it up. Ask Aryan to add the GitHub token to enable on-demand runs.")
    else:
        if a.limit: inputs["limit"] = str(a.limit)
    body = json.dumps({"ref": "main", "inputs": inputs}).encode()
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{a.worker}.yml/dispatches", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"dispatched {a.worker} {inputs or ''} (HTTP {r.status}). It takes 2–10 minutes; check with: arvisctl runs")
    except urllib.error.HTTPError as e:
        hints = {401: "GITHUB_TOKEN is invalid or expired (check the line in /opt/arvis/.env, no quotes, no spaces)",
                 403: "GITHUB_TOKEN lacks permission: edit the token, Repository permissions → Actions: Read and write",
                 404: "workflow or repo not found: check GITHUB_REPO"}
        sys.exit(f"dispatch failed: HTTP {e.code} — {hints.get(e.code, e.reason)}. The market is saved; the nightly schedule will still run it.")

def cmd_sheets(a):
    from common.sheets import list_tabs
    info = list_tabs()
    if info is None: sys.exit("Google Sheet not configured yet: GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SHEET_ID missing in /opt/arvis/.env.")
    if a.json: return print(json.dumps(info, indent=2))
    print(f"Shared spreadsheet: {info['spreadsheet']} — {info['url']}")
    for t in info["tabs"]: print(f"  · {t['tab']}: {t['rows']} rows — {t['url']}")
    try:
        ms = db().table("markets").select("market_id,task_label,sheet_id,sheet_color").execute().data
    except Exception:
        ms = []
    own = [m for m in ms if m.get("sheet_id")]
    if own:
        print("Task tabs: " + ", ".join(m.get("task_label") or m["market_id"] for m in own[:20]))
    colored = [m for m in ms if m.get("sheet_color") and not m.get("sheet_id")]
    if colored:
        print("Colours on the shared sheet: " + ", ".join(f"{m.get('task_label') or m['market_id']}={m['sheet_color']}" for m in colored[:20]))

def cmd_sheets_layout(a):
    from common.sheets import rebuild, LAYOUTS
    if a.layout not in LAYOUTS: sys.exit(f"layout must be one of {LAYOUTS}")
    env_path = os.environ.get("ARVIS_ENV", "/opt/arvis/.env")
    try:  # persist the choice
        lines = [l for l in open(env_path).read().splitlines() if not l.startswith("SHEETS_LAYOUT=")]
        open(env_path, "w").write("\n".join(lines + [f"SHEETS_LAYOUT={a.layout}"]) + "\n")
    except Exception as e: print("note: could not persist layout:", e)
    n = rebuild(a.layout)
    print(f"sheet rebuilt in '{a.layout}' layout: {n} records placed. Run `arvisctl sheets` to list tabs.")

def cmd_mirror(a):
    from common.sheets import mirror_leads
    n = mirror_leads()
    print(f"mirror done: {n} new records pushed to the Google Sheet." if n is not None else "mirror skipped")

def cmd_verify(a):
    import random, urllib.error
    url = os.environ.get("REACHER_URL", "http://127.0.0.1:8081").rstrip("/") + "/v0/check_email"
    try:
        from common.events import log_event
    except Exception:
        log_event = lambda *x, **k: None
    rows = db().table("contacts").select("contact_id,lead_id,email,contact_quality").eq("email_status", "unknown").limit(a.limit).execute().data
    counts = collections.Counter(); unknown_streak = 0
    for c in rows:
        body = json.dumps({"to_email": c["email"]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r: res = json.load(r)
            status = res.get("is_reachable", "unknown"); catch_all = bool((res.get("mx") or {}).get("accepts_mail")) and bool((res.get("smtp") or {}).get("is_catch_all"))
        except Exception as e:
            status, catch_all = "unknown", False
        counts[status] += 1
        unknown_streak = unknown_streak + 1 if status == "unknown" else 0
        db().table("contacts").update({"email_status": status, "verified_at": now_iso(), "verifier": "reacher"}).eq("contact_id", c["contact_id"]).execute()
        lead_upd = None
        if status == "safe" or (status == "risky" and c["contact_quality"] == "named"):
            lead_upd = {"status": "verified", "primary_email": c["email"], "contact_quality": c["contact_quality"]}
        elif status == "invalid":
            others = db().table("contacts").select("contact_id").eq("lead_id", c["lead_id"]).in_("email_status", ["unknown", "safe", "risky"]).execute().data
            if not others: lead_upd = {"status": "parked", "parked_reason": "invalid_only"}
        if lead_upd:
            lead_upd["updated_at"] = now_iso()
            db().table("leads").update(lead_upd).eq("lead_id", c["lead_id"]).execute()
        if unknown_streak >= 20:
            msg = "Reacher returned 'unknown' 20× in a row: outbound port 25 is probably blocked on the VPS. Stopping; fall back to Hunter verification."
            log_event("brain", "warn", msg); print(msg); break
        time.sleep(random.uniform(5, 15))
    summary = f"verified {len(rows)} contacts: " + ", ".join(f"{k}={v}" for k, v in counts.items()) if rows else "no contacts waiting for verification"
    log_event("brain", "info", summary); print(summary)

def cmd_email(a):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mailer
    try: from common.events import log_event
    except Exception: log_event = lambda *x, **k: None
    if a.action == "check":
        user = os.environ.get("MAILBOX_1_USER", "connect@armedias.tech"); dom = user.split("@")[-1]
        probs = mailer.deliverability_check(dom)
        if not os.environ.get("MAILBOX_1_PASS"): probs.append("MAILBOX_1_PASS (Zoho app password) not set")
        if not os.environ.get("POSTAL_ADDRESS"): probs.append("POSTAL_ADDRESS not set")
        print("ready to send from " + user if not probs else "NOT ready: " + "; ".join(probs)); return
    if a.action == "draft":
        if not (a.to and a.subject and a.body): sys.exit("draft needs --to, --subject and --body")
        sid, text = mailer.draft(db, a.to, a.subject, a.body, a.name)
        log_event("brain", "info", f"email draft {sid[:8]} to {a.to}")
        print(f"DRAFT {sid}\n-----\nTo: {a.to}\n{text}\n-----\nShow this to Aryan exactly. Send only after he replies 'send': arvisctl email send --id {sid} --confirm")
        return
    if a.action == "send":
        if not a.confirm: sys.exit("refusing: add --confirm, and only after Aryan replied 'send' to this exact draft")
        to, mid = mailer.send(db, a.id)
        log_event("brain", "info", f"email sent to {to}", {"message_id": mid})
        print(f"sent to {to} (Message-ID {mid})"); return
    sys.exit("email action must be draft, send or check")

def cmd_report(a):
    rows = db().table("leads").select("niche,city,primary_email,scraped_at,contact_quality").execute().data
    today = now().astimezone(IST).strftime("%a %d %b")
    last24 = [r for r in rows if r["scraped_at"] and r["scraped_at"] >= ago(24)]
    runs = db().table("worker_runs").select("worker,status,counts,error,started_at").gte("started_at", ago(24)).execute().data
    failed = [r for r in runs if r["status"] == "failed"]
    by_mk = collections.Counter(f"{r['niche']} {r['city']}" for r in last24)
    lines = [f"ARVIS daily — {today}",
             f"Scraped last 24h: {len(last24)} businesses ({sum(1 for r in last24 if r['primary_email'])} with email) across {len(by_mk)} markets",
             *[f"  · {k}: {v}" for k, v in by_mk.most_common(6)],
             f"Total: {len(rows)} businesses scraped, {sum(1 for r in rows if r['primary_email'])} emails ({sum(1 for r in rows if r['contact_quality']=='named')} named)",
             f"Worker runs: {len(runs)} ({len(failed)} failed)" + (": " + "; ".join(f"{r['worker']} {str(r['error'])[:60]}" for r in failed) if failed else ""),
             f"Audited {count('audits')} · Contacts found {count('contacts')} · Verified leads {count('leads', status='verified')} · Parked {count('leads', status='parked')}",
             "Sent 0 · Replied 0 · Booked 0 (phases 4–6 not live)",
             "Needs you: Google service account for the Sheet" if not os.environ.get("GOOGLE_SHEET_ID") else "",
             "Needs you: GitHub token for on-demand scrapes" if not os.environ.get("GITHUB_TOKEN") else ""]
    print("\n".join(l for l in lines if l))

def main():
    p = argparse.ArgumentParser(prog="arvisctl"); p.add_argument("--json", action="store_true")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("stats"); sp.add_parser("report"); sp.add_parser("sheets"); sp.add_parser("mirror")
    sl = sp.add_parser("sheets-layout"); sl.add_argument("layout")
    vf = sp.add_parser("verify"); vf.add_argument("--limit", type=int, default=60)
    em = sp.add_parser("email"); em.add_argument("action", choices=["draft", "send", "check"]); em.add_argument("--to"); em.add_argument("--subject")
    em.add_argument("--body"); em.add_argument("--name"); em.add_argument("--id"); em.add_argument("--confirm", action="store_true")
    for name in ("businesses", "leads"):
        l = sp.add_parser(name); l.add_argument("--limit", type=int, default=10); l.add_argument("--market"); l.add_argument("--with-email", action="store_true"); l.add_argument("--group")
    m = sp.add_parser("markets"); m.add_argument("--status")
    am = sp.add_parser("add-market"); am.add_argument("--country"); am.add_argument("--city", required=True); am.add_argument("--niche", required=True)
    am.add_argument("--new-sheet", action="store_true"); am.add_argument("--color"); am.add_argument("--label")
    r = sp.add_parser("runs"); r.add_argument("--limit", type=int, default=10)
    d = sp.add_parser("dispatch"); d.add_argument("worker", choices=["scrape", "audit"]); d.add_argument("--market"); d.add_argument("--city"); d.add_argument("--niche"); d.add_argument("--country"); d.add_argument("--count", type=int); d.add_argument("--limit", type=int)
    d.add_argument("--new-sheet", action="store_true"); d.add_argument("--color"); d.add_argument("--label")
    a = p.parse_args()
    log_event("brain", "info", "arvisctl %s" % " ".join(sys.argv[1:])[:200], {"cmd": a.cmd})
    {"stats": cmd_stats, "leads": cmd_leads, "businesses": cmd_leads, "markets": cmd_markets, "add-market": cmd_add_market, "runs": cmd_runs,
     "dispatch": cmd_dispatch, "sheets": cmd_sheets, "sheets-layout": cmd_sheets_layout, "mirror": cmd_mirror, "verify": cmd_verify, "email": cmd_email, "report": cmd_report}[a.cmd](a)

if __name__ == "__main__":
    main()
