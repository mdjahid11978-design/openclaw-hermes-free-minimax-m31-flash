#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Launch OpenClaw on the FREE MiniMax M3.1 Flash endpoint (NVIDIA NIM).
#
# Built by Jahid — AI Agent Developer & Full Stack Engineer
#   github.com/mdjahid11978-design
#
# Why this file exists
#   The obvious free route — OpenRouter's `minimax/minimax-m3.1-flash:free` —
#   was reported as retired in the project notes on 2026-10-22. Check the current catalog; the
#   available model identifiers and pricing may change.
#   NVIDIA's build.nvidia.com catalog still serves `minimaxai/minimax-m3.1-flash`
#   subject to NVIDIA account pricing, trial eligibility, and rate limits.
#
# Setup (once):
#   1. Get a free key: https://build.nvidia.com/settings/api-keys   (no credit card)
#   2. export NVIDIA_API_KEY=nvapi-...
#   3. ./run-openclaw.sh
#
# This script also self-heals: if the Node 24 runtime or the OpenClaw state
# directory is missing (e.g. after a sandbox restart), it rebuilds them.
# ---------------------------------------------------------------------------
set -euo pipefail

TOOLS_DIR="${HOME:?HOME must be set}/tools"
NODE_DIR="$TOOLS_DIR/node24"
STATE_DIR="${OPENCLAW_STATE_DIR:-${HOME:?HOME must be set}/openclaw-state}"

export PATH="$NODE_DIR/bin:${PATH}"
export OPENCLAW_STATE_DIR="$STATE_DIR"

# --- The free key -----------------------------------------------------------
if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
  cat >&2 <<'MSG'
ERROR: NVIDIA_API_KEY is not set.

Create an NVIDIA API key in your NVIDIA account:
  https://build.nvidia.com/settings/api-keys

Then:
  read -rsp "NVIDIA API key: " NVIDIA_API_KEY; echo; export NVIDIA_API_KEY
MSG
  exit 1
fi

# --- Self-heal: Node 24 runtime (OpenClaw >= 2026.10 requires >=24.22.1) ---
if [[ ! -x "$NODE_DIR/bin/node" ]]; then
  echo "[setup] Node 24 missing — installing..." >&2
  mkdir -p "$TOOLS_DIR"
  curl -fsSL --max-time 300 -o "$TOOLS_DIR/node.tar.xz" \
    "https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz"
  mkdir -p "$NODE_DIR"
  tar -xJf "$TOOLS_DIR/node.tar.xz" -C "$NODE_DIR" --strip-components=1
  rm -f "$TOOLS_DIR/node.tar.xz"
fi

# --- Self-heal: OpenClaw package ---------------------------------------------
if [[ ! -x "$NODE_DIR/bin/openclaw" ]]; then
  echo "[setup] OpenClaw missing — installing..." >&2
  npm install -g openclaw@latest --prefix "$NODE_DIR" \
    --allow-scripts=@google/genai,esbuild,koffi,protobufjs,openclaw
fi

# --- Self-heal: state dir + config -------------------------------------------
if [[ ! -f "$STATE_DIR/openclaw.json" ]]; then
  echo "[setup] OpenClaw state missing — onboarding..." >&2
  mkdir -p "$STATE_DIR"

  # The workspace mount here is NFS-backed and rejects the hardlink-based
  # atomic publish OpenClaw uses for bootstrap files, which aborts onboarding
  # with `unsafe workspace file "IDENTITY.md"`. Pre-seeding the workspace
  # templates makes OpenClaw publish them via the plain (non-atomic) path.
  TPL="$NODE_DIR/lib/node_modules/openclaw/docs/reference/templates"
  WS="$STATE_DIR/workspace"
  mkdir -p "$WS"
  for f in AGENTS.md SOUL.md IDENTITY.md USER.md BOOTSTRAP.md; do
    [[ -f "$TPL/$f" ]] && cp -n "$TPL/$f" "$WS/$f" 2>/dev/null || true
  done

  ( cd "$STATE_DIR" && openclaw onboard --non-interactive --accept-risk \
      --skip-health --auth-choice nvidia-api-key --secret-input-mode ref )
fi

# --- Ensure the model is pinned to MiniMax M3.1 Flash (free NVIDIA route) ---
# Onboard defaults to whatever the provider catalog lists first, so re-apply
# the model patch on every launch. It is idempotent and cheap.
PATCH_FILE="${OPENCLAW_MODEL_PATCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../config/openclaw-m31-flash.patch.json5}"
if [[ -f "$PATCH_FILE" ]]; then
  ( cd "$STATE_DIR" && openclaw config patch --file "$PATCH_FILE" >/dev/null 2>&1 ) || true
  # Drop the catalog default alias so only the free model is selectable.
  ( cd "$STATE_DIR" && openclaw config unset \
      'agents.defaults.models.nvidia/nemotron-3-ultra-550b-a55b' >/dev/null 2>&1 ) || true
fi

exec openclaw "$@"
