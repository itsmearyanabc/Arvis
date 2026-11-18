#!/usr/bin/env bash
# =============================================================================
# ARVIS — 10-update-ai-and-guard.sh   (run as root: sudo bash vps/10-update-ai-and-guard.sh)
# Rolls out design v2 phases A + B:
#   A. website guard (root timer, every 30 s) — see vps/09-install-guard.sh
#   B. new AI router: chat/background lanes, free-tier budgets, hedged chat requests,
#      2-min skip for overloaded models, more Gemini buckets, GitHub Models + Cloudflare ready
# Also applies the earlier pending fixes (cron delivery to Telegram, dashboard refresh).
# Touches nothing outside ARVIS. PM2 / armedias.com untouched.
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
cd /opt/arvis/arvis-repo && sudo -u arvis git pull -q
bash vps/09-install-guard.sh
sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
export XDG_RUNTIME_DIR="/run/user/$(id -u)"; export PATH="$HOME/.local/bin:$PATH"
/opt/arvis/venv/bin/pip install -q -r /opt/arvis/arvis-repo/workers/requirements.txt
systemctl --user restart arvis-router && sleep 3
echo "== router"; curl -s 127.0.0.1:8090/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print("chat order:", [p for p in d["order"] if p in d["configured"]]); print("cooldown:", d["cooldown"])'
echo "== test answer"; curl -s -m 90 127.0.0.1:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"arvis-router","messages":[{"role":"user","content":"Reply with one word: ready"}]}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("model"), "->", d["choices"][0]["message"]["content"][:30])'
~/.hermes/scripts/update-dashboard.sh || true
hermes gateway restart >/dev/null 2>&1 || true
AS_ARVIS
bash vps/08-fix-cron-delivery.sh
echo "Done. PM2 / armedias.com untouched."
