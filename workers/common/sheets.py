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

def mirror_leads(since_iso: Optional[str] = None) -> int:
    """One tab per niche group (Healthcare, Legal & Finance, ...). Appends leads not yet on the tab."""
    gc, sid = _client()
    if not gc:
        print("sheets mirror: not configured, skipping"); return 0
    sh = gc.open_by_key(sid)
    q = db().table("leads").select(",".join(LEAD_COLS)).order("scraped_at")
    if since_iso: q = q.gte("scraped_at", since_iso)
    by_group = {}
    for r in q.execute().data:
        by_group.setdefault(group_of(r.get("niche")), []).append(r)
    total = 0
    for group, leads in by_group.items():
        ws = _tab(sh, group)
        have = set(ws.col_values(1)[1:])
        rows = [[("" if r.get(c) is None else r.get(c)) for c in LEAD_COLS] for r in leads if r["lead_id"] not in have]
        for i in range(0, len(rows), 500):
            ws.append_rows(rows[i:i+500], value_input_option="RAW")
        total += len(rows)
        print(f"sheets mirror: +{len(rows)} leads on tab '{group}'")
    return total

if __name__ == "__main__":
    mirror_leads(sys.argv[1] if len(sys.argv) > 1 else None)
