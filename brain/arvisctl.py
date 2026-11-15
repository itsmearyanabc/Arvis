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
  arvisctl add-market --country C --city CITY --niche NICHE   seed a new market (idempotent)
  arvisctl runs [--limit N]           recent worker runs (scrape/audit) with counts
  arvisctl dispatch scrape [--market ID | --city CITY --niche NICHE [--country C]] [--count N]
                                      start a scrape on GitHub Actions now (needs GITHUB_TOKEN); unseeded
                                      city/niche is added as a market first
  arvisctl dispatch audit [--limit N]
  arvisctl sheets                     list the Google Sheet tabs (one per niche group) with counts + links
  arvisctl mirror                     push new records to the Google Sheet now
  arvisctl report                     the daily Telegram report text
Output is plain text meant to be pasted to Aryan; add --json for machine output."""
import os, sys, json, argparse, datetime as dt, collections, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "workers"))

def load_env():
    path = os.environ.get("ARVIS_ENV", "/opt/arvis/.env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()
from common.db import db
from common.niches import group_of, GROUPS

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

def add_market(country, city, niche):
    country = country or COUNTRY_GUESS.get(city.lower())
    if not country: sys.exit(f"Which country is {city} in? Re-run with --country.")
    mid = f"mk_{_slug(country)[:2]}_{_slug(city)}_{_slug(niche)}"
    exists = db().table("markets").select("market_id,status").eq("market_id", mid).execute().data
    if exists:
        if exists[0]["status"] != "active":
            db().table("markets").update({"status": "active"}).eq("market_id", mid).execute()
        return mid, False
    db().table("markets").insert({"market_id": mid, "country": country, "city": city.title(), "niche": niche.lower(),
                                  "status": "active", "rationale": f"group: {group_of(niche)}; added on request {now().date()}"}).execute()
    return mid, True

def cmd_add_market(a):
    mid, created = add_market(a.country, a.city, a.niche)
    print(f"market {mid} {'added' if created else 'already existed'} (group: {group_of(a.niche)}). It joins the nightly rotation; `arvisctl dispatch scrape --market {mid}` runs it now.")

def cmd_dispatch(a):
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPO", "itsmearyanabc/Arvis")
    inputs = {}
    if a.worker == "scrape":
        if a.city and a.niche and not a.market:
            a.market, created = add_market(a.country, a.city, a.niche)
            print(f"market {a.market} {'added' if created else 'found'}")
        if a.market: inputs["market_id"] = a.market
        if a.count: inputs["count"] = str(a.count)
    if not tok: sys.exit("GITHUB_TOKEN missing in /opt/arvis/.env — cannot start a run now. The market is saved and the nightly schedule (02:00 IST) will pick it up. Ask Aryan to add the GitHub token to enable on-demand runs.")
    else:
        if a.limit: inputs["limit"] = str(a.limit)
    body = json.dumps({"ref": "main", "inputs": inputs}).encode()
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{a.worker}.yml/dispatches", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"dispatched {a.worker} {inputs or ''} (HTTP {r.status}). It takes 2–10 minutes; check with: arvisctl runs")

def cmd_sheets(a):
    from common.sheets import list_tabs
    info = list_tabs()
    if info is None: sys.exit("Google Sheet not configured yet: GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SHEET_ID missing in /opt/arvis/.env.")
    if a.json: return print(json.dumps(info, indent=2))
    print(f"Spreadsheet: {info['spreadsheet']} — {info['url']}")
    for t in info["tabs"]: print(f"  · {t['tab']}: {t['rows']} rows — {t['url']}")

def cmd_mirror(a):
    from common.sheets import mirror_leads
    n = mirror_leads()
    print(f"mirror done: {n} new records pushed to the Google Sheet." if n is not None else "mirror skipped")

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
             "Audited 0 · Verified 0 · Sent 0 · Replied 0 · Booked 0 (phases 3–6 not live)",
             "Needs you: Google service account for the Sheet" if not os.environ.get("GOOGLE_SHEET_ID") else "",
             "Needs you: GitHub token for on-demand scrapes" if not os.environ.get("GITHUB_TOKEN") else ""]
    print("\n".join(l for l in lines if l))

def main():
    p = argparse.ArgumentParser(prog="arvisctl"); p.add_argument("--json", action="store_true")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("stats"); sp.add_parser("report"); sp.add_parser("sheets"); sp.add_parser("mirror")
    for name in ("businesses", "leads"):
        l = sp.add_parser(name); l.add_argument("--limit", type=int, default=10); l.add_argument("--market"); l.add_argument("--with-email", action="store_true"); l.add_argument("--group")
    m = sp.add_parser("markets"); m.add_argument("--status")
    am = sp.add_parser("add-market"); am.add_argument("--country"); am.add_argument("--city", required=True); am.add_argument("--niche", required=True)
    r = sp.add_parser("runs"); r.add_argument("--limit", type=int, default=10)
    d = sp.add_parser("dispatch"); d.add_argument("worker", choices=["scrape", "audit"]); d.add_argument("--market"); d.add_argument("--city"); d.add_argument("--niche"); d.add_argument("--country"); d.add_argument("--count", type=int); d.add_argument("--limit", type=int)
    a = p.parse_args()
    {"stats": cmd_stats, "leads": cmd_leads, "businesses": cmd_leads, "markets": cmd_markets, "add-market": cmd_add_market, "runs": cmd_runs,
     "dispatch": cmd_dispatch, "sheets": cmd_sheets, "mirror": cmd_mirror, "report": cmd_report}[a.cmd](a)

if __name__ == "__main__":
    main()
