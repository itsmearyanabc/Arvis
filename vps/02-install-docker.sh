#!/usr/bin/env bash
# =============================================================================
# ARVIS — 02-install-docker.sh
#
# What it does:
#   1. Installs Docker Engine + compose plugin from Docker's official apt repo
#      (skips if docker is already installed).
#   2. Adds the `arvis` user to the `docker` group.
#   3. Points Docker's default cgroup parent at arvis.slice so every container
#      ARVIS starts is counted against the ARVIS CPU/RAM caps from 01.
#   4. Limits container log size so logs can't fill the disk.
#
# Shared VPS with armedias.com: PM2, Node and Nginx are never touched. Docker is
# already installed on this box (VPS report), so the install block is skipped and the
# script only writes daemon.json and restarts dockerd. It refuses to restart dockerd
# if any container is currently running, so nothing of yours is interrupted.
#
# Usage: sudo bash 02-install-docker.sh
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

if command -v docker &>/dev/null; then
  echo "docker already installed: $(docker --version)"
else
  apt-get update
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

usermod -aG docker arvis

# daemon.json: put containers under arvis.slice, cap log size.
# If a daemon.json already exists it is backed up, not overwritten blindly.
if [[ -n "$(docker ps -q 2>/dev/null)" ]]; then
  echo "Containers are running on this box:"; docker ps --format '  {{.Names}} ({{.Image}})'
  echo "Restarting dockerd would stop them. Stop them first or paste this output to Claude." >&2
  exit 1
fi
mkdir -p /etc/docker
if [[ -f /etc/docker/daemon.json ]]; then
  cp /etc/docker/daemon.json "/etc/docker/daemon.json.bak.$(date +%s)"
  echo "existing /etc/docker/daemon.json backed up — merge these keys by hand if it was non-empty:"
fi
cat > /etc/docker/daemon.json <<'JSON'
{
  "cgroup-parent": "arvis.slice",
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true
}
JSON
systemctl enable docker
systemctl restart docker

echo
docker --version
docker compose version
echo "arvis is in group docker (takes effect on next login of arvis)."
echo "Containers will run under arvis.slice. PM2 / armedias.com untouched."
