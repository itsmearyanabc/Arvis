"""Optional Google Sheets mirror. Appends new rows from a Supabase table to a tab of Aryan's
Sheet so he can browse leads in Sheets while Supabase stays the system of record.
Needs GOOGLE_SERVICE_ACCOUNT_JSON (the JSON text, or a path) and GOOGLE_SHEET_ID.
Silently skips when either is missing."""
import os, sys, json
from typing import Optional
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db import db, fetch_all
from common.niches import group_of

LEAD_COLS = ["lead_id", "business_name", "niche", "city", "country", "phone", "website", "rating",
             "review_count", "fit_score", "ticket_score", "contact_quality", "primary_email",
             "email_source", "source", "maps_url", "top_issue", "status", "instagram_url",
             "linkedin_url", "scraped_at"]

import re as _re

def _sheet_id(v):
    """Accept the bare id or the whole Google Sheets URL (people paste the URL)."""
    v = (v or "").strip()
    m = _re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]{20,})", v)
    return m.group(1) if m else (v or None)

def _client():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"); sid = _sheet_id(os.environ.get("GOOGLE_SHEET_ID"))
    if not raw:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [os.environ.get("ARVIS_ENV"), "/opt/arvis/.env", os.path.join(root, ".env")]
        for p in candidates:
            if p and os.path.exists(p):
                for line in open(p):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
                break
        raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"); sid = _sheet_id(os.environ.get("GOOGLE_SHEET_ID"))
    if not raw:
        return None, None
    import gspread
    from google.oauth2.service_account import Credentials
    if not raw.strip().startswith("{") and not os.path.isabs(raw):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidate = os.path.join(root, raw)
        if os.path.exists(candidate):
            raw = candidate
    info = json.loads(raw) if raw.strip().startswith("{") else json.load(open(raw))
    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    try:   # retries 429/5xx with exponential backoff instead of crashing the nightly mirror
        gc = gspread.authorize(creds, http_client=gspread.BackOffHTTPClient)
    except Exception:
        gc = gspread.authorize(creds)
    if not sid:
        try:
            for f in gc.list_spreadsheet_files():
                name = (f.get("name") or "").strip().lower()
                if name in ("arvis data", "arvis — data", "arvis_data"):
                    sid = f["id"]
                    break
        except Exception:
            pass
    return gc, sid

def _tab(sh, name):
    try:
        ws = sh.worksheet(name)
    except Exception:
        ws = sh.add_worksheet(name, rows=2000, cols=len(LEAD_COLS))
    if not ws.row_values(1):
        ws.append_row(LEAD_COLS)
        ws.freeze(rows=1)
    return ws

PALETTE = ["#FFF2CC", "#D9EAD3", "#CFE2F3", "#F4CCCC", "#EAD1DC", "#FCE5CD", "#D0E0E3", "#E6B8AF", "#FFD966", "#B6D7A8"]

def _hex_to_rgb(h):
    h = (h or "").lstrip("#")
    if len(h) != 6: return None
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}

def _market_sheet_map():
    """market_id -> (sheet_id or None, colour or None, task_label)."""
    try:
        ms = fetch_all(db().table("markets").select("market_id,sheet_id,sheet_color,task_label").order("market_id"))
    except Exception:  # migration 003 not applied yet
        ms = fetch_all(db().table("markets").select("market_id").order("market_id"))
    return {m["market_id"]: (m.get("sheet_id"), m.get("sheet_color"), m.get("task_label")) for m in ms}

def create_sheet(title: str, share_with: Optional[str] = None) -> str:
    """Service accounts cannot own Drive files (no storage quota), so a brand-new spreadsheet must be
    created by Aryan and shared with the service account. This helper therefore creates a dedicated TAB
    named after the task inside the shared spreadsheet and returns the shared spreadsheet id; the
    market's task_label routes its rows to that tab (see mirror_leads)."""
    gc, sid = _client()
    if not gc: raise SystemExit("Google Sheets not configured (GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID).")
    sh = gc.open_by_key(sid)
    _tab(sh, title[:90])
    return sid

LAYOUTS = ("market", "city", "group")

def layout() -> str:
    """How tabs are organised. market = one tab per city+niche ("Toronto — Dentist", default);
    city = one tab per city; group = one tab per niche group. Set with `arvisctl sheets-layout`."""
    v = (os.environ.get("SHEETS_LAYOUT") or "market").strip().lower()
    return v if v in LAYOUTS else "market"

def tab_for(r, mmap, lay=None):
    sid_, _, label = mmap.get(r.get("market_id")) or (None, None, None)
    if sid_ and label:                      # a task Aryan wanted on its own tab
        return label[:90]
    lay = lay or layout()
    niche = (r.get("niche") or "").strip()
    city = (r.get("city") or "").strip()
    if lay == "market": return f"{city} — {niche.title()}"[:95]
    if lay == "city": return city[:95] or "Unknown city"
    return group_of(niche)

def rebuild(lay: str) -> int:
    """Wipe the shared spreadsheet's tabs and re-mirror everything in the given layout."""
    gc, sid = _client()
    if not gc: raise SystemExit("Google Sheets not configured.")
    sh = gc.open_by_key(sid)
    keep = sh.add_worksheet("_rebuilding", rows=2, cols=2)
    for ws in sh.worksheets():
        if ws.id != keep.id: sh.del_worksheet(ws)
    os.environ["SHEETS_LAYOUT"] = lay
    n = mirror_leads()
    sh.del_worksheet(keep)
    return n

def mirror_leads(since_iso: Optional[str] = None) -> int:
    """Per market: its own spreadsheet (sheet_id) or the default one; inside a spreadsheet tabs follow
    layout(); rows of a market get its highlight colour. Appends only rows not yet on the tab."""
    gc, default_sid = _client()
    if not gc:
        print("sheets mirror: not configured, skipping"); return 0
    cols = LEAD_COLS + ["market_id"]
    q = db().table("leads").select(",".join(cols)).order("scraped_at")
    if since_iso: q = q.gte("scraped_at", since_iso)
    mmap = _market_sheet_map()
    lay = layout()
    buckets = {}  # (sheet_id, tab) -> list of leads
    for r in q.execute().data:
        sid_, _, _label = mmap.get(r.get("market_id")) or (None, None, None)
        sid = sid_ or default_sid
        buckets.setdefault((sid, tab_for(r, mmap, lay)), []).append(r)
    total, books, tabs, have = 0, {}, {}, {}
    for sid in {k[0] for k in buckets}:
        sh = books[sid] = gc.open_by_key(sid)
        tabs[sid] = {ws.title: ws for ws in sh.worksheets()}                       # 1 call
        titles = list(tabs[sid])
        if titles:                                                                 # 1 call for ALL tabs
            ranges = sh.values_batch_get([f"'{t}'!A:A" for t in titles]).get("valueRanges", [])
            for t, vr in zip(titles, ranges):
                have[(sid, t)] = [row[0] for row in vr.get("values", []) if row]
    for (sid, group), leads in buckets.items():
        sh = books[sid]
        col = have.get((sid, group), [])
        known = set(col[1:])
        new = [r for r in leads if r["lead_id"] not in known]
        if not new: continue                                                       # untouched tab: 0 calls
        ws = tabs[sid].get(group) or _tab(sh, group)
        if not col: col = [LEAD_COLS[0]]                                           # _tab wrote the header
        start = len(col) + 1
        rows = [[("" if r.get(c) is None else r.get(c)) for c in LEAD_COLS] for r in new]
        for i in range(0, len(rows), 500):
            ws.append_rows(rows[i:i+500], value_input_option="RAW")
        # colour runs of rows per market
        fmt = []
        for i, r in enumerate(new):
            color = (mmap.get(r.get("market_id")) or (None, None, None))[1]
            rgb = _hex_to_rgb(color)
            if rgb: fmt.append({"range": f"A{start+i}:{chr(64+len(LEAD_COLS))}{start+i}", "format": {"backgroundColor": rgb}})
        for i in range(0, len(fmt), 200):
            try: ws.batch_format(fmt[i:i+200])
            except Exception as e: print("sheets mirror: colour skipped:", str(e)[:80])
        total += len(new)
        print(f"sheets mirror: +{len(new)} records on tab '{group}' of {sh.title}")
    # keep tabs alphabetical so cities sit together
    try:
        for sh in books.values():
            ws = sh.worksheets(); sh.reorder_worksheets(sorted(ws, key=lambda w: w.title.lower()))
    except Exception: pass
    return total

def list_tabs():
    """Tabs of the ARVIS spreadsheet with row counts and direct links."""
    gc, sid = _client()
    if not gc:
        return None
    sh = gc.open_by_key(sid)
    out = []
    for ws in sh.worksheets():
        rows = max(len(ws.col_values(1)) - 1, 0)
        out.append({"tab": ws.title, "rows": rows, "url": f"https://docs.google.com/spreadsheets/d/{sid}/edit#gid={ws.id}"})
    return {"spreadsheet": sh.title, "url": f"https://docs.google.com/spreadsheets/d/{sid}", "tabs": out}

def _diagnose(e):
    """Explain a Sheets failure without printing secrets."""
    sid = _sheet_id(os.environ.get("GOOGLE_SHEET_ID")) or ""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or ""
    who = "?"
    try:
        info = json.loads(raw) if raw.strip().startswith("{") else json.load(open(raw))
        who = info.get("client_email", "?")
    except Exception:
        who = "unreadable GOOGLE_SERVICE_ACCOUNT_JSON"
    hint = ("GOOGLE_SHEET_ID looks like a placeholder, not a real id (real ids are ~44 characters)" if len(sid) < 30
            else f"the sheet is not shared with {who}, or GOOGLE_SHEET_ID points at another spreadsheet")
    return f"Sheet mirror skipped: {type(e).__name__}. Service account: {who}. GOOGLE_SHEET_ID length: {len(sid)}. Likely cause: {hint}."

if __name__ == "__main__":
    # The mirror is a convenience copy; Supabase is the system of record. A Sheets problem must never
    # mark the nightly scrape as failed, so it ends as a GitHub warning + a brain-log entry instead.
    try:
        mirror_leads(sys.argv[1] if len(sys.argv) > 1 else None)
    except Exception as e:
        msg = _diagnose(e)
        print(f"::warning title=Google Sheet mirror::{msg}")
        try:
            from common.events import log_event
            log_event("mirror", "warn", msg)
        except Exception:
            pass
