#!/usr/bin/env bash
# =============================================================================
# ARVIS — 05-install-router.sh   (run as root: sudo bash vps/05-install-router.sh)
#
# Phase 3a: LLM reliability.
#   1. aiohttp into /opt/arvis/venv; arvis-router as a systemd *user* service for arvis
#      (127.0.0.1:8090, in the capped user slice, restarts on failure, starts at boot).
#   2. Points Hermes at the router: model.provider custom, base_url http://127.0.0.1:8090/v1,
#      model arvis-router. Failover across Gemini / Cerebras / NVIDIA / Groq / OpenRouter-free
#      now happens inside the router; add keys to /opt/arvis/.env any time, restart the router.
#   3. Trims Hermes' skills folder to ARVIS skills only (the bundled apple/creative/devops/... skills
#      add thousands of tokens to every request). Moved, not deleted: ~/.hermes/skills-disabled/.
#   4. Restarts the gateway and self-tests the router.
# Touches nothing outside /opt/arvis. PM2 / armedias.com untouched.
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
[[ -f /opt/arvis/.env ]] || { echo "/opt/arvis/.env missing"; exit 1; }
mkdir -p /opt/arvis/logs && chown arvis:arvis /opt/arvis/logs

sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
REPO=/opt/arvis/arvis-repo
cd "$REPO" && git pull -q || true
/opt/arvis/venv/bin/pip install -q -r "$REPO/workers/requirements.txt"

# 0. the router reads /opt/arvis/.env: carry over LLM keys Hermes already has in ~/.hermes/.env
for k in GROQ_API_KEY GOOGLE_API_KEY CEREBRAS_API_KEY NVIDIA_API_KEY OPENROUTER_API_KEY; do
  if ! grep -q "^$k=" /opt/arvis/.env && grep -q "^$k=" "$HOME/.hermes/.env" 2>/dev/null; then
    grep "^$k=" "$HOME/.hermes/.env" | tail -1 >> /opt/arvis/.env
  fi
done

# 1. service
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/arvis-router.service" <<'UNIT'
[Unit]
Description=ARVIS LLM failover router (127.0.0.1:8090)
After=network-online.target

[Service]
Environment=ARVIS_ENV=/opt/arvis/.env
Environment=ROUTER_LOG=/opt/arvis/logs/router.log
ExecStart=/opt/arvis/venv/bin/python -I /opt/arvis/arvis-repo/brain/router/router.py
Restart=always
RestartSec=3
MemoryMax=200M

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now arvis-router
sleep 2
systemctl --user restart arvis-router
sleep 2

# 2. hermes -> router
grep -q '^ROUTER_KEY=' "$HOME/.hermes/.env" 2>/dev/null || echo 'ROUTER_KEY=local' >> "$HOME/.hermes/.env"
hermes config set model.provider custom >/dev/null
hermes config set model.base_url http://127.0.0.1:8090/v1 >/dev/null
hermes config set model.key_env ROUTER_KEY >/dev/null
hermes config set model.default arvis-router >/dev/null

# 3. trim skills to ARVIS's own (repo-linked) skills
mkdir -p "$HOME/.hermes/skills-disabled"
for d in "$HOME/.hermes/skills"/*/; do
  n=$(basename "$d")
  if [[ ! -d "$REPO/hermes/skills/$n" ]]; then mv "$d" "$HOME/.hermes/skills-disabled/$n" 2>/dev/null || true; fi
done
echo "active skills: $(ls "$HOME/.hermes/skills" | tr '\n' ' ')"

hermes gateway restart >/dev/null 2>&1 || true
sleep 6
echo "== router health"; curl -s http://127.0.0.1:8090/health; echo
echo "== router answer"; curl -s -m 60 http://127.0.0.1:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"arvis-router","messages":[{"role":"user","content":"Reply with exactly: router ok"}],"max_tokens":10}' | head -c 400; echo
echo "== gateway"; hermes gateway status | tail -4
AS_ARVIS
echo "Done. Ask the bot on Telegram: which model are you on? — then: how many businesses scraped?"
