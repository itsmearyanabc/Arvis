"""Upsert gosom CSV output into Supabase leads with scoring and dedup.
Usage: python -I workers/scrape/upload.py results.csv <market_id> <run_id>
Never writes consumer listings (no category) and never re-inserts an existing place_id."""
import sys, os, csv, re, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db import db, finish_run, now_iso

SOCIAL = {"instagram.com": "instagram_url", "linkedin.com": "linkedin_url", "facebook.com": "facebook_url"}

def to_int(v):
    try: return int(float(v))
    except Exception: return None

def ticket_score(r):
    s = 0
    if (to_int(r.get("review_count")) or 0) >= 50: s += 25
    try:
        if float(r.get("review_rating") or 0) >= 4.3: s += 15
    except ValueError: pass
    if r.get("website"): s += 10
    else: s += 30               # no site = bigger project
    return min(s, 100)

def fit_score(r, market):
    s = 50
    if market["city"].lower() in (r.get("address") or "").lower(): s += 20
    if r.get("category"): s += 15
    name = (r.get("title") or "").lower()
    if any(k in name for k in ("inc", "group", "corporation", "franchise")): s -= 15
    return max(0, min(s, 100))

def main():
    path, market_id, run_id = sys.argv[1:4]
    market = db().table("markets").select("*").eq("market_id", market_id).single().execute().data
    existing = {r["place_id"] for r in db().table("leads").select("place_id").eq("market_id", market_id).execute().data}
    rows, skipped = [], 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("category") or not r.get("title"):
                skipped += 1; continue                     # not a business listing
            place_id = r.get("data_id") or r.get("cid") or hashlib.sha1((r["title"] + (r.get("phone") or "")).encode()).hexdigest()
            if place_id in existing: continue
            existing.add(place_id)
            lead = {
                "lead_id": "ld_" + hashlib.sha1(place_id.encode()).hexdigest()[:12],
                "place_id": place_id, "market_id": market_id,
                "business_name": r["title"], "niche": market["niche"], "city": market["city"],
                "country": market["country"], "address": r.get("address"), "phone": r.get("phone") or None,
                "website": (r.get("website") or None), "rating": r.get("review_rating") or None,
                "review_count": to_int(r.get("review_count")), "maps_url": r.get("link"),
                "source": "google_maps", "ticket_score": ticket_score(r), "fit_score": fit_score(r, market),
                "contact_quality": "named" if r.get("owner") else "none",
                "notes": ("owner: " + r["owner"]) if r.get("owner") else None,
                "scraped_at": now_iso(),
            }
            emails = [e for e in re.split(r"[,; ]+", r.get("emails") or "") if "@" in e]
            if emails:
                lead["primary_email"] = emails[0]
                lead["email_source"] = "website"   # gosom -email reads the business's own site
                lead["contact_quality"] = "generic" if emails[0].split("@")[0] in ("info", "contact", "hello", "office", "admin") else "named"
            for host, col in SOCIAL.items():
                m = re.search(r"https?://(?:www\.)?" + re.escape(host) + r"/[\w./-]+", r.get("about", "") + " " + r.get("website", ""))
                if m: lead[col] = m.group(0)
            rows.append(lead)
    def upsert(batch):
        try:
            db().table("leads").upsert(batch, on_conflict="place_id", ignore_duplicates=True).execute()
        except Exception as e:  # email_source column not migrated yet -> retry without it
            if "email_source" not in str(e): raise
            for r in batch: r.pop("email_source", None)
            db().table("leads").upsert(batch, on_conflict="place_id", ignore_duplicates=True).execute()
    for i in range(0, len(rows), 200):
        upsert(rows[i:i+200])
    db().table("markets").update({"last_scraped_at": now_iso(), "businesses_found": len(existing)}).eq("market_id", market_id).execute()
    finish_run(run_id, {"new_leads": len(rows), "skipped_non_business": skipped, "market_id": market_id})
    print(f"inserted {len(rows)} leads, skipped {skipped}")

if __name__ == "__main__":
    main()
