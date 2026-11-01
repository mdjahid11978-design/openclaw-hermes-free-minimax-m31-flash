#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Launch Hermes Agent with MiniMax M3.1 Flash via NVIDIA NIM.
#
# Built by Jahid — AI Agent Developer & Full Stack Engineer
#   github.com/mdjahid11978-design
#
# Why this file exists
#   OpenRouter's free `minimax/minimax-m3.1-flash:free` slug was retired on
#   2026-10-22. NVIDIA's build.nvidia.com catalog still serves
#   `minimaxai/minimax-m3.1-flash` subject to NVIDIA account pricing, trial eligibility, and rate limits.
#
# Setup (once):
#   1. Get a free key: https://build.nvidia.com/settings/api-keys   (no credit card)
#   2. read -rsp "NVIDIA API key: " NVIDIA_API_KEY; echo; export NVIDIA_API_KEY
#   3. ./run-hermes.sh
#
# Hermes lives under ~/.hermes (persistent) and its model config is already
# pinned to MiniMax-M3.1-Flash. This script just carries the runtime paths
# and the PyPI index override the installer needs.
# ---------------------------------------------------------------------------
set -euo pipefail

HERMES_ROOT="${HOME:?HOME must be set}/.hermes/hermes-agent"
export PATH="$HERMES_ROOT/.hermes/bin:${PATH}"

# --- uv/pip index (the sandbox default Aliyun mirror is unreachable) --------
export UV_INDEX_URL="${UV_INDEX_URL:-https://pypi.org/simple}"
export UV_DEFAULT_INDEX="${UV_DEFAULT_INDEX:-https://pypi.org/simple}"

# --- The free key -----------------------------------------------------------
if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
  cat >&2 <<'MSG'
ERROR: NVIDIA_API_KEY is not set.

Create an NVIDIA API key in your NVIDIA account:
  https://build.nvidia.com/settings/api-keys

Then:
  export NVIDIA_API_KEY=nvapi-...
MSG
  exit 1
fi

exec hermes "$@"
