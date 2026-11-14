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
