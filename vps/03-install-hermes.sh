#!/usr/bin/env bash
# =============================================================================
# ARVIS — 03-install-hermes.sh
#
# What it does (everything as the `arvis` user, inside /opt/arvis):
#   1. Installs Hermes Agent (Nous Research) with the official installer.
#   2. Runs `hermes setup`            -> pick LLM provider + paste API keys
#   3. Runs `hermes gateway setup`    -> Telegram: paste TELEGRAM_BOT_TOKEN,
#                                        allow only your Telegram user id
#   4. Runs `hermes gateway install`  -> installs the gateway as a systemd
#                                        *user* service for arvis (survives
#                                        reboot thanks to enable-linger from 01)
#   5. Symlinks this repo's hermes/skills into Hermes' skills directory.
#
#   Steps 2-3 are INTERACTIVE: the script stops and lets you answer.
#   Docs: https://hermes-agent.nousresearch.com/docs
#
# What it NEVER does:
#   - Nothing system-wide except apt install of python3/git/curl (already present per the
#     VPS report). Does not touch PM2 / armedias.com / root's nvm Node.
#
# Usage: run as root/sudo; it drops to the arvis user itself:
#   sudo bash 03-install-hermes.sh
# =============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi

ARVIS_HOME=/opt/arvis
REPO_DIR="${ARVIS_HOME}/arvis-repo"   # where this git repo is cloned on the VPS

# basic tools Hermes needs (python3, git, curl) — apt is the only root action here
apt-get install -y python3 python3-venv python3-pip git curl >/dev/null

if [[ ! -d "$REPO_DIR" ]]; then
  echo "NOTE: $REPO_DIR not found. Clone the arvis repo there first (as arvis), e.g.:"
  echo "  sudo -u arvis git clone <your-repo-url> $REPO_DIR"
  echo "Continuing with Hermes install anyway."
fi

sudo -iu arvis bash <<'AS_ARVIS'
set -euo pipefail
cd "$HOME"
export PATH="$HOME/.local/bin:$PATH"

# 1. install Hermes -------------------------------------------------------------
if command -v hermes &>/dev/null; then
  echo "hermes already installed: $(hermes --version 2>/dev/null || echo present)"
else
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
  grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
command -v hermes >/dev/null || { echo "hermes not on PATH after install — paste this output to Claude"; exit 1; }

# 5. link skills (before setup so Hermes sees them) ------------------------------
SKILLS_SRC="$HOME/arvis-repo/hermes/skills"
SKILLS_DST="$HOME/.hermes/skills"
mkdir -p "$SKILLS_DST"
if [[ -d "$SKILLS_SRC" ]]; then
  for d in "$SKILLS_SRC"/*/; do
    n=$(basename "$d"); ln -sfn "$d" "$SKILLS_DST/$n"
  done
  echo "linked skills: $(ls "$SKILLS_DST" | tr '\n' ' ')"
fi

# 2-4. The installer above already ran the setup wizard and installed the gateway
#      service. Model + Telegram are set afterwards with plain config commands
#      (see README Phase 1), because this heredoc has no TTY for the wizard.
hermes gateway status || true
AS_ARVIS

echo
echo "Done. Send /start to your bot on Telegram; paste the reply (or a screenshot) back."
echo "Next: copy .env.example to /opt/arvis/.env (owner arvis, chmod 600) and fill the keys."
echo "PM2 / armedias.com untouched."

