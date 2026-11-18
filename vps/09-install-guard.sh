#!/usr/bin/env bash
# =============================================================================
# ARVIS — 09-install-guard.sh   (run as root: sudo bash vps/09-install-guard.sh)
# Installs arvis-guard (vps/guard/arvis-guard.sh) as a root systemd timer, every 30 s.
# Read-only towards the website: it only sends one local request to armedias.com and reads
# /proc. It changes nothing except ARVIS's own CPU cap and the Reacher container.
# Remove any time:  systemctl disable --now arvis-guard.timer
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
cd /opt/arvis/arvis-repo && sudo -u arvis git pull -q || true
install -m 0755 /opt/arvis/arvis-repo/vps/guard/arvis-guard.sh /usr/local/sbin/arvis-guard
cat > /etc/systemd/system/arvis-guard.service <<'UNIT'
[Unit]
Description=ARVIS website guard (throttles ARVIS when armedias.com or the VPS is under strain)
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/arvis-guard
Nice=-5
UNIT
cat > /etc/systemd/system/arvis-guard.timer <<'UNIT'
[Unit]
Description=Run arvis-guard every 30 seconds
[Timer]
OnBootSec=60
OnUnitActiveSec=30
AccuracySec=2
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now arvis-guard.timer
echo "== one reading now:"
/usr/local/sbin/arvis-guard; cat /run/arvis-guard.state
code=$(curl -sk -o /dev/null -m 5 -w '%{http_code} in %{time_total}s' --resolve armedias.com:443:127.0.0.1 https://armedias.com/ || true)
echo "== armedias.com measured on this server: HTTP $code (000 = guard falls back to load + memory only)"
echo "== current caps:"; systemctl show arvis.slice -p CPUQuotaPerSecUSec; systemctl show "user-$(id -u arvis).slice" -p CPUQuotaPerSecUSec
systemctl list-timers arvis-guard.timer --no-pager | head -3
echo "Done. Watch it: journalctl -t arvis-guard -f"
