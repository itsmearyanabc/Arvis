"""Audit websites of leads with status=new. Plain HTTP + optional PageSpeed Insights.
Usage: python -I workers/audit/audit.py [limit]
Max 3 requests per site, honest User-Agent, respects robots.txt for the pages fetched."""
import sys, os, re, time, random, datetime as dt
import requests
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db import db, start_run, finish_run, now_iso
from common import render

UA = "ARVIS-audit/1.0 (+https://armedias.com; site health check)"
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

def fetch(url):
    return requests.get(url, headers={"User-Agent": UA}, timeout=15, allow_redirects=True)

def psi(url):
    key = os.environ.get("PSI_API_KEY")
    try:
        r = requests.get(PSI, params={"url": url, "strategy": "mobile", "category": "performance", **({"key": key} if key else {})}, timeout=60).json()
        lh = r["lighthouseResult"]
        return int(lh["categories"]["performance"]["score"] * 100), round(lh["audits"]["largest-contentful-paint"]["numericValue"] / 1000, 1)
    except Exception:
        return None, None

def audit(lead):
    url = lead["website"]
    if not url.startswith("http"): url = "https://" + url
    a = {"lead_id": lead["lead_id"], "website": url, "checked_at": now_iso()}
    try:
        r, html, rendered = render.fetch(url)
    except requests.exceptions.SSLError:
        a["ssl_ok"] = False
        try: r, html, rendered = render.fetch(url.replace("https://", "http://"))
        except Exception: a["site_status"] = "down"; return a
    if r is None and not html:
        a["site_status"] = "down"; return a
    a["site_status"] = "ok" if (r is None or r.status_code < 500) else "down"
    final_url = r.url if r is not None else url
    a.setdefault("ssl_ok", final_url.startswith("https://"))
    a["https_redirect"] = final_url.startswith("https://")
    a["rendered_with_browser"] = rendered
    html = (html or "")[:600_000]; soup = BeautifulSoup(html, "html.parser")
    a["has_title"] = bool(soup.title and soup.title.string and soup.title.string.strip())
    a["has_meta_desc"] = bool(soup.find("meta", attrs={"name": re.compile("^description$", re.I)}))
    a["h1_count"] = len(soup.find_all("h1"))
    imgs = soup.find_all("img"); a["img_alt_missing_pct"] = round(100 * sum(1 for i in imgs if not i.get("alt")) / len(imgs), 1) if imgs else 0
    low = html.lower()
    a["cms"] = "wordpress" if "wp-content" in low else "wix" if "wix.com" in low else "squarespace" if "squarespace" in low else "shopify" if "cdn.shopify" in low else "unknown"
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", low)]
    a["copyright_year"] = max(years) if years else None
    a["looks_outdated"] = bool((a["copyright_year"] and a["copyright_year"] <= dt.date.today().year - 3) or not soup.find("meta", attrs={"name": "viewport"}))
    a["contact_email_on_site"] = bool(re.search(r"mailto:|[\w.+-]+@[\w-]+\.[a-z]{2,}", low))
    a["contact_form"] = bool(soup.find("form"))
    a["booking_widget"] = any(k in low for k in ("calendly", "cal.com", "acuity", "book now", "zocdoc"))
    a["meta_pixel"] = "connect.facebook.net" in low or "fbq(" in low
    a["google_tag"] = "googletagmanager" in low or "gtag(" in low
    a["perf_score"], a["lcp_s"] = psi(url); a["mobile_score"] = a["perf_score"]
    issues = []
    if not a["ssl_ok"]: issues.append("no valid SSL certificate")
    if a["perf_score"] is not None and a["perf_score"] < 50: issues.append(f"slow on mobile (PageSpeed {a['perf_score']}/100, LCP {a['lcp_s']}s)")
    if a["looks_outdated"]: issues.append("design looks outdated" + (f" (copyright {a['copyright_year']})" if a["copyright_year"] else " (not mobile-ready)"))
    if not a["has_meta_desc"]: issues.append("missing meta description")
    if not a["contact_form"] and not a["booking_widget"]: issues.append("no way to enquire or book online")
    a["top_issue"] = issues[0] if issues else None
    a["audit_summary"] = ("Site is live. Issues: " + "; ".join(issues[:3]) + ".") if issues else "Site is live and looks healthy on the basics."
    return a

def bump(lead, a):
    s = lead["ticket_score"] or 0
    if a.get("site_status") == "down": s += 25
    if a.get("ssl_ok") is False: s += 20
    if (a.get("perf_score") or 100) < 50: s += 15
    if a.get("looks_outdated"): s += 15
    if a.get("meta_pixel") or a.get("google_tag"): s += 10
    return min(s, 100)

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    run_id = start_run("audit", {"limit": limit})
    leads = db().table("leads").select("*").eq("status", "new").not_.is_("website", "null").order("ticket_score", desc=True).limit(limit).execute().data
    done, failed = 0, []
    try:
        for lead in leads:
            try:                                   # one odd site must never stop the whole run
                a = audit(lead)
                try: db().table("audits").insert(a).execute()
                except Exception as e:   # migration 004 not applied yet
                    if "rendered_with_browser" not in str(e): raise
                    a.pop("rendered_with_browser", None); db().table("audits").insert(a).execute()
                db().table("leads").update({"status": "audited", "ticket_score": bump(lead, a), "top_issue": a.get("top_issue"),
                                            "audit_summary": a.get("audit_summary"), "updated_at": now_iso()}).eq("lead_id", lead["lead_id"]).execute()
                done += 1
            except Exception as e:
                failed.append(f"{lead['lead_id']}: {str(e)[:120]}"); print("audit skipped", lead["lead_id"], e)
            time.sleep(random.uniform(5, 20))
    finally:
        render.close()
    finish_run(run_id, {"audited": done, "failed": len(failed)}, error=("; ".join(failed[:5]) if failed and not done else None))
    # leads with no website at all: mark audited with no_site so enrich can still run
    nosite = db().table("leads").select("lead_id").eq("status", "new").is_("website", None).limit(limit).execute().data
    for l in nosite:
        db().table("audits").insert({"lead_id": l["lead_id"], "site_status": "no_site", "top_issue": "no website", "audit_summary": "No website found on the Maps listing."}).execute()
        db().table("leads").update({"status": "audited", "top_issue": "no website", "audit_summary": "No website found on the Maps listing."}).eq("lead_id", l["lead_id"]).execute()
    print(f"audited {done}, no-site {len(nosite)}")

if __name__ == "__main__":
    main()
