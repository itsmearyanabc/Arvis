#!/usr/bin/env bash
# =============================================================================
# arvis-guard — protects armedias.com (and every other site on this VPS) from ARVIS.
# Runs as root every 30 s (systemd timer). Cost per run: one local HTTP request + reading 2 files.
#
# Strained = armedias.com answers slower than SLOW_MS on this machine, OR 1-min load > LOAD_MAX
#            (per core), OR available memory < MEM_MIN_MB.
# Strained -> ARVIS CPU cap drops to LOW (default 10 %) for arvis.slice + the arvis user slice, and
#             Reacher (email verifier container) is paused.
# Calm for CALM_RUNS checks in a row (default 10 = 5 min) -> back to NORMAL (40 %), Reacher resumed.
# "Can't measure the site" (no answer at all) is neutral: only load/memory decide, so a probe glitch
# can never pin ARVIS down forever. Every state change is logged to the journal + ARVIS brain log.
# Changes are --runtime only: a reboot always returns to the normal caps from vps/01.
# =============================================================================
set -u
SITE_URL="${SITE_URL:-https://armedias.com/}"
SITE_HOST="${SITE_HOST:-armedias.com}"
SLOW_MS="${SLOW_MS:-800}"
LOAD_MAX="${LOAD_MAX:-0.80}"
MEM_MIN_MB="${MEM_MIN_MB:-300}"
LOW="${LOW:-10%}"; NORMAL="${NORMAL:-40%}"
CALM_RUNS="${CALM_RUNS:-10}"
STATE="${STATE:-/run/arvis-guard.state}"            # "normal|throttled <calm_count>"
LOADAVG_FILE="${LOADAVG_FILE:-/proc/loadavg}"
MEMINFO_FILE="${MEMINFO_FILE:-/proc/meminfo}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
DOCKER="${DOCKER:-docker}"
CURL="${CURL:-curl}"
ENV_FILE="${ENV_FILE:-/opt/arvis/.env}"
ARVIS_UID="${ARVIS_UID:-$(id -u arvis 2>/dev/null || echo 0)}"
NPROC="${NPROC:-$(nproc 2>/dev/null || echo 1)}"

# --- measurements -------------------------------------------------------------
ms=$($CURL -sk -o /dev/null -m 5 -w '%{http_code} %{time_total}' --resolve "$SITE_HOST:443:127.0.0.1" "$SITE_URL" 2>/dev/null || echo "000 0")
code=${ms%% *}; secs=${ms##* }
site_ms=$(awk -v s="$secs" 'BEGIN{printf "%d", s*1000}')
load1=$(awk '{print $1}' "$LOADAVG_FILE")
load_per_core=$(awk -v l="$load1" -v n="$NPROC" 'BEGIN{printf "%.2f", l/n}')
mem_mb=$(awk '/^MemAvailable:/{printf "%d", $2/1024}' "$MEMINFO_FILE")

reasons=""
if [ "$code" != "000" ] && [ "$site_ms" -gt "$SLOW_MS" ]; then reasons="$reasons site ${site_ms}ms>${SLOW_MS}ms;"; fi
if [ "$code" -ge 500 ] 2>/dev/null; then reasons="$reasons site HTTP $code;"; fi
if awk -v a="$load_per_core" -v b="$LOAD_MAX" 'BEGIN{exit !(a>b)}'; then reasons="$reasons load ${load_per_core}/core>${LOAD_MAX};"; fi
if [ "${mem_mb:-99999}" -lt "$MEM_MIN_MB" ]; then reasons="$reasons free RAM ${mem_mb}MB<${MEM_MIN_MB}MB;"; fi

read -r mode calm 2>/dev/null < "$STATE" || { mode=normal; calm=0; }

set_cap() {   # $1 = CPUQuota
  $SYSTEMCTL set-property --runtime arvis.slice "CPUQuota=$1" >/dev/null 2>&1
  [ "$ARVIS_UID" != "0" ] && $SYSTEMCTL set-property --runtime "user-$ARVIS_UID.slice" "CPUQuota=$1" >/dev/null 2>&1
  return 0
}
brain_log() {  # $1 level, $2 message  (best effort, never blocks the guard for long)
  local url key
  url=$(grep -m1 '^SUPABASE_URL=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
  key=$(grep -m1 '^SUPABASE_SERVICE_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2-)
  [ -n "$url" ] && [ -n "$key" ] || return 0
  $CURL -s -m 5 -o /dev/null -X POST "$url/rest/v1/brain_events" -H "apikey: $key" -H "Authorization: Bearer $key" \
    -H "Content-Type: application/json" -H "Prefer: return=minimal" \
    -d "{\"source\":\"brain\",\"level\":\"$1\",\"message\":\"$2\",\"data\":{\"kind\":\"guard\",\"site_ms\":$site_ms,\"site_code\":\"$code\",\"load_per_core\":$load_per_core,\"mem_mb\":${mem_mb:-0}}}" || true
}

if [ -n "$reasons" ]; then
  if [ "$mode" != "throttled" ]; then
    set_cap "$LOW"; $DOCKER pause arvis-reacher >/dev/null 2>&1 || true
    r=${reasons# }; msg="guard: website protection ON — ARVIS limited to $LOW CPU (${r%;})"
    echo "$msg"; logger -t arvis-guard "$msg" 2>/dev/null || true; brain_log warn "$msg"
  fi
  echo "throttled 0" > "$STATE"
else
  if [ "$mode" = "throttled" ]; then
    calm=$((calm + 1))
    if [ "$calm" -ge "$CALM_RUNS" ]; then
      set_cap "$NORMAL"; $DOCKER unpause arvis-reacher >/dev/null 2>&1 || true
      msg="guard: all calm for $CALM_RUNS checks — ARVIS back to $NORMAL CPU (site ${site_ms}ms, load ${load_per_core}/core, ${mem_mb}MB free)"
      echo "$msg"; logger -t arvis-guard "$msg" 2>/dev/null || true; brain_log info "$msg"
      echo "normal 0" > "$STATE"
    else
      echo "throttled $calm" > "$STATE"
    fi
  else
    echo "normal 0" > "$STATE"
  fi
fi
# one compact reading for `journalctl -t arvis-guard`/status checks (only every 10th run when calm)
exit 0
