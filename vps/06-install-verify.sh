#!/usr/bin/env bash
# =============================================================================
# ARVIS — 06-install-verify.sh   (run as root: sudo bash vps/06-install-verify.sh)
#
# Phase 3b: email verification on the VPS.
#   1. Tests outbound port 25 (Reacher needs it to talk to mail servers). Hostinger sometimes
#      blocks it; if blocked, verification falls back to Hunter and the script says so.
#   2. Starts the Reacher container (docker compose, 127.0.0.1:8081, 256 MB cap, under arvis.slice).
#   3. Installs the nightly Hermes cron "verify-nightly" (06:30 IST, script-only, no LLM tokens).
#   4. Self-test: verifies one address through Reacher.
# Touches nothing outside /opt/arvis. Other containers (originx-*) and PM2 untouched.
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
echo "== outbound port 25 test"
if timeout 8 bash -c 'exec 3<>/dev/tcp/alt1.gmail-smtp-in.l.google.com/25' 2>/dev/null; then echo "port 25: OPEN (Reacher SMTP verification will work)"; P25=open
else echo "port 25: BLOCKED (Reacher will answer 'unknown'; use Hunter verification)"; P25=blocked; fi
grep -q '^REACHER_URL=' /opt/arvis/.env || echo 'REACHER_URL=http://127.0.0.1:8081' >> /opt/arvis/.env

sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
REPO=/opt/arvis/arvis-repo
cd "$REPO" && git pull -q || true
mkdir -p "$HOME/.hermes/scripts"; cp "$REPO/brain/scripts/verify-nightly.sh" "$HOME/.hermes/scripts/"; chmod +x "$HOME/.hermes/scripts/verify-nightly.sh"
echo "== reacher"
cd "$REPO/docker" && docker compose up -d 2>&1 | tail -2
sleep 6
docker ps --filter name=arvis-reacher --format '  {{.Names}} {{.Status}}'
echo "== cron"
if ! hermes cron list 2>/dev/null | grep -q "verify-nightly"; then
  hermes cron create "30 6 * * *" --no-agent --script verify-nightly.sh --name verify-nightly --timezone Asia/Kolkata || echo "cron create failed — paste 'hermes cron list' to Claude"
fi
echo "== self-test (one address)"
curl -s -m 60 -X POST http://127.0.0.1:8081/v0/check_email -H 'Content-Type: application/json' -d '{"to_email":"connect@armedias.tech"}' | head -c 300; echo
echo "== pending contacts"; arvisctl verify --limit 2 || true
AS_ARVIS
echo "Done. port25=$P25. PM2 / armedias.com untouched."
