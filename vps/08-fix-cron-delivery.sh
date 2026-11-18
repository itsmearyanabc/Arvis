#!/usr/bin/env bash
# =============================================================================
# ARVIS — 08-fix-cron-delivery.sh   (run as root: sudo bash vps/08-fix-cron-delivery.sh)
#
# Bug fix: daily-report and verify-nightly were created without a delivery target, so Hermes
# kept their output on the server ("Deliver: local") and the 08:30 report never reached Telegram.
# Re-creates both with --deliver telegram (home channel). update-dashboard stays local (silent).
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd /opt/arvis/arvis-repo && git pull -q || true
cp brain/scripts/verify-nightly.sh "$HOME/.hermes/scripts/" && chmod +x "$HOME/.hermes/scripts/verify-nightly.sh"
for j in daily-report verify-nightly; do hermes cron remove "$j" >/dev/null 2>&1 || true; done
hermes cron create "30 8 * * *" "Run the shell command: arvisctl report  — then send its exact output as a message. Do not add commentary." \
  --name daily-report --timezone Asia/Kolkata --skill arvis-ops --deliver telegram
hermes cron create "30 6 * * *" --no-agent --script verify-nightly.sh --name verify-nightly --timezone Asia/Kolkata --deliver telegram
echo "== jobs"; hermes cron list | grep -E "Name|Deliver|Next run" || hermes cron list
echo "== test: running daily-report now (arrives on Telegram in ~1 min)"
hermes cron run daily-report || echo "run it manually: hermes cron run daily-report"
AS_ARVIS
