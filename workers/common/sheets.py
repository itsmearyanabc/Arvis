"""Optional Google Sheets mirror. Appends new rows from a Supabase table to a tab of Aryan's
Sheet so he can browse leads in Sheets while Supabase stays the system of record.
Needs GOOGLE_SERVICE_ACCOUNT_JSON (the JSON text, or a path) and GOOGLE_SHEET_ID.
Silently skips when either is missing."""
import os, sys, json
from typing import Optional
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db import db
from common.niches import group_of

LEAD_COLS = ["lead_id", "business_name", "niche", "city", "country", "phone", "website", "rating",
             "review_count", "fit_score", "ticket_score", "contact_quality", "primary_email",
             "email_source", "source", "maps_url", "top_issue", "status", "instagram_url",
             "linkedin_url", "scraped_at"]

def _client():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"); sid = os.environ.get("GOOGLE_SHEET_ID")
    if not raw or not sid:
        return None, None
    import gspread
    from google.oauth2.service_account import Credentials
    info = json.loads(raw) if raw.strip().startswith("{") else json.load(open(raw))
    creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds), sid

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
        ms = db().table("markets").select("market_id,sheet_id,sheet_color,task_label").execute().data
    except Exception:  # migration 003 not applied yet
        ms = db().table("markets").select("market_id").execute().data
    return {m["market_id"]: (m.get("sheet_id"), m.get("sheet_color"), m.get("task_label")) for m in ms}

def create_sheet(title: str, share_with: Optional[str] = None) -> str:
    """Create a new spreadsheet owned by the service account and share it with Aryan. Returns its id."""
    gc, _ = _client()
    if not gc: raise SystemExit("Google Sheets not configured (GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID).")
    sh = gc.create(title)
    owner = share_with or os.environ.get("ARVIS_OWNER_EMAIL")
    if owner:
        sh.share(owner, perm_type="user", role="writer", notify=False)
    return sh.id

def mirror_leads(since_iso: Optional[str] = None) -> int:
    """Per market: its own spreadsheet (sheet_id) or the default one; inside a spreadsheet one tab per
    niche group; rows of a market get its highlight colour. Appends only rows not yet on the tab."""
    gc, default_sid = _client()
    if not gc:
        print("sheets mirror: not configured, skipping"); return 0
    cols = LEAD_COLS + ["market_id"]
    q = db().table("leads").select(",".join(cols)).order("scraped_at")
    if since_iso: q = q.gte("scraped_at", since_iso)
    mmap = _market_sheet_map()
    buckets = {}  # (sheet_id, group) -> list of leads
    for r in q.execute().data:
        sid = (mmap.get(r.get("market_id")) or (None, None, None))[0] or default_sid
        buckets.setdefault((sid, group_of(r.get("niche"))), []).append(r)
    total, books = 0, {}
    for (sid, group), leads in buckets.items():
        sh = books.setdefault(sid, gc.open_by_key(sid))
        ws = _tab(sh, group)
        have = set(ws.col_values(1)[1:])
        new = [r for r in leads if r["lead_id"] not in have]
        if not new: continue
        start = len(ws.col_values(1)) + 1
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

if __name__ == "__main__":
    mirror_leads(sys.argv[1] if len(sys.argv) > 1 else None)
