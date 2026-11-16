#!/usr/bin/env bash
# =============================================================================
# ARVIS — 07-install-dashboard.sh   (run as root: sudo bash vps/07-install-dashboard.sh)
#
# Hosts the ARVIS dashboard at https://arvis.armedias.com on THIS VPS, without slowing armedias.com:
#   - nothing is built here: the ready-made server comes from GitHub (release dashboard-latest)
#   - Node 22 is installed privately in /opt/arvis/node (root's nvm and PM2 are not touched)
#   - runs as user arvis, 127.0.0.1:3100, MemoryMax 300M, inside the capped arvis user slice
#   - Nginx gets ONE new server block for arvis.armedias.com only; the armedias.com block is not
#     edited; `nginx -t` must pass before a zero-downtime `reload`
#   - TLS via certbot for arvis.armedias.com only
#   - Hermes cron "update-dashboard" pulls new builds hourly (no LLM tokens)
# Before running: Cloudflare DNS for armedias.com → A record `arvis` → this VPS's IP, DNS only (grey).
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
DOMAIN=arvis.armedias.com
IP=$(curl -4 -s ifconfig.me || true)
echo "== this VPS public IP: $IP"
RESOLVED=$(getent ahostsv4 $DOMAIN | awk 'NR==1{print $1}' || true)
echo "== $DOMAIN resolves to: ${RESOLVED:-nothing yet}"
[[ "$RESOLVED" == "$IP" ]] || echo "WARNING: DNS not pointing here yet (needs Cloudflare A record, DNS only). certbot will fail until it does."

# 1. private Node 22 for arvis
if [[ ! -x /opt/arvis/node/bin/node ]]; then
  V=$(curl -s https://nodejs.org/dist/index.json | python3 -c 'import sys,json; print(next(r["version"] for r in json.load(sys.stdin) if r["version"].startswith("v22.")))')
  curl -fsSL "https://nodejs.org/dist/$V/node-$V-linux-x64.tar.xz" -o /tmp/node.tar.xz
  mkdir -p /opt/arvis/node && tar -xJf /tmp/node.tar.xz -C /opt/arvis/node --strip-components=1 && rm /tmp/node.tar.xz
  chown -R arvis:arvis /opt/arvis/node
fi
echo "== node $(/opt/arvis/node/bin/node -v)"

# 2. runtime env for the server (secrets stay on the VPS, read at runtime)
ENVF=/opt/arvis/dashboard.env
get() { grep -m1 "^$1=" /opt/arvis/.env | cut -d= -f2- || true; }
UNSUB=$(grep -m1 '^UNSUBSCRIBE_SECRET=' /opt/arvis/.env | cut -d= -f2- || true)
[[ -n "$UNSUB" ]] || { UNSUB=$(openssl rand -hex 24); echo "UNSUBSCRIBE_SECRET=$UNSUB" >> /opt/arvis/.env; }
cat > "$ENVF" <<ENV
NODE_ENV=production
PORT=3100
HOSTNAME=127.0.0.1
NEXT_TELEMETRY_DISABLED=1
SUPABASE_SERVICE_KEY=$(get SUPABASE_SERVICE_KEY)
UNSUBSCRIBE_SECRET=$UNSUB
CALCOM_WEBHOOK_SECRET=$(get CALCOM_WEBHOOK_SECRET)
ENV
chown arvis:arvis "$ENVF" && chmod 600 "$ENVF"

# 3. service + first download (as arvis)
sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
cd /opt/arvis/arvis-repo && git pull -q || true
mkdir -p "$HOME/.config/systemd/user" "$HOME/.hermes/scripts"
cat > "$HOME/.config/systemd/user/arvis-dashboard.service" <<'UNIT'
[Unit]
Description=ARVIS dashboard (Next.js standalone, 127.0.0.1:3100)
After=network-online.target

[Service]
EnvironmentFile=/opt/arvis/dashboard.env
WorkingDirectory=/opt/arvis/dashboard
ExecStart=/opt/arvis/node/bin/node server.js
Restart=always
RestartSec=3
MemoryMax=300M
Nice=10

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable arvis-dashboard >/dev/null
cp /opt/arvis/arvis-repo/brain/scripts/update-dashboard.sh "$HOME/.hermes/scripts/" && chmod +x "$HOME/.hermes/scripts/update-dashboard.sh"
rm -f /opt/arvis/dashboard/.sha256
"$HOME/.hermes/scripts/update-dashboard.sh" || { echo "download failed: has the GitHub 'dashboard' workflow published dashboard-latest yet?"; exit 1; }
sleep 3
curl -s -o /dev/null -w '== local check: login page HTTP %{http_code}\n' http://127.0.0.1:3100/login
export PATH="$HOME/.local/bin:$PATH"
hermes cron list 2>/dev/null | grep -q update-dashboard || hermes cron create "15 * * * *" --no-agent --script update-dashboard.sh --name update-dashboard --timezone Asia/Kolkata >/dev/null && echo "== cron update-dashboard hourly"
AS_ARVIS

# 4. nginx: one new server block, nothing else
cat > /etc/nginx/sites-available/arvis-dashboard.conf <<'NGINX'
# ARVIS dashboard only. Separate from armedias.com; added by vps/07-install-dashboard.sh.
server {
    listen 80;
    listen [::]:80;
    server_name arvis.armedias.com;
    access_log /var/log/nginx/arvis-dashboard.access.log;
    error_log  /var/log/nginx/arvis-dashboard.error.log;
    add_header X-Robots-Tag "noindex, nofollow" always;
    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
NGINX
ln -sfn /etc/nginx/sites-available/arvis-dashboard.conf /etc/nginx/sites-enabled/arvis-dashboard.conf
if nginx -t 2>&1 | tail -2; then systemctl reload nginx && echo "== nginx reloaded (zero downtime)"; else
  rm -f /etc/nginx/sites-enabled/arvis-dashboard.conf; echo "nginx test FAILED — block removed, nothing changed"; exit 1; fi

# 5. TLS for this subdomain only
command -v certbot >/dev/null || apt-get install -y certbot python3-certbot-nginx >/dev/null
if [[ "$RESOLVED" == "$IP" ]]; then
  certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect | tail -3
else
  echo "== certbot skipped: point DNS first, then run: certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect"
fi
curl -s -o /dev/null -w "== public check: https://$DOMAIN/login HTTP %{http_code}\n" https://$DOMAIN/login || true
echo "Done. PM2 / armedias.com untouched."
