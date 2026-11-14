"""Build the query list for gosom/google-maps-scraper from active markets.
Usage: python -I workers/scrape/make_queries.py [market_id]
Writes queries.txt (one query per line) and market.txt (the chosen market_id) in the CWD.
Picks the given market, else the active market with the oldest last_scraped_at."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db import db

SYNONYMS = {  # extend per niche; keep to real business categories
    "dentist": ["dentist", "dental clinic", "orthodontist"],
    "lawyer": ["law firm", "lawyer", "attorney"],
    "real estate": ["real estate agency", "realtor", "property agent"],
    "plumber": ["plumber", "plumbing company"],
    "clinic": ["medical clinic", "private clinic"],
}

def main():
    market_id = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    q = db().table("markets").select("*").eq("status", "active")
    if market_id:
        q = q.eq("market_id", market_id)
    rows = q.order("last_scraped_at", desc=False, nullsfirst=True).limit(1).execute().data
    if not rows:
        print("no active market found" + (f" with id {market_id}" if market_id else ""), file=sys.stderr)
        sys.exit(2)
    m = rows[0]
    terms = SYNONYMS.get(m["niche"].lower(), [m["niche"]])[:4]
    with open("queries.txt", "w") as f:
        for t in terms:
            f.write(f"{t} in {m['city']}, {m['country']}\n")
    with open("market.txt", "w") as f:
        f.write(m["market_id"])
    print(f"market {m['market_id']}: {len(terms)} queries")

if __name__ == "__main__":
    main()
