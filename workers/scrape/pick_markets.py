"""Pick the N active markets scraped longest ago and print them as a JSON list (for the Actions matrix).
Usage: python -I workers/scrape/pick_markets.py [N] [market_id]   -> writes markets.json and prints it"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db import db

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() else 3
    forced = sys.argv[2].strip() if len(sys.argv) > 2 else ""
    if forced:
        ids = [forced]
    else:
        rows = db().table("markets").select("market_id").eq("status", "active") \
            .order("last_scraped_at", desc=False, nullsfirst=True).limit(n).execute().data
        ids = [r["market_id"] for r in rows]
    json.dump(ids, open("markets.json", "w"))
    print(json.dumps(ids))

if __name__ == "__main__":
    main()
