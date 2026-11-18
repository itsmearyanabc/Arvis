"""Enrich worker (Phase 3b): find a named decision-maker + email for audited businesses, from PUBLIC
sources only: the business's own website pages, Brave Search snippets, Hunter.io (free tier, high
ticket only). Writes candidate rows to `contacts` with email_status=unknown; verification happens on
the VPS (`arvisctl verify`, self-hosted Reacher). Never touches LinkedIn/Instagram/Facebook.
Usage: python -I workers/enrich/enrich.py [limit]"""
import sys, os, re, json, time, random, html
import requests
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scrape"))
from common.db import db, start_run, finish_run, now_iso, fetch_all
from common.events import log_event
from common import render
from upload import clean_email, email_quality, email_rank

ROLE_WORDS = {"founder", "co-founder", "director", "owner", "principal", "partner", "manager", "ceo", "md", "dr", "dentist",
              "lead", "managing", "practice", "clinic", "senior", "head", "chief", "officer", "president", "team", "our", "the"}
def clean_name(n):
    """'Amanda Dsouza Founder' -> 'Amanda Dsouza': drop role words around a scraped name."""
    words = [w for w in (n or "").replace(",", " ").split() if w.lower().strip(".") not in ROLE_WORDS]
    return " ".join(words[:3]) or None

UA = "ARVIS-enrich/1.0 (+https://armedias.com; business contact lookup)"
PAGES = ["", "/contact", "/contact-us", "/about", "/about-us", "/team", "/our-team", "/meet-the-team"]
ROLE_RE = re.compile(r"\b(owner|founder|co-founder|director|principal|managing partner|partner|ceo|md|practice manager|clinic manager|lead dentist|principal dentist|dr\.?)\b", re.I)
NAME_RE = re.compile(r"\b((?:Dr\.?\s+)?[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z'’-]{1,20}){1,2})\b")
SOCIAL = {"instagram.com": "instagram_url", "linkedin.com": "linkedin_url", "facebook.com": "facebook_url"}
BRAVE = os.environ.get("BRAVE_SEARCH_API_KEY"); HUNTER = os.environ.get("HUNTER_API_KEY")
GCSE_KEY = os.environ.get("GOOGLE_CSE_API_KEY"); GCSE_ID = os.environ.get("GOOGLE_CSE_ID")   # Programmable Search: 100 queries/day free, no card
HUNTER_BUDGET = int(os.environ.get("HUNTER_RUN_BUDGET", "5"))   # domain searches per run (free tier: 25/mo)

def fetch(url, browser=True):
    try:
        r, html, _ = render.fetch(url, allow_browser=browser)
        return html if (r is None or r.status_code < 400) else ""
    except Exception:
        return ""

def site_root(website):
    if not website: return None
    if not website.startswith("http"): website = "https://" + website
    return re.sub(r"/+$", "", website.split("?")[0].split("#")[0]) if website.count("/") <= 2 else "/".join(website.split("/")[:3])

def extract(html_text, site_dom):
    """emails, names-with-roles, social links from one page."""
    emails, people, socials = set(), [], {}
    text = html.unescape(html_text)
    for e in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        c = clean_email(e)
        if c: emails.add(c)
    soup = BeautifulSoup(text, "html.parser")
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.lower().startswith("mailto:"):
            c = clean_email(h[7:].split("?")[0])
            if c: emails.add(c)
        for host, col in SOCIAL.items():
            if host in h and col not in socials: socials[col] = h.split("?")[0]
    for s in soup.find_all("script", type="application/ld+json"):
        try: data = json.loads(s.string or "")
        except Exception: continue
        for obj in (data if isinstance(data, list) else [data]):
            if not isinstance(obj, dict): continue
            for key in ("founder", "employee", "employees", "member"):
                v = obj.get(key)
                for p in (v if isinstance(v, list) else [v]):
                    if isinstance(p, dict) and p.get("name"): people.append((p["name"], p.get("jobTitle") or key, "website"))
            if obj.get("@type") == "Person" and obj.get("name"): people.append((obj["name"], obj.get("jobTitle") or "person", "website"))
    body = soup.get_text(" ", strip=True)
    for m in ROLE_RE.finditer(body):
        window = body[max(0, m.start() - 60): m.end() + 60]
        for n in NAME_RE.findall(window):
            if n.split()[0].lower() in ("our", "the", "meet", "contact", "about", "team", "dental", "clinic"): continue
            people.append((n.strip(), m.group(1), "website"))
    return emails, people, socials

def web_search(q):
    """Public web search snippets: Google Programmable Search (free tier) first, Brave if configured."""
    if GCSE_KEY and GCSE_ID:
        try:
            r = requests.get("https://www.googleapis.com/customsearch/v1", params={"key": GCSE_KEY, "cx": GCSE_ID, "q": q, "num": 5}, timeout=15).json()
            if "items" in r:
                return [(x.get("title", ""), x.get("snippet", ""), x.get("link", "")) for x in r["items"]]
        except Exception:
            pass
    if BRAVE:
        try:
            r = requests.get("https://api.search.brave.com/res/v1/web/search", params={"q": q, "count": 5},
                             headers={"X-Subscription-Token": BRAVE, "Accept": "application/json"}, timeout=15)
            return [(x.get("title", ""), x.get("description", ""), x.get("url", "")) for x in r.json().get("web", {}).get("results", [])]
        except Exception:
            pass
    return []

def hunter_domain(domain):
    if not HUNTER: return []
    try:
        r = requests.get("https://api.hunter.io/v2/domain-search", params={"domain": domain, "api_key": HUNTER, "limit": 5}, timeout=20).json()
        return [(e.get("value"), (e.get("first_name") or "") + " " + (e.get("last_name") or ""), e.get("position") or "", e.get("confidence", 0)) for e in r.get("data", {}).get("emails", [])]
    except Exception:
        return []

def enrich(lead, hunter_left):
    root = site_root(lead.get("website"))
    emails, people, socials = set(), [], {}
    dom = re.sub(r"^https?://(www\.)?", "", root or "").split("/")[0].lower()
    email_src = {}                                # email -> where it was found
    if root:
        for i, p in enumerate(PAGES[:5]):
            h = fetch(root + p, browser=(i < 2))      # browser only for home + first contact page
            if not h: continue
            e, pe, so = extract(h, dom); emails |= e; people += pe; socials = {**so, **socials}
            for x in e: email_src.setdefault(x, "website")
            time.sleep(random.uniform(1, 3))
    # public search: owner name + sometimes an email in the snippet
    for title, desc, url in web_search(f'"{lead["business_name"]}" {lead.get("city","")} owner OR founder OR director'):
        if any(b in url for b in ("linkedin.com", "instagram.com", "facebook.com")):   # store nothing from social hosts
            continue
        for e in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", desc):
            c = clean_email(e)
            if c and (dom and dom in c): emails.add(c); email_src.setdefault(c, "web_search")
        for m in ROLE_RE.finditer(desc):
            for n in NAME_RE.findall(desc[max(0, m.start()-60): m.end()+60]): people.append((n, m.group(1), "web_search"))
    used_hunter = False
    if dom and hunter_left > 0 and (lead.get("ticket_score") or 0) >= 70 and not any(email_quality(e) == "named" for e in emails):
        for value, name, pos, conf in hunter_domain(dom):
            c = clean_email(value)
            if c: emails.add(c); email_src.setdefault(c, "hunter"); people.append((name.strip() or None, pos, "hunter"))
        used_hunter = True
    # rank: named + own domain first
    ranked = sorted(emails, key=lambda e: (email_rank(e), dom not in e))
    # best person
    best_person = None
    for n, role, origin in people:
        n = clean_name(n)
        if n and len(n.split()) >= 2 and len(n) < 50: best_person = (n, role, origin); break
    return ranked, best_person, socials, used_hunter, email_src

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_id = start_run("enrich", {"limit": limit, "search": "google" if GCSE_KEY and GCSE_ID else ("brave" if BRAVE else "none"), "hunter": bool(HUNTER)})
    log_event("audit", "info", f"enrich run started (limit {limit})")
    # audited businesses not yet enriched (= no contacts rows yet); verify later moves them to verified/parked
    # all audited ids (paged), minus those already enriched -> best `limit` by ticket score
    have = {c["lead_id"] for c in fetch_all(db().table("contacts").select("lead_id").order("contact_id"))}
    cand = [l for l in fetch_all(db().table("leads").select("lead_id,ticket_score").eq("status", "audited").order("lead_id"))
            if l["lead_id"] not in have]
    pick = [l["lead_id"] for l in sorted(cand, key=lambda l: -(l["ticket_score"] or 0))[:limit]]
    leads = db().table("leads").select("*").in_("lead_id", pick).execute().data if pick else []
    leads.sort(key=lambda l: -(l["ticket_score"] or 0))
    failed = []
    hunter_left, found_named, found_any, done = HUNTER_BUDGET, 0, 0, 0
    try:
        for lead in leads:
          try:                                       # one odd site must never stop the whole run
            ranked, person, socials, used_h, src = enrich(lead, hunter_left)
            if used_h: hunter_left -= 1
            rows = []
            for e in ranked[:3]:
                rows.append({"lead_id": lead["lead_id"], "email": e, "email_status": "unknown",
                             "email_source": src.get(e, "website"),
                             "contact_quality": email_quality(e),
                             "contact_name": person[0] if person and email_quality(e) == "named" else None,
                             "role": person[1] if person and email_quality(e) == "named" else None})
            if rows:
                existing = {c["email"] for c in db().table("contacts").select("email").eq("lead_id", lead["lead_id"]).execute().data}
                rows = [r for r in rows if r["email"] not in existing]
                if rows: db().table("contacts").insert(rows).execute()
                found_any += 1
                if email_quality(ranked[0]) == "named": found_named += 1
            upd = {k: v for k, v in socials.items() if v and not lead.get(k)}
            if ranked and (not lead.get("primary_email") or (email_quality(ranked[0]) == "named" and lead.get("contact_quality") != "named")):
                upd.update({"primary_email": ranked[0], "email_source": src.get(ranked[0], "website"), "contact_quality": email_quality(ranked[0])})
            if person and not (lead.get("notes") or "").startswith("owner:"):
                upd["notes"] = f"owner: {person[0]} ({person[1]})" + (f" | {lead['notes']}" if lead.get("notes") else "")
            if not ranked: upd.update({"status": "parked", "parked_reason": "no_email"})
            upd["updated_at"] = now_iso()
            db().table("leads").update(upd).eq("lead_id", lead["lead_id"]).execute()
            done += 1
          except Exception as e:
            failed.append(f"{lead['lead_id']}: {str(e)[:120]}"); print("enrich skipped", lead["lead_id"], e)
          time.sleep(random.uniform(3, 8))
        render.close()
        finish_run(run_id, {"processed": done, "failed": len(failed), "with_email": found_any, "named": found_named, "hunter_used": HUNTER_BUDGET - hunter_left},
                   error=("; ".join(failed[:5]) if failed and not done else None))
        log_event("audit", "info", f"enrich done: {done} processed, {found_any} with email, {found_named} named")
    except Exception as e:
        finish_run(run_id, {"processed": done}, error=str(e)); log_event("audit", "error", f"enrich failed: {e}"); raise
    print(f"enriched {done}: {found_any} with email, {found_named} named")

if __name__ == "__main__":
    main()
