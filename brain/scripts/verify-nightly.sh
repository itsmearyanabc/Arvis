#!/usr/bin/env bash
# Hermes cron (script-only, no LLM): verify pending contact emails with Reacher, 06:30 IST.
export PATH="$HOME/.local/bin:$PATH"
arvisctl verify --limit 60 2>&1 | tail -3
