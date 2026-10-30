#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup.sh — install OpenClaw + Hermes Agent, both on FREE MiniMax M3.1 Flash.
#
# Built by Jahid — AI Agent Developer & Full Stack Engineer
#   github.com/mdjahid11978-design
#
# What it does
#   1. Installs Node 24 (required by OpenClaw >= 2026.10) under ~/.home/tools
#   2. Installs OpenClaw (npm, latest stable)
#   3. Installs Hermes Agent (official installer, stable channel)
#   4. Points both at minimaxai/minimax-m3.1-flash on NVIDIA NIM's free tier
#   5. Verifies both resolve to the model
#
# Usage
#   ./setup.sh              # full install
#   ./setup.sh --verify     # just verify an existing install
#
# You still need ONE free key for the model itself:
#   https://build.nvidia.com/settings/api-keys   (no credit card required)
#   export NVIDIA_API_KEY=nvapi-...
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${HOME:?HOME must be set}"
TOOLS_DIR="$HOME_DIR/tools"
NODE_DIR="$TOOLS_DIR/node24"
STATE_DIR="$HOME_DIR/openclaw-state"
HERMES_HOME_DIR="$HOME_DIR/.hermes"
NODE_VERSION="24.22.1"
MODEL="minimaxai/minimax-m3.1-flash"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
die()  { printf '\n\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# NFS-backed mounts can return a spurious ENOTEMPTY on rmdir, so retry removals.
rm_rf() {
  local p="$1" i
  for i in 1 2 3 4 5; do
    rm -rf "$p" 2>/dev/null || true
    [[ -e "$p" ]] || return 0
    sleep 1
  done
  return 1
}

VERIFY_ONLY=0
[[ "${1:-}" == "--verify" ]] && VERIFY_ONLY=1

# ---------------------------------------------------------------------------
say "Preflight"
# ---------------------------------------------------------------------------
command -v curl  >/dev/null || die "curl is required"
command -v git   >/dev/null || die "git is required"
command -v tar   >/dev/null || die "tar is required"
info "curl, git, tar present"

# The default Aliyun PyPI mirror in some images is unreachable — force pypi.org.
export UV_INDEX_URL="${UV_INDEX_URL:-https://pypi.org/simple}"
export UV_DEFAULT_INDEX="${UV_DEFAULT_INDEX:-https://pypi.org/simple}"

# ---------------------------------------------------------------------------
say "Node.js $NODE_VERSION"
# ---------------------------------------------------------------------------
if [[ ! -x "$NODE_DIR/bin/node" ]]; then
  info "downloading…"
  mkdir -p "$TOOLS_DIR"
  curl -fsSL --max-time 600 -o "$TOOLS_DIR/node.tar.xz" \
    "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz"
  mkdir -p "$NODE_DIR"
  tar -xJf "$TOOLS_DIR/node.tar.xz" -C "$NODE_DIR" --strip-components=1
  rm -f "$TOOLS_DIR/node.tar.xz"
fi
export PATH="$NODE_DIR/bin:$PATH"
info "node $(node -v)  ·  npm $(npm -v)"

# ---------------------------------------------------------------------------
say "OpenClaw"
# ---------------------------------------------------------------------------
if [[ ! -x "$NODE_DIR/bin/openclaw" ]]; then
  info "installing latest stable…"
  # Clear any partial install first — npm's own cleanup can hit ENOTEMPTY on NFS.
  rm_rf "$NODE_DIR/lib/node_modules/openclaw"
  npm install -g openclaw@latest --prefix "$NODE_DIR" \
    --allow-scripts=@google/genai,esbuild,koffi,protobufjs,openclaw
fi
info "openclaw $("$NODE_DIR/bin/openclaw" --version 2>/dev/null | head -1)"

export OPENCLAW_STATE_DIR="$STATE_DIR"

if [[ ! -f "$STATE_DIR/openclaw.json" ]]; then
  info "onboarding…"

  # The workspace mount may be NFS-backed, which rejects OpenClaw's hardlink-based
  # atomic publish and aborts onboarding with `unsafe workspace file "IDENTITY.md"`.
  # Pre-seeding the workspace templates makes OpenClaw publish them via the plain
  # (non-atomic) path, which works on NFS.
  TPL="$NODE_DIR/lib/node_modules/openclaw/docs/reference/templates"
  WS="$STATE_DIR/workspace"
  mkdir -p "$WS"
  for f in AGENTS.md SOUL.md IDENTITY.md USER.md BOOTSTRAP.md; do
    [[ -f "$TPL/$f" ]] && cp -n "$TPL/$f" "$WS/$f" 2>/dev/null || true
  done

  ( cd "$STATE_DIR" && "$NODE_DIR/bin/openclaw" onboard --non-interactive \
      --accept-risk --skip-health --auth-choice nvidia-api-key --secret-input-mode ref )
else
  info "state already present"
fi

# Pin the model. Onboard defaults to the catalog's first model, so always re-apply.
PATCH_FILE="$SCRIPT_DIR/../config/openclaw-m31-flash.patch.json5"
if [[ -f "$PATCH_FILE" ]]; then
  ( cd "$STATE_DIR" && "$NODE_DIR/bin/openclaw" config patch --file "$PATCH_FILE" >/dev/null 2>&1 ) || true
  ( cd "$STATE_DIR" && "$NODE_DIR/bin/openclaw" config unset \
      'agents.defaults.models.nvidia/nemotron-3-ultra-550b-a55b' >/dev/null 2>&1 ) || true
  info "model pinned to nvidia/$MODEL"
fi

# ---------------------------------------------------------------------------
say "Hermes Agent"
# ---------------------------------------------------------------------------
HERMES_BIN="$HERMES_HOME_DIR/hermes-agent/.hermes/bin/hermes"
if [[ ! -x "$HERMES_BIN" ]]; then
  info "installing latest stable…"
  INSTALLER="$(mktemp)"
  curl -fsSL --max-time 120 -o "$INSTALLER" \
    "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh"
  bash "$INSTALLER" --non-interactive || bash "$INSTALLER" --stage venv
  rm -f "$INSTALLER"
fi
export PATH="$HERMES_HOME_DIR/hermes-agent/.hermes/bin:$PATH"
info "hermes $("$HERMES_BIN" --version 2>/dev/null | head -1)"

if command -v hermes >/dev/null 2>&1; then
  hermes config set model.default "$MODEL"    >/dev/null 2>&1 || true
  hermes config set model.provider "nvidia"  >/dev/null 2>&1 || true
  hermes config set model.base_url "https://integrate.api.nvidia.com/v1" >/dev/null 2>&1 || true
  hermes config set model.context_length "1000000" >/dev/null 2>&1 || true
  # agent.reasoning_effort is YAML-only (no `hermes config set` support) — edit directly.
  if ! grep -qE '^\s*reasoning_effort:\s*"' "$HERMES_HOME_DIR/config.yaml" 2>/dev/null; then
    python3 - "$HERMES_HOME_DIR/config.yaml" <<'PY' 2>/dev/null || true
import re, sys
p = sys.argv[1]
s = open(p).read()
m = re.search(r'^agent:\s*$', s, re.M)
if m and 'reasoning_effort:' not in s[m.end():]:
    s = s[:m.end()] + '  reasoning_effort: "medium"\n' + s[m.end():]
    open(p, 'w').write(s)
PY
  fi
  info "model pinned to $MODEL"
fi

# ---------------------------------------------------------------------------
say "Verify"
# ---------------------------------------------------------------------------
export OPENCLAW_STATE_DIR="$STATE_DIR"
oc_model="$("$NODE_DIR/bin/openclaw" models status --plain 2>/dev/null | head -1)"
[[ "$oc_model" == *"$MODEL"* ]] && info "OpenClaw -> $oc_model" || info "OpenClaw -> ${oc_model:-unresolved}"

if command -v hermes >/dev/null 2>&1; then
  h_model="$(hermes config get model.default 2>/dev/null | tail -1)"
  [[ "$h_model" == *"$MODEL"* ]] && info "Hermes   -> $h_model" || info "Hermes   -> ${h_model:-unresolved}"
fi

cat <<'DONE'

Done. One key is still needed for the model itself:

  1. Get a free key (no credit card):
       https://build.nvidia.com/settings/api-keys
  2. export NVIDIA_API_KEY=nvapi-...
  3. ./scripts/run-openclaw.sh     # OpenClaw
     ./scripts/run-hermes.sh        # Hermes Agent

DONE
