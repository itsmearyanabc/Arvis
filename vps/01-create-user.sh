#!/usr/bin/env bash
# =============================================================================
# ARVIS — 01-create-user.sh
#
# What it does:
#   1. Creates a dedicated Linux user `arvis` with home /opt/arvis (no sudo).
#   2. Creates /opt/arvis/{secrets,data,logs,docker,hermes} with safe permissions.
#   3. Creates a systemd slice `arvis.slice` that caps CPU and RAM for EVERYTHING
#      ARVIS runs (Hermes, cron jobs, and the Docker containers via their
#      cgroup parent), so the main site can never be starved.
#   4. Adds a 2G swapfile if the box has none (Hostinger images ship without swap).
#
# What it NEVER does:
#   - It does not touch PM2, Node, Nginx config, or anything belonging to
#     armedias.com. It only adds a new user, a new slice and (optionally) swap.
#
# ARVIS runs on its OWN dedicated VPS (decided 2026-11-15). armedias.com lives on a
# different server and is never touched by anything in this repo. The slice caps here are
# sane limits so a runaway scraper cannot wedge the ARVIS box itself:
#   Default ........ sudo bash 01-create-user.sh
#        CPUQuota=90% of cores, MemoryMax=80% of RAM, MemoryHigh=85% of that, 2G swap.
#   Custom ......... sudo bash 01-create-user.sh <cpu%> <mem> [swap]
#        e.g. sudo bash 01-create-user.sh 180% 6G 2G
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

ARVIS_USER=arvis
ARVIS_HOME=/opt/arvis

if [[ $# -eq 0 ]]; then
  CORES=$(nproc); MEM_KB=$(awk '/MemTotal/{print $2}' /proc/meminfo)
  CPU_QUOTA="$(( CORES * 90 ))%"
  MEM_MAX="$(( MEM_KB * 80 / 100 / 1024 ))M"
  SWAP_SIZE="2G"
else
  CPU_QUOTA="$1"; MEM_MAX="${2:?usage: 01-create-user.sh [<cpu%> <mem> [swap]]}"; SWAP_SIZE="${3:-2G}"
fi
[[ "$CPU_QUOTA" == *% ]] || CPU_QUOTA="${CPU_QUOTA}%"

# MemoryHigh (soft, throttle) = 85% of MemoryMax (hard, OOM)
num="${MEM_MAX%[GgMm]}"; unit="${MEM_MAX: -1}"
if [[ "$unit" == [Gg] ]]; then num=$(( num * 1024 )); unit=M; fi
MEM_HIGH="$(( num * 85 / 100 ))${unit}"

# 1. user ---------------------------------------------------------------------
if id "$ARVIS_USER" &>/dev/null; then
  echo "user $ARVIS_USER already exists, skipping adduser"
else
  adduser --system --group --home "$ARVIS_HOME" --shell /bin/bash "$ARVIS_USER"
  echo "created user $ARVIS_USER"
fi
mkdir -p "$ARVIS_HOME"/{secrets,data,logs,docker,hermes}
chown -R "$ARVIS_USER:$ARVIS_USER" "$ARVIS_HOME"
chmod 750 "$ARVIS_HOME"
chmod 700 "$ARVIS_HOME/secrets"
# user services (Hermes gateway) must keep running after logout
loginctl enable-linger "$ARVIS_USER"
UID_ARVIS=$(id -u "$ARVIS_USER")

# 2. systemd slice for Docker containers --------------------------------------
cat > /etc/systemd/system/arvis.slice <<SLICE
[Unit]
Description=ARVIS resource slice (Docker services started by ARVIS)
Before=slices.target

[Slice]
CPUAccounting=yes
MemoryAccounting=yes
IOAccounting=yes
CPUQuota=${CPU_QUOTA}
MemoryMax=${MEM_MAX}
MemoryHigh=${MEM_HIGH}
IOWeight=50
CPUWeight=50
SLICE

# 3. same caps on the arvis user's own session slice (Hermes, cron, shells) ---
mkdir -p "/etc/systemd/system/user-${UID_ARVIS}.slice.d"
cat > "/etc/systemd/system/user-${UID_ARVIS}.slice.d/arvis-caps.conf" <<CONF
[Slice]
CPUAccounting=yes
MemoryAccounting=yes
CPUQuota=${CPU_QUOTA}
MemoryMax=${MEM_MAX}
MemoryHigh=${MEM_HIGH}
CPUWeight=50
CONF
systemctl daemon-reload
systemctl start arvis.slice

# 4. swapfile (optional) -------------------------------------------------------
if [[ "$SWAP_SIZE" != "0" ]]; then
  if swapon --show | grep -q .; then
    echo "swap already active, not adding another:"; swapon --show
  else
    fallocate -l "$SWAP_SIZE" /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl -w vm.swappiness=10 >/dev/null
    grep -q '^vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf
    echo "swapfile ${SWAP_SIZE} added (swappiness=10)"
  fi
fi

echo
echo "Done. Summary:"
echo "  user        : $ARVIS_USER (uid $UID_ARVIS), home $ARVIS_HOME"
echo "  caps        : CPUQuota=$CPU_QUOTA MemoryMax=$MEM_MAX MemoryHigh=$MEM_HIGH"
echo "  applied to  : arvis.slice (containers) + user-${UID_ARVIS}.slice (Hermes/cron)"
systemctl show arvis.slice -p CPUQuotaPerSecUSec -p MemoryMax -p MemoryHigh
free -h
echo "armedias.com (other server) untouched."
