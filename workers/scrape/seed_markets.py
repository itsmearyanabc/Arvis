"""Seed the markets table with the starting set of (city, niche) pairs across niche groups.
Usage: python -I workers/scrape/seed_markets.py          (idempotent: existing ids are left alone)
Cities: English-speaking, high-ticket, dense Google Maps coverage, Aryan can take calls in their
business hours from India (Toronto/London evening = India night; Sydney/Dubai = India day)."""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.db import db
from common.niches import GROUPS

CITIES = [("Canada", "Toronto"), ("Canada", "Vancouver"), ("United Kingdom", "London"),
          ("United Kingdom", "Manchester"), ("Australia", "Sydney"), ("United Arab Emirates", "Dubai")]

def slug(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def main():
    rows = []
    for group, niches in GROUPS.items():
        for niche in niches:
            for country, city in CITIES:
                rows.append({"market_id": f"mk_{slug(country)[:2]}_{slug(city)}_{slug(niche)}",
                             "country": country, "city": city, "niche": niche, "status": "active",
                             "rationale": f"group: {group}; seeded 2026-11-15"})
    existing = {r["market_id"] for r in db().table("markets").select("market_id").execute().data}
    new = [r for r in rows if r["market_id"] not in existing]
    for i in range(0, len(new), 100):
        db().table("markets").insert(new[i:i+100]).execute()
    print(f"markets: {len(existing)} existing, {len(new)} added, {len(rows)} total defined")

if __name__ == "__main__":
    main()
