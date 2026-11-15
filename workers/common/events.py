"""Brain log: one row per notable event in brain_events (supabase/migrations_002_brain_events.sql).
The dashboard streams these via Realtime. Never raises: a logging failure must not break a worker."""
import sys
from typing import Optional

SOURCES = ("brain", "scrape", "audit", "mirror", "telegram")
LEVELS = ("debug", "info", "warn", "error")


def log_event(source, level, message, data=None):
    # type: (str, str, str, Optional[dict]) -> None
    source = source if source in SOURCES else "brain"
    level = level if level in LEVELS else "info"
    try:
        from common.db import db
        db().table("brain_events").insert({
            "source": source, "level": level, "message": str(message)[:2000], "data": data or {},
        }).execute()
    except Exception as e:  # table missing, no network, no key: log locally and move on
        print("[events] %s/%s not recorded: %s" % (source, level, e), file=sys.stderr)
