"""Upsert gosom CSV output into Supabase leads with scoring and dedup.
Usage: python -I workers/scrape/upload.py results.csv <market_id> <run_id>
Never writes consumer listings (no category) and never re-inserts an existing place_id."""
import sys, os, csv, re, json, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db import db, finish_run, now_iso, fetch_all
from common.events import log_event

SOCIAL = {"instagram.com": "instagram_url", "linkedin.com": "linkedin_url", "facebook.com": "facebook_url"}

JUNK_DOMAINS = ("sentry", "wixpress", "wix.com", "example.com", "domain.com", "email.com", "yourdomain",
                "godaddy", "squarespace", "shopify", "schema.org", "w3.org", "googleapis", "gstatic",
                "cloudflare", "jquery", "bootstrap", "fontawesome", "mysite.com", "website.com")
JUNK_LOCAL = ("noreply", "no-reply", "donotreply", "mailer-daemon", "postmaster", "abuse", "privacy",
              "unsubscribe", "webmaster", "dmarc", "sentry", "u003e", "wixpress")
# shared inboxes a business reads (good for first contact), best first
GENERIC = ("info", "contact", "hello", "hi", "office", "admin", "enquiries", "enquiry", "inquiries", "inquiry",
           "reception", "frontdesk", "smile", "smiles", "team", "mail", "bookings", "booking", "appointments",
           "studio", "general", "clinic", "practice")
# department / role inboxes: never a named person, and the wrong door for a sales email
ROLE_INBOX = ("career", "careers", "jobs", "job", "hr", "recruit", "recruitment", "hiring", "procurement", "purchasing",
              "sales", "media", "press", "pr", "marketing", "accounts", "accounting", "billing", "invoice", "invoices",
              "finance", "support", "help", "helpdesk", "service", "services", "customerservice", "feedback",
              "complaints", "legal", "compliance", "it", "tech", "webmaster", "web", "design", "projects", "orders",
              "shop", "store", "noreply", "newsletter", "events", "partnerships", "vendors", "suppliers")
EMAIL_RE = re.compile(r"^[a-z0-9._%+-]{1,64}@[a-z0-9.-]+\.[a-z]{2,24}$")

def clean_email(e):
    """Return a plausible business email or None. Drops image names, tracker addresses, placeholders."""
    e = (e or "").strip().strip(".,;:<>()[]\"'").lower()
    if not EMAIL_RE.match(e): return None
    local, dom = e.split("@", 1)
    if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|pdf|woff2?)$", dom) or re.search(r"@\dx\.", e): return None
    if any(j in dom for j in JUNK_DOMAINS) or any(j in local for j in JUNK_LOCAL): return None
    if len(local) >= 24 and re.fullmatch(r"[0-9a-f]+", local): return None     # hex ids
    return e

def _j(v):
    try: return json.loads(v) if v and v not in ("null", "[]", "{}") else None
    except Exception: return None

def extras(r):
    """Business facts worth keeping. Reviewer names/photos are NOT stored (private individuals)."""
    reviews = []
    for rv in (_j(r.get("user_reviews")) or [])[:5]:
        txt = (rv.get("Description") or "").strip()
        if txt: reviews.append({"rating": rv.get("Rating"), "text": txt[:280]})
        if len(reviews) == 2: break
    booking = bool(_j(r.get("order_online")) or _j(r.get("reservations")))
    out = {"category": r.get("category") or None, "open_hours": _j(r.get("open_hours")),
           "price_range": r.get("price_range") or None, "description": (r.get("descriptions") or "")[:500] or None,
           "online_booking": booking, "lat": r.get("latitude") or None, "lng": r.get("longitude") or None,
           "review_excerpts": reviews or None}
    return {k: v for k, v in out.items() if v not in (None, "", [])}

def _local(e):
    return e.split("@")[0].lower()

def email_quality(e):
    """named = looks like a person (john@, john.smith@, jsmith@); otherwise generic."""
    local = _local(e)
    base = re.split(r"[.\-_+0-9]", local)[0]
    if local in GENERIC or local in ROLE_INBOX or base in GENERIC or base in ROLE_INBOX:
        return "generic"
    return "named"

def email_rank(e):
    """Sort key: named people first, then the main shared inbox (info@, contact@), then departments."""
    local = _local(e); base = re.split(r"[.\-_+0-9]", local)[0]
    if email_quality(e) == "named": return 0
    if local in GENERIC or base in GENERIC: return 1 + GENERIC.index(local if local in GENERIC else base) / 100
    return 2

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
    if re.search(r"\b(inc|group|corporation|corp|franchise|holdings)\b", name): s -= 15   # whole words only
    return max(0, min(s, 100))

def main():
    path, market_id, run_id = sys.argv[1:4]
    log_event("scrape", "info", "upload started for %s" % market_id, {"run_id": run_id})
    market = db().table("markets").select("*").eq("market_id", market_id).single().execute().data
    existing = {r["place_id"] for r in fetch_all(db().table("leads").select("place_id").eq("market_id", market_id).order("place_id"))}
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
                "contact_quality": "none",
                "notes": ("maps owner field: " + r["owner"]) if r.get("owner") else None,
                "scraped_at": now_iso(),
                "extra": extras(r), "timezone": r.get("timezone") or None,
            }
            emails = [c for c in (clean_email(e) for e in re.split(r"[,; ]+", r.get("emails") or "")) if c]
            # prefer a named address over a generic one, and the site's own domain over others
            site_dom = re.sub(r"^https?://(www\.)?", "", r.get("website") or "").split("/")[0].lower()
            emails.sort(key=lambda e: (email_rank(e), site_dom not in e))
            if emails:
                lead["primary_email"] = emails[0]
                lead["email_source"] = "website"   # gosom -email reads the business's own site
                lead["contact_quality"] = email_quality(emails[0])
            else:
                lead["contact_quality"] = "none"   # an owner name alone is not a contact yet
            for host, col in SOCIAL.items():
                m = re.search(r"https?://(?:www\.)?" + re.escape(host) + r"/[\w./-]+", r.get("about", "") + " " + r.get("website", ""))
                if m: lead[col] = m.group(0)
            rows.append(lead)
    def upsert(batch):
        try:
            db().table("leads").upsert(batch, on_conflict="place_id", ignore_duplicates=True).execute()
        except Exception as e:  # newer columns not migrated yet -> retry without them
            if not any(c in str(e) for c in ("email_source", "extra", "timezone")): raise
            for r in batch:
                for c in ("email_source", "extra", "timezone"): r.pop(c, None)
            db().table("leads").upsert(batch, on_conflict="place_id", ignore_duplicates=True).execute()
    for i in range(0, len(rows), 200):
        upsert(rows[i:i+200])
    db().table("markets").update({"last_scraped_at": now_iso(), "businesses_found": len(existing)}).eq("market_id", market_id).execute()
    finish_run(run_id, {"new_leads": len(rows), "skipped_non_business": skipped, "market_id": market_id})
    print(f"inserted {len(rows)} leads, skipped {skipped}")
    log_event("scrape", "info", "upload finished for %s: %d new leads, %d skipped" % (market_id, len(rows), skipped),
              {"run_id": run_id, "market_id": market_id, "new_leads": len(rows)})

if __name__ == "__main__":
    main()
