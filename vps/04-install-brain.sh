#!/usr/bin/env bash
# =============================================================================
# ARVIS — 04-install-brain.sh   (run as root: sudo bash vps/04-install-brain.sh)
#
# Gives the Hermes brain its hands:
#   1. Python venv at /opt/arvis/venv with the worker requirements (supabase client etc.)
#   2. `arvisctl` on the arvis user's PATH (wrapper around brain/arvisctl.py)
#   3. Makes sure /opt/arvis/.env exists (chmod 600) and is sourced into Hermes' env
#   4. Re-links hermes/skills (adds arvis-ops) and restarts the gateway
#   5. Hermes cron job "daily-report" at 08:30 IST (idempotent)
# Touches nothing outside /opt/arvis. PM2 / armedias.com untouched.
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
REPO=/opt/arvis/arvis-repo
[[ -f /opt/arvis/.env ]] || { echo "/opt/arvis/.env missing — create it first (see README Phase 2)"; exit 1; }
chown arvis:arvis /opt/arvis/.env && chmod 600 /opt/arvis/.env

sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
REPO=/opt/arvis/arvis-repo
cd "$REPO" && git pull -q || true

# 1. venv
[[ -x /opt/arvis/venv/bin/python ]] || python3 -m venv /opt/arvis/venv
/opt/arvis/venv/bin/pip install -q --upgrade pip
/opt/arvis/venv/bin/pip install -q -r "$REPO/workers/requirements.txt"

# 2. arvisctl wrapper
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/arvisctl" <<'W'
#!/usr/bin/env bash
exec /opt/arvis/venv/bin/python -I /opt/arvis/arvis-repo/brain/arvisctl.py "$@"
W
chmod +x "$HOME/.local/bin/arvisctl"

# 3. env: Hermes' tool shell inherits ~/.hermes/.env; mirror the non-secret pointer there
grep -q '^ARVIS_ENV=' "$HOME/.hermes/.env" 2>/dev/null || echo 'ARVIS_ENV=/opt/arvis/.env' >> "$HOME/.hermes/.env"

# 4. skills
mkdir -p "$HOME/.hermes/skills"
for d in "$REPO"/hermes/skills/*/; do ln -sfn "$d" "$HOME/.hermes/skills/$(basename "$d")"; done

# 5. cron (idempotent)
if ! hermes cron list 2>/dev/null | grep -q "daily-report"; then
  hermes cron create "30 8 * * *" "Run the shell command: arvisctl report  — then send its exact output as a message. Do not add commentary." \
    --name daily-report --timezone Asia/Kolkata --skill arvis-ops || echo "cron create failed — run 'hermes cron list' and paste to Claude"
fi

hermes gateway restart >/dev/null 2>&1 || true
sleep 5
echo "== arvisctl self-test"; arvisctl stats
echo "== cron"; hermes cron list 2>/dev/null | head -20 || true
AS_ARVIS
echo "Done. Ask the bot on Telegram: how many emails scraped till now?"
