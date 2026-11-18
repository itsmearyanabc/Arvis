"""Supabase client + run logging shared by all workers. Service-role key only (never shipped to a browser)."""
import os, json, datetime as dt
from typing import Optional
from supabase import create_client

_client = None

def db():
    global _client
    if _client is None:
        _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    return _client

def fetch_all(query, page: int = 1000) -> list:
    """Run a PostgREST select and return ALL rows. Supabase caps every response at 1000 rows,
    so a plain .execute() silently truncates big tables. `query` is an unexecuted select builder
    (filters/order applied); it is re-used with .range() per page."""
    out, start = [], 0
    while True:
        rows = query.range(start, start + page - 1).execute().data or []
        out.extend(rows)
        if len(rows) < page:
            return out
        start += page

def start_run(worker: str, inp: Optional[dict] = None) -> str:
    row = db().table("worker_runs").insert({"worker": worker, "input": inp or {}}).execute().data[0]
    return row["run_id"]

def finish_run(run_id: str, counts: dict, error: Optional[str] = None):
    db().table("worker_runs").update({
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "failed" if error else "ok", "counts": counts, "error": error,
    }).eq("run_id", run_id).execute()

def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()
