#!/usr/bin/env bash
# Download the latest dashboard build (GitHub release asset) if it changed, swap it in, restart.
# Runs as the arvis user (Hermes cron, no LLM). Exits quietly when nothing changed.
set -euo pipefail
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
URL="https://github.com/itsmearyanabc/Arvis/releases/download/dashboard-latest/dashboard.tar.gz"
DIR=/opt/arvis/dashboard; NEW=/opt/arvis/dashboard.new; TMP=/opt/arvis/dashboard.tar.gz
curl -fsSL -o "$TMP" "$URL"
SUM=$(sha256sum "$TMP" | cut -d' ' -f1)
if [[ -f "$DIR/.sha256" && "$(cat "$DIR/.sha256")" == "$SUM" ]]; then rm -f "$TMP"; exit 0; fi
rm -rf "$NEW" && mkdir -p "$NEW" && tar -xzf "$TMP" -C "$NEW" && echo "$SUM" > "$NEW/.sha256"
rm -rf "$DIR.old"; [[ -d "$DIR" ]] && mv "$DIR" "$DIR.old"; mv "$NEW" "$DIR"; rm -f "$TMP"
systemctl --user restart arvis-dashboard
echo "dashboard updated to $(cat "$DIR/VERSION" 2>/dev/null | cut -c1-7)"
