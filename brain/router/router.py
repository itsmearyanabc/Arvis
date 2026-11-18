#!/usr/bin/env python3
"""arvis-router — one OpenAI-compatible endpoint in front of several FREE LLM providers, with failover.

Hermes talks to http://127.0.0.1:8090/v1 as if it were a single model called "arvis-router".
For each request the router tries providers in order and moves on when one answers 429/5xx,
times out, or returns an error body. Streaming is passed through once a provider starts
answering. Providers whose key is missing are skipped. Order and models come from /opt/arvis/.env:

  ROUTER_ORDER / ROUTER_BATCH_ORDER  (chat lane: smart first; background lane "arvis-batch": light first)
  per-provider free budgets (rpm/rpd/tpm), 2-min cooldown for overloaded models, hedged chat requests
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
G_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
CF_URL = f"https://api.cloudflare.com/client/v4/accounts/{E('CF_ACCOUNT_ID', '')}/ai/v1/chat/completions"
# Each provider: url, key, model, free-tier budget (rpm = requests/minute, rpd = requests/day,
# tpm = tokens/minute; 0 = unknown/unlimited), tier ("smart" or "light"). Every Gemini MODEL has its
# own free quota, so one Google key gives several independent buckets. All values overridable via env.
def P(url, key, model, rpm, rpd, tpm=0, tier="light", **kw):
    return {"url": url, "key": key, "model": model, "rpm": rpm, "rpd": rpd, "tpm": tpm, "tier": tier, **kw}
PROVIDERS = {
    "gemini":          P(G_URL, E("GOOGLE_API_KEY"), E("GEMINI_MODEL", "gemini-3.8-flash"), 10, 250, tier="smart"),
    "gemini-37":       P(G_URL, E("GOOGLE_API_KEY"), E("GEMINI_37_MODEL", "gemini-3.7-flash"), 10, 250, tier="smart"),
    "gemini-35":       P(G_URL, E("GOOGLE_API_KEY"), E("GEMINI_35_MODEL", "gemini-3.5-flash"), 10, 250, tier="smart"),
    "gemini-lite":     P(G_URL, E("GOOGLE_API_KEY"), E("GEMINI_LITE_MODEL", "gemini-3.5-flash-lite"), 15, 1000),
    "gemini-lite-31":  P(G_URL, E("GOOGLE_API_KEY"), E("GEMINI_LITE31_MODEL", "gemini-3.1-flash-lite"), 15, 1000),
    # GitHub Models: free with any GitHub account; token needs Account permission "Models: Read"
    "github":          P("https://models.github.ai/inference/chat/completions", E("GITHUB_MODELS_TOKEN"), E("GITHUB_MODELS_MODEL", "openai/gpt-4.1"), 10, 50, tier="smart", max_chars=int(E("GITHUB_MAX_CHARS", "28000"))),
    "github-mini":     P("https://models.github.ai/inference/chat/completions", E("GITHUB_MODELS_TOKEN"), E("GITHUB_MINI_MODEL", "openai/gpt-4.1-mini"), 15, 150, max_chars=int(E("GITHUB_MAX_CHARS", "28000"))),
    # Cloudflare Workers AI: free daily allowance; needs CF_ACCOUNT_ID + CF_API_TOKEN ("Workers AI" permission)
    "cloudflare":      P(CF_URL, E("CF_API_TOKEN") if E("CF_ACCOUNT_ID") else None, E("CF_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"), 30, 300, tier="smart"),
    "groq":            P("https://api.groq.com/openai/v1/chat/completions", E("GROQ_API_KEY"), E("GROQ_MODEL", "openai/gpt-oss-120b"), 30, 1000, 8000, max_chars=int(E("GROQ_MAX_CHARS", "24000"))),
    "cerebras":        P("https://api.cerebras.ai/v1/chat/completions", E("CEREBRAS_API_KEY"), E("CEREBRAS_MODEL", "gpt-oss-120b"), 30, 14400, 60000),
    "mistral":         P("https://api.mistral.ai/v1/chat/completions", E("MISTRAL_API_KEY"), E("MISTRAL_MODEL", "mistral-small-latest"), 60, 0),
    "nvidia":          P("https://integrate.api.nvidia.com/v1/chat/completions", E("NVIDIA_API_KEY"), E("NVIDIA_MODEL", "openai/gpt-oss-120b"), 40, 0),
    "openrouter-free": P("https://openrouter.ai/api/v1/chat/completions", E("OPENROUTER_API_KEY"), E("OPENROUTER_FREE_MODEL", "nvidia/nemotron-3.5-super-vl:free"), 20, 50),
    # Modal-hosted model (needs billing on Modal) — only used if listed in ROUTER_ORDER
    "modal":           P((E("MODAL_BASE_URL") or "").rstrip("/") + "/chat/completions", E("MODAL_KEY"), E("MODAL_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash"), 60, 0, tier="smart",
                         headers={"Modal-Key": E("MODAL_KEY") or "", "Modal-Secret": E("MODAL_SECRET") or ""}),
}
for _n, _p in PROVIDERS.items():          # per-provider env overrides, e.g. ROUTER_RPM_GEMINI_LITE=20
    _k = _n.upper().replace("-", "_")
    for _f in ("rpm", "rpd", "tpm"):
        if E(f"ROUTER_{_f.upper()}_{_k}"): _p[_f] = int(E(f"ROUTER_{_f.upper()}_{_k}"))
# Conversation lane (Aryan on Telegram): strongest model with room first. Background lane
# (model "arvis-batch"): light models first, and it may only use a provider while 30 % of that
# provider's budget is still free, so it can never use up what the conversation needs.
ORDER = [p.strip() for p in E("ROUTER_ORDER", "gemini,gemini-37,github,gemini-lite,gemini-lite-31,cloudflare,gemini-35,github-mini,groq,cerebras,mistral,nvidia,openrouter-free").split(",") if p.strip() in PROVIDERS]
BATCH_ORDER = [p.strip() for p in E("ROUTER_BATCH_ORDER", "gemini-lite,gemini-lite-31,github-mini,cloudflare,groq,cerebras,mistral,nvidia,gemini-35,gemini,gemini-37,github,openrouter-free").split(",") if p.strip() in PROVIDERS]
BATCH_RESERVE = float(E("ROUTER_BATCH_RESERVE", "0.30"))
MAX_REQ_CHARS = int(E("ROUTER_MAX_REQ_CHARS", "160000"))   # ≈40k tokens; older turns are trimmed above this
RETRY_WAITS = [int(x) for x in E("ROUTER_RETRY_WAITS", "8,25").split(",") if x.strip()]
TIMEOUT_CHAT = int(E("ROUTER_TIMEOUT_CHAT", "30"))         # give up on a slow model fast while Aryan waits
TIMEOUT_BATCH = int(E("ROUTER_TIMEOUT_BATCH", "90"))
HEDGE_SECS = float(E("ROUTER_HEDGE_SECS", "6"))            # chat: if no answer yet, ask the next model in parallel
TOOL_ALLOW = {t.strip() for t in E("ROUTER_TOOL_ALLOW", "").split(",") if t.strip()}   # empty = send all tools
PORT = int(E("ROUTER_PORT", "8090"))
RETRY_STATUSES = {408, 409, 425, 429, 500, 502, 503, 504, 529}
COOLDOWN = {}   # provider -> unix time until which it is skipped (429 / overloaded / billing)
USAGE = {}      # provider -> list of (time, est_tokens) for the last 24 h

def _usage(name, now):
    u = [x for x in USAGE.get(name, []) if now - x[0] < 86400]; USAGE[name] = u
    minute = [x for x in u if now - x[0] < 60]
    return len(minute), sum(t for _, t in minute), len(u)

def room(name, p, est_tokens, reserve=0.0):
    """True if this provider's free budget has space for one more request (keeping `reserve` free)."""
    rpm_used, tpm_used, rpd_used = _usage(name, time.time())
    keep = 1.0 - reserve
    if p["rpm"] and rpm_used + 1 > p["rpm"] * keep: return False
    if p["rpd"] and rpd_used + 1 > p["rpd"] * keep: return False
    if p["tpm"] and tpm_used + est_tokens > p["tpm"] * keep: return False
    return True

def record(name, est_tokens):
    USAGE.setdefault(name, []).append((time.time(), est_tokens))

_handlers = [logging.StreamHandler(sys.stdout)]          # -> systemd journal
if E("ROUTER_LOG"):
    try:
        os.makedirs(os.path.dirname(E("ROUTER_LOG")), exist_ok=True)
        _handlers.append(logging.FileHandler(E("ROUTER_LOG")))
    except Exception as _e:
        print("router: cannot open log file:", _e, flush=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=_handlers, force=True)
log = logging.getLogger("router")

# --- brain log (Supabase brain_events, kind=llm) for the dashboard AI page ----------------------
EVENTS = []
def note(level, message, **data):
    EVENTS.append({"source": "brain", "level": level, "message": message[:500], "data": {"kind": "llm", **data}})
    if len(EVENTS) > 500: del EVENTS[:100]

async def flush_events(app):
    url, key = E("SUPABASE_URL"), E("SUPABASE_SERVICE_KEY")
    if not (url and key): return
    async with ClientSession() as s:
        while True:
            await asyncio.sleep(int(E("ROUTER_FLUSH_SECS", "30")))
            if not EVENTS: continue
            batch = EVENTS[:100]
            try:
                r = await s.post(url.rstrip("/") + "/rest/v1/brain_events", json=batch, timeout=ClientTimeout(total=20),
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"})
                if r.status < 300: del EVENTS[:len(batch)]
                r.release()
            except Exception:
                pass

async def start_flusher(app):
    app["flusher"] = asyncio.create_task(flush_events(app))

def active_providers(req_chars, lane="chat"):
    now = time.time(); est = req_chars // 4
    for name in (BATCH_ORDER if lane == "batch" else ORDER):
        p = PROVIDERS[name]
        if not p["key"]: continue
        if COOLDOWN.get(name, 0) > now: continue
        if p.get("max_chars") and req_chars > p["max_chars"]: continue
        if not room(name, p, est, BATCH_RESERVE if lane == "batch" else 0.0): continue
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

# --- Gemini thought signatures -----------------------------------------------------------------
# Gemini 3 returns extra_content.google.thought_signature on every tool call and rejects the next
# request (HTTP 400 "Function call is missing a thought_signature") if it is not sent back. Hermes
# does not keep that field, so the router remembers signatures by tool_call id and re-attaches
# them; unknown ids get Google's documented placeholder that skips validation.
SIG_CACHE = {}            # tool_call_id -> signature
SIG_DUMMY = "skip_thought_signature_validator"

def remember_signatures(message):
    for tc in (message or {}).get("tool_calls") or []:
        sig = (((tc.get("extra_content") or {}).get("google") or {}).get("thought_signature"))
        if tc.get("id") and sig:
            SIG_CACHE[tc["id"]] = sig
    if len(SIG_CACHE) > 5000:
        for k in list(SIG_CACHE)[:1000]: SIG_CACHE.pop(k, None)

def prepare_messages(body, provider):
    """Gemini: make sure every assistant tool call carries a signature. Others: strip extra_content."""
    out = []
    for m in body.get("messages") or []:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            m = dict(m); tcs = []
            for tc in m["tool_calls"]:
                tc = dict(tc)
                if provider.startswith("gemini"):
                    sig = (((tc.get("extra_content") or {}).get("google") or {}).get("thought_signature")) \
                          or SIG_CACHE.get(tc.get("id")) or SIG_DUMMY
                    tc["extra_content"] = {"google": {"thought_signature": sig}}
                else:
                    tc.pop("extra_content", None)
                tcs.append(tc)
            m["tool_calls"] = tcs
        elif not provider.startswith("gemini") and "extra_content" in m:
            m = {k: v for k, v in m.items() if k != "extra_content"}
        out.append(m)
    return {**body, "messages": out}

def scan_stream_chunk(buf):
    """Pull thought signatures out of streamed SSE lines (tool_call deltas)."""
    for line in buf.split(b"\n"):
        line = line.strip()
        if not line.startswith(b"data:") or line.endswith(b"[DONE]"): continue
        try:
            d = json.loads(line[5:])
        except Exception:
            continue
        for ch in d.get("choices") or []:
            remember_signatures(ch.get("delta") or {})

def parse_retry_after(resp):
    try: return max(5, min(300, int(float(resp.headers.get("Retry-After", "60")))))
    except Exception: return 60

async def try_provider(session, name, p, body, stream, lane="chat"):
    payload = prepare_messages(body, name); payload["model"] = p["model"]
    if TOOL_ALLOW and payload.get("tools"):
        payload["tools"] = [t for t in payload["tools"] if (t.get("function") or {}).get("name") in TOOL_ALLOW] or None
        if not payload["tools"]: payload.pop("tools", None); payload.pop("tool_choice", None)
    payload.pop("user", None)
    headers = {"Content-Type": "application/json", **(p.get("headers") or {"Authorization": f"Bearer {p['key']}"})}
    if name == "openrouter-free": headers["HTTP-Referer"] = "https://armedias.com"; headers["X-Title"] = "ARVIS"
    record(name, len(json.dumps(payload)) // 4)
    read_to = TIMEOUT_CHAT if lane == "chat" else TIMEOUT_BATCH
    resp = await session.post(p["url"], json=payload, headers=headers, timeout=ClientTimeout(total=read_to * 4, sock_connect=10, sock_read=read_to))
    if resp.status in RETRY_STATUSES:
        txt = " ".join((await resp.text()).split())[:300]; resp.release()
        if resp.status == 429: COOLDOWN[name] = time.time() + parse_retry_after(resp)
        if resp.status in (500, 502, 503, 504, 529): COOLDOWN[name] = time.time() + 120   # overloaded: skip for 2 min
        if any(w in txt.lower() for w in ("payment method", "spend limit", "billing", "insufficient credit", "quota exceeded for this month")):
            COOLDOWN[name] = time.time() + 3600   # billing problem: no point retrying soon
        raise RuntimeError(f"{name} HTTP {resp.status}: {txt}")
    if resp.status >= 400:
        txt = " ".join((await resp.text()).split())[:300]; resp.release()
        raise RuntimeError(f"{name} HTTP {resp.status}: {txt}")
    return resp

TOOLS_SEEN = {"at": 0}

async def chat(request):
    body = await request.json()
    lane = "batch" if (body.get("model") == "arvis-batch" or request.headers.get("X-Arvis-Lane") == "batch") else "chat"
    if body.get("tools") and time.time() - TOOLS_SEEN["at"] > 3600:       # hourly: which tools Hermes sends, and their size
        TOOLS_SEEN["at"] = time.time()
        names = [(t.get("function") or {}).get("name") for t in body["tools"]]
        note("info", f"tools sent by Hermes: {len(names)}", tools=names, tools_chars=len(json.dumps(body["tools"])), lane=lane)
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
            cands = list(active_providers(req_chars, lane))
            while cands:
                # --- hedged race: start the best candidate; in the chat lane, if it has not answered within
                # HEDGE_SECS, start the next one too; first good answer wins, the others are cancelled.
                pending, started = {}, 0
                winner = None; hedge_due = False
                while (cands or pending) and winner is None:
                    if cands and (not pending or (lane == "chat" and len(pending) < 2 and hedge_due)):
                        name, p = cands.pop(0)
                        pending[asyncio.ensure_future(try_provider(session, name, p, body, stream, lane))] = (name, p, time.time())
                        started += 1
                    wait_for = HEDGE_SECS if (lane == "chat" and cands and len(pending) < 2) else None
                    done, _ = await asyncio.wait(list(pending), timeout=wait_for, return_when=asyncio.FIRST_COMPLETED)
                    hedge_due = not done          # nothing answered within HEDGE_SECS -> next loop starts a parallel request
                    for t in done:
                        name, p, t0 = pending.pop(t)
                        try:
                            resp = t.result()
                        except asyncio.TimeoutError:
                            COOLDOWN[name] = time.time() + 120
                            errors.append(f"{name}: too slow (> {TIMEOUT_CHAT if lane == 'chat' else TIMEOUT_BATCH}s)"); log.warning("failover: %s too slow", name)
                            note("warn", f"{name} failed: too slow", provider=name, ok=False, lane=lane); continue
                        except Exception as e:
                            errors.append(str(e)[:200]); log.warning("failover: %s", str(e)[:200])
                            note("warn", f"{name} failed: {str(e)[:160]}", provider=name, ok=False, lane=lane); continue
                        if winner is None: winner = (name, p, t0, resp)
                        else: resp.release()
                for t in pending:                                  # cancel the losers
                    t.cancel()
                if winner is None:
                    continue
                name, p, t0, resp = winner
                def served():
                    log.info("served by %s (%s) in %.1fs stream=%s chars=%d lane=%s", name, p["model"], time.time() - t0, stream, req_chars, lane)
                    note("info", f"served by {name}", provider=name, model=p["model"], ok=True, secs=round(time.time() - t0, 2),
                         chars=req_chars, stream=stream, attempt=attempt, trimmed=dropped, lane=lane)
                if not stream:
                    try:
                        data = await resp.json(content_type=None)
                    except Exception as e:
                        errors.append(f"{name}: unreadable answer"); log.warning("failover: %s returned non-JSON: %s", name, str(e)[:120])
                        note("warn", f"{name} failed: unreadable answer", provider=name, ok=False, lane=lane); continue
                    ch = ((data or {}).get("choices") or [{}])[0]; msg = ch.get("message") or {}
                    hit_limit = ch.get("finish_reason") == "length"     # caller's max_tokens reached: a valid answer
                    if not data.get("choices") or (not hit_limit and not (msg.get("content") or "").strip() and not msg.get("tool_calls")):
                        errors.append(f"{name}: empty answer"); log.warning("failover: %s returned an empty answer", name)
                        note("warn", f"{name} failed: empty answer", provider=name, ok=False, lane=lane); continue
                    served()
                    remember_signatures(msg)
                    data["model"] = f"arvis-router/{name}"
                    return web.json_response(data)
                served()
                out = web.StreamResponse(status=200, headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache", "X-Arvis-Provider": name})
                await out.prepare(request)
                tail = b""
                try:
                    async for chunk in resp.content.iter_any():
                        buf = tail + chunk
                        cut = buf.rfind(b"\n")
                        if cut >= 0:
                            scan_stream_chunk(buf[:cut]); tail = buf[cut + 1:]
                        else:
                            tail = buf
                        await out.write(chunk)
                    if tail: scan_stream_chunk(tail)
                    await out.write_eof()
                except (ConnectionResetError, Exception) as e:   # client went away mid-stream
                    log.info("stream from %s ended early: %s", name, str(e)[:120])
                return out
    msg = "all providers failed: " + " | ".join(errors[-6:]) if errors else "no provider configured (set GOOGLE_API_KEY etc. in /opt/arvis/.env)"
    log.error(msg)
    note("error", "all providers failed", ok=False, errors=errors[-4:])
    return web.json_response({"error": {"message": msg, "type": "router_exhausted", "code": 503}}, status=503)

async def models(request):
    return web.json_response({"object": "list", "data": [{"id": "arvis-router", "object": "model", "owned_by": "arvis", "context_length": 1000000,
                                                          "providers": [n for n, _ in active_providers(0)]}]})

async def health(request):
    now = time.time()
    budgets = {n: dict(zip(("rpm_used", "tpm_used", "rpd_used"), _usage(n, now)), rpm=PROVIDERS[n]["rpm"], rpd=PROVIDERS[n]["rpd"])
               for n in ORDER if PROVIDERS[n]["key"]}
    return web.json_response({"ok": True, "order": ORDER, "batch_order": BATCH_ORDER, "budgets": budgets,
                              "configured": [n for n in ORDER if PROVIDERS[n]["key"]],
                              "cooldown": {k: int(v - time.time()) for k, v in COOLDOWN.items() if v > time.time()}, "time": dt.datetime.utcnow().isoformat()})

app = web.Application(client_max_size=64 * 1024 * 1024)
app.on_startup.append(start_flusher)
app.add_routes([web.post("/v1/chat/completions", chat), web.get("/v1/models", models), web.get("/health", health)])

if __name__ == "__main__":
    log.info("arvis-router on 127.0.0.1:%s; order=%s; configured=%s", PORT, ORDER, [n for n in ORDER if PROVIDERS[n]["key"]])
    web.run_app(app, host="127.0.0.1", port=PORT, print=None, access_log=None)
