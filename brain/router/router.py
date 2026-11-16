#!/usr/bin/env python3
"""arvis-router — one OpenAI-compatible endpoint in front of several FREE LLM providers, with failover.

Hermes talks to http://127.0.0.1:8090/v1 as if it were a single model called "arvis-router".
For each request the router tries providers in order and moves on when one answers 429/5xx,
times out, or returns an error body. Streaming is passed through once a provider starts
answering. Providers whose key is missing are skipped. Order and models come from /opt/arvis/.env:

  ROUTER_ORDER=gemini-lite,gemini,cerebras,nvidia,groq,openrouter-free     (default)
  GOOGLE_API_KEY / CEREBRAS_API_KEY / NVIDIA_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY
  GEMINI_LITE_MODEL=gemini-3.5-flash-lite  GEMINI_MODEL=gemini-3.8-flash
  CEREBRAS_MODEL=gpt-oss-120b  NVIDIA_MODEL=openai/gpt-oss-120b  GROQ_MODEL=openai/gpt-oss-120b
  OPENROUTER_FREE_MODEL=nvidia/nemotron-3.5-super-vl:free
  ROUTER_PORT=8090  ROUTER_LOG=/opt/arvis/logs/router.log

Groq's free tier rejects big prompts, so it is only tried when the request is small
(GROQ_MAX_CHARS, default 24000 chars ≈ 6k tokens). Zero dependencies beyond aiohttp.
"""
import os, sys, json, time, asyncio, logging, datetime as dt
from aiohttp import web, ClientSession, ClientTimeout

def load_env(path=os.environ.get("ARVIS_ENV", "/opt/arvis/.env")):
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

E = os.environ.get
PROVIDERS = {
    "gemini-lite":     {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "key": E("GOOGLE_API_KEY"),     "model": E("GEMINI_LITE_MODEL", "gemini-3.5-flash-lite")},
    "gemini":          {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "key": E("GOOGLE_API_KEY"),     "model": E("GEMINI_MODEL", "gemini-3.8-flash")},
    "cerebras":        {"url": "https://api.cerebras.ai/v1/chat/completions",                               "key": E("CEREBRAS_API_KEY"),   "model": E("CEREBRAS_MODEL", "gpt-oss-120b")},
    "nvidia":          {"url": "https://integrate.api.nvidia.com/v1/chat/completions",                     "key": E("NVIDIA_API_KEY"),     "model": E("NVIDIA_MODEL", "openai/gpt-oss-120b")},
    "groq":            {"url": "https://api.groq.com/openai/v1/chat/completions",                           "key": E("GROQ_API_KEY"),       "model": E("GROQ_MODEL", "openai/gpt-oss-120b"), "max_chars": int(E("GROQ_MAX_CHARS", "24000"))},
    "openrouter-free": {"url": "https://openrouter.ai/api/v1/chat/completions",                             "key": E("OPENROUTER_API_KEY"), "model": E("OPENROUTER_FREE_MODEL", "nvidia/nemotron-3.5-super-vl:free")},
    # free, no card: GitHub Models (fine-grained token with "Models: Read"), Mistral "Experiment" plan
    "github":          {"url": "https://models.github.ai/inference/chat/completions",                       "key": E("GITHUB_MODELS_TOKEN"), "model": E("GITHUB_MODELS_MODEL", "openai/gpt-4.1-mini"), "max_chars": int(E("GITHUB_MAX_CHARS", "28000"))},
    "mistral":         {"url": "https://api.mistral.ai/v1/chat/completions",                                "key": E("MISTRAL_API_KEY"),    "model": E("MISTRAL_MODEL", "mistral-small-latest")},
    # Modal-hosted DeepSeek (Modal proxy auth: Modal-Key / Modal-Secret headers). Shared endpoints need
    # billing on the Modal account, so it is NOT in the default order; add "modal" to ROUTER_ORDER to use it.
    "modal":           {"url": (E("MODAL_BASE_URL") or "").rstrip("/") + "/chat/completions",                "key": E("MODAL_KEY"),          "model": E("MODAL_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash"),
                        "headers": {"Modal-Key": E("MODAL_KEY") or "", "Modal-Secret": E("MODAL_SECRET") or ""}},
}
ORDER = [p.strip() for p in E("ROUTER_ORDER", "gemini-lite,cerebras,mistral,nvidia,github,gemini,groq,openrouter-free").split(",") if p.strip() in PROVIDERS]
MAX_REQ_CHARS = int(E("ROUTER_MAX_REQ_CHARS", "160000"))   # ≈40k tokens; older turns are trimmed above this
RETRY_WAITS = [int(x) for x in E("ROUTER_RETRY_WAITS", "8,25").split(",") if x.strip()]
PORT = int(E("ROUTER_PORT", "8090"))
RETRY_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504, 529}
COOLDOWN = {}   # provider -> unix time until which it is skipped (after a 429)

logging.basicConfig(filename=E("ROUTER_LOG") or None, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("router")

def active_providers(req_chars):
    now = time.time()
    for name in ORDER:
        p = PROVIDERS[name]
        if not p["key"]: continue
        if COOLDOWN.get(name, 0) > now: continue
        if p.get("max_chars") and req_chars > p["max_chars"]: continue
        yield name, p

def trim_history(body):
    """Keep system messages + the most recent turns so the request stays under MAX_REQ_CHARS.
    The kept tail always starts at a user message, so tool calls never lose their results."""
    msgs = body.get("messages") or []
    if len(json.dumps(body)) <= MAX_REQ_CHARS or len(msgs) < 4:
        return body, 0
    system = [m for m in msgs if m.get("role") == "system"]
    rest = [m for m in msgs if m.get("role") != "system"]
    tools_chars = len(json.dumps(body.get("tools") or []))
    budget = MAX_REQ_CHARS - tools_chars - len(json.dumps(system))
    tail, size = [], 0
    for m in reversed(rest):
        s = len(json.dumps(m))
        if size + s > budget and tail: break
        tail.insert(0, m); size += s
    while tail and tail[0].get("role") != "user":   # never start on a tool/assistant fragment
        tail.pop(0)
    if not tail:
        tail = [m for m in rest if m.get("role") == "user"][-1:]
    dropped = len(rest) - len(tail)
    note = {"role": "system", "content": f"[{dropped} earlier messages trimmed to fit the model's limits]"}
    return {**body, "messages": system + [note] + tail}, dropped

def parse_retry_after(resp):
    try: return max(5, min(300, int(float(resp.headers.get("Retry-After", "60")))))
    except Exception: return 60

async def try_provider(session, name, p, body, stream):
    payload = dict(body); payload["model"] = p["model"]
    payload.pop("user", None)
    headers = {"Content-Type": "application/json", **(p.get("headers") or {"Authorization": f"Bearer {p['key']}"})}
    if name == "openrouter-free": headers["HTTP-Referer"] = "https://armedias.com"; headers["X-Title"] = "ARVIS"
    resp = await session.post(p["url"], json=payload, headers=headers, timeout=ClientTimeout(total=180, sock_connect=15, sock_read=90))
    if resp.status in RETRY_STATUSES:
        txt = " ".join((await resp.text()).split())[:300]; resp.release()
        if resp.status == 429: COOLDOWN[name] = time.time() + parse_retry_after(resp)
        if any(w in txt.lower() for w in ("payment method", "spend limit", "billing", "insufficient credit", "quota exceeded for this month")):
            COOLDOWN[name] = time.time() + 3600   # billing problem: no point retrying soon
        raise RuntimeError(f"{name} HTTP {resp.status}: {txt}")
    if resp.status >= 400:
        txt = " ".join((await resp.text()).split())[:300]; resp.release()
        raise RuntimeError(f"{name} HTTP {resp.status}: {txt}")
    return resp

async def chat(request):
    body = await request.json()
    body, dropped = trim_history(body)
    if dropped: log.info("trimmed %d old messages", dropped)
    stream = bool(body.get("stream"))
    req_chars = len(json.dumps(body))
    errors = []
    async with ClientSession() as session:
        for attempt in range(len(RETRY_WAITS) + 1):
            if attempt:
                wait = RETRY_WAITS[attempt - 1]
                log.warning("all providers busy; waiting %ss before retry %d", wait, attempt)
                await asyncio.sleep(wait)
                for k in list(COOLDOWN):        # give providers whose cooldown is nearly over another chance
                    if COOLDOWN[k] - time.time() < wait: COOLDOWN.pop(k, None)
            for name, p in active_providers(req_chars):
                t0 = time.time()
                try:
                    resp = await try_provider(session, name, p, body, stream)
                except Exception as e:
                    errors.append(str(e)[:200]); log.warning("failover: %s", str(e)[:200]); continue
                log.info("served by %s (%s) in %.1fs stream=%s chars=%d", name, p["model"], time.time() - t0, stream, req_chars)
                if not stream:
                    data = await resp.json(content_type=None)
                    ch = (data.get("choices") or [{}])[0]; msg = ch.get("message") or {}
                    if not data.get("choices") or (not (msg.get("content") or "").strip() and not msg.get("tool_calls")):
                        errors.append(f"{name}: empty answer"); log.warning("failover: %s returned an empty answer", name); continue
                    data["model"] = f"arvis-router/{name}"
                    return web.json_response(data)
                out = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "X-Arvis-Provider": name})
                await out.prepare(request)
                try:
                    async for chunk in resp.content.iter_any():
                        await out.write(chunk)
                finally:
                    await out.write_eof()
                return out
    msg = "all providers failed: " + " | ".join(errors[-6:]) if errors else "no provider configured (set GOOGLE_API_KEY etc. in /opt/arvis/.env)"
    log.error(msg)
    return web.json_response({"error": {"message": msg, "type": "router_exhausted", "code": 503}}, status=503)

async def models(request):
    return web.json_response({"object": "list", "data": [{"id": "arvis-router", "object": "model", "owned_by": "arvis", "context_length": 1000000,
                                                          "providers": [n for n, _ in active_providers(0)]}]})

async def health(request):
    return web.json_response({"ok": True, "order": ORDER, "configured": [n for n in ORDER if PROVIDERS[n]["key"]],
                              "cooldown": {k: int(v - time.time()) for k, v in COOLDOWN.items() if v > time.time()}, "time": dt.datetime.utcnow().isoformat()})

app = web.Application(client_max_size=64 * 1024 * 1024)
app.add_routes([web.post("/v1/chat/completions", chat), web.get("/v1/models", models), web.get("/health", health)])

if __name__ == "__main__":
    print(f"arvis-router on 127.0.0.1:{PORT}; order={ORDER}; configured={[n for n in ORDER if PROVIDERS[n]['key']]}", flush=True)
    web.run_app(app, host="127.0.0.1", port=PORT, print=None, access_log=None)
