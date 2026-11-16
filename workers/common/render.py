"""Page fetching for audit/enrich: plain HTTP first; if the page is a JavaScript shell (Wix, React,
Squarespace builders) fall back to a real headless Chromium (Playwright), the same approach Firecrawl
uses, but run only inside GitHub Actions. Never runs on the VPS. Respects a short timeout per page."""
import re, requests
from typing import Optional, Tuple

UA = "ARVIS-audit/1.0 (+https://armedias.com; site health check)"
_pw = None; _browser = None

def visible_text_len(html_text: str) -> int:
    t = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", html_text or "")
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return len(" ".join(t.split()))

def looks_like_js_shell(html_text: str) -> bool:
    low = (html_text or "").lower()
    return visible_text_len(html_text) < 400 or any(k in low for k in ('id="__next"></div>', 'id="root"></div>', "wix-warmup-data", "please enable javascript"))

def _browser_get(url: str) -> Optional[str]:
    global _pw, _browser
    try:
        if _browser is None:
            from playwright.sync_api import sync_playwright
            _pw = sync_playwright().start()
            _browser = _pw.chromium.launch(args=["--no-sandbox"])
        page = _browser.new_page(user_agent=UA)
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            return page.content()
        finally:
            page.close()
    except Exception:
        return None

def fetch(url: str, allow_browser: bool = True) -> Tuple[Optional[requests.Response], str, bool]:
    """Returns (response or None, html, rendered_with_browser)."""
    resp, html = None, ""
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=15, allow_redirects=True)
        if "text/html" in resp.headers.get("content-type", "") or resp.text.lstrip().startswith("<"):
            html = resp.text
    except requests.exceptions.SSLError:
        raise
    except Exception:
        resp = None
    if allow_browser and (not html or looks_like_js_shell(html)):
        rendered = _browser_get(resp.url if resp is not None else url)
        if rendered and visible_text_len(rendered) > visible_text_len(html):
            return resp, rendered, True
    return resp, html, False

def close():
    global _pw, _browser
    try:
        if _browser: _browser.close()
        if _pw: _pw.stop()
    except Exception:
        pass
    _browser = None; _pw = None
