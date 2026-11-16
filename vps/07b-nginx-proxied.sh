#!/usr/bin/env bash
# =============================================================================
# ARVIS — 07b-nginx-proxied.sh   (run as root AFTER 07, BEFORE turning Cloudflare's orange cloud on)
#
# Rewrites ONLY /etc/nginx/sites-available/arvis-dashboard.conf so the dashboard works behind the
# Cloudflare proxy in any SSL mode (Flexible, Full, Full strict) without a redirect loop:
#   - port 80 serves the app directly (no origin redirect; Cloudflare's "Always Use HTTPS" does it)
#   - port 443 serves the app with the Let's Encrypt certificate certbot already issued
#   - ACME challenges stay reachable on both, so certbot renewals keep working
# The armedias.com server block is not touched. `nginx -t` must pass, else the old file is restored.
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
F=/etc/nginx/sites-available/arvis-dashboard.conf
LE=/etc/letsencrypt/live/arvis.armedias.com
[[ -f $LE/fullchain.pem ]] || { echo "no certificate at $LE — run vps/07-install-dashboard.sh first"; exit 1; }
cp "$F" "$F.bak.$(date +%s)"
SSLOPT=""; [[ -f /etc/letsencrypt/options-ssl-nginx.conf ]] && SSLOPT="include /etc/letsencrypt/options-ssl-nginx.conf;"
DH="";     [[ -f /etc/letsencrypt/ssl-dhparams.pem ]] && DH="ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;"
cat > "$F" <<NGINX
# ARVIS dashboard only (arvis.armedias.com). Separate from armedias.com. Written by vps/07b-nginx-proxied.sh.
map \$http_upgrade \$arvis_conn_upgrade { default upgrade; '' close; }
server {
    listen 80;
    listen [::]:80;
    listen 443 ssl http2;        # nginx 1.24 syntax ("http2 on;" needs >= 1.25.1)
    listen [::]:443 ssl http2;
    server_name arvis.armedias.com;
    ssl_certificate     $LE/fullchain.pem;
    ssl_certificate_key $LE/privkey.pem;
    $SSLOPT
    $DH
    access_log /var/log/nginx/arvis-dashboard.access.log;
    error_log  /var/log/nginx/arvis-dashboard.error.log;
    add_header X-Robots-Tag "noindex, nofollow" always;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / {
        proxy_pass http://127.0.0.1:3100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$arvis_conn_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
NGINX
if nginx -t 2>&1 | tail -2; then systemctl reload nginx && echo "== nginx reloaded (zero downtime)"
else cp "$(ls -t $F.bak.* | head -1)" "$F"; nginx -t >/dev/null 2>&1 && systemctl reload nginx; echo "nginx test FAILED — previous config restored"; exit 1; fi
curl -s -o /dev/null -w "== http  -> HTTP %{http_code} (expect 200, no redirect)\n" -H "Host: arvis.armedias.com" http://127.0.0.1/login
curl -sk -o /dev/null -w "== https -> HTTP %{http_code}\n" --resolve arvis.armedias.com:443:127.0.0.1 https://arvis.armedias.com/login
echo "Now turn the Cloudflare cloud for 'arvis' ORANGE (Proxied). armedias.com untouched."
