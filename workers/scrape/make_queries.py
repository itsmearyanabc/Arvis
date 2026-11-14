"""Build the query list for gosom/google-maps-scraper from active markets.
Usage: python -I workers/scrape/make_queries.py [market_id] > queries.txt
Picks the active market with the oldest last_scraped_at (or the one given) and writes
2-4 synonym queries. Prints the chosen market_id to stderr for the upload step."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db import db

SYNONYMS = {  # extend per niche; keep to real business categories
    "dentist": ["dentist", "dental clinic", "orthodontist"],
    "lawyer": ["law firm", "lawyer", "attorney"],
    "real estate": ["real estate agency", "realtor", "property agent"],
    "plumber": ["plumber", "plumbing company"],
    "clinic": ["medical clinic", "private clinic"],
}

def main():
    q = db().table("markets").select("*").eq("status", "active")
    if len(sys.argv) > 1:
        q = q.eq("market_id", sys.argv[1])
    rows = q.order("last_scraped_at", desc=False, nullsfirst=True).limit(1).execute().data
    if not rows:
        print("no active market", file=sys.stderr); sys.exit(2)
    m = rows[0]
    terms = SYNONYMS.get(m["niche"].lower(), [m["niche"]])[:4]
    for t in terms:
        print(f"{t} in {m['city']}, {m['country']}")
    print(m["market_id"], file=sys.stderr)

if __name__ == "__main__":
    main()
