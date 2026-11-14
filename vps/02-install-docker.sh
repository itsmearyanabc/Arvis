#!/usr/bin/env bash
# =============================================================================
# ARVIS — 02-install-docker.sh
#
# What it does:
#   1. Installs Docker Engine + compose plugin from Docker's official apt repo
#      ONLY if docker is missing (on this box it is already installed, so: skipped).
#   2. Adds the `arvis` user to the `docker` group.
#
# What it NEVER does:
#   - It does NOT edit /etc/docker/daemon.json and does NOT restart dockerd, because
#     other containers run on this box (originx-web, originx-api) and must not be
#     interrupted. ARVIS containers are placed under arvis.slice by `cgroup_parent:`
#     in docker/docker-compose.yml instead, and log size is capped per container there.
#   - Does not touch PM2, Node, Nginx or armedias.com.
#
# Usage: sudo bash 02-install-docker.sh
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

if command -v docker &>/dev/null; then
  echo "docker already installed: $(docker --version) — install skipped, daemon untouched"
else
  apt-get update
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu/ ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

usermod -aG docker arvis
echo "arvis added to group docker (takes effect on the next 'sudo -iu arvis' login)."
docker compose version
echo "Running containers (untouched):"; docker ps --format '  {{.Names}}'
echo "PM2 / armedias.com untouched."
