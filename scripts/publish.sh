#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# publish.sh — build the repo and push it to GitHub.
#
# Built by Jahid — AI Agent Developer & Full Stack Engineer
#   github.com/mdjahid11978-design
#
# Usage
#   export GITHUB_TOKEN=ghp_xxx     # or ghp_ / github_pat_
#   ./publish.sh                    # create repo (if needed) + push
#   ./publish.sh --repo my-name     # push to a specific repo name
#   ./publish.sh --public           # make it public (default: public)
#   ./publish.sh --private          # make it private
#
# Token scopes required: repo (or public_repo for public repos).
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OWNER="${GITHUB_OWNER:-mdjahid11978-design}"
REPO_NAME="${REPO_NAME:-openclaw-hermes-free-minimax-m31-flash}"
VISIBILITY="public"
BRANCH="main"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)    REPO_NAME="$2"; shift 2 ;;
    --public)  VISIBILITY="public"; shift ;;
    --private) VISIBILITY="private"; shift ;;
    --owner)   OWNER="$2"; shift 2 ;;
    --branch)  BRANCH="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

command -v gh >/dev/null || { echo "ERROR: gh CLI not found. Install: https://cli.github.com" >&2; exit 1; }
[[ -n "${GITHUB_TOKEN:-}" ]] || { echo "ERROR: GITHUB_TOKEN is not set." >&2; exit 1; }
export GH_TOKEN="$GITHUB_TOKEN"

echo "==> Verifying token"
gh auth status 2>&1 | head -4 || true
login="$(gh api user --jq .login 2>/dev/null || echo "")"
[[ -n "$login" ]] || { echo "ERROR: token is invalid." >&2; exit 1; }
echo "    authenticated as $login"

echo "==> Preparing repo"
cd "$REPO_DIR"
[[ -d .git ]] || git init -q -b "$BRANCH"
git add -A

# Commit only when there is something new to commit.
if git diff --cached --quiet; then
  echo "    nothing new to commit"
else
  git -c user.name="${GIT_AUTHOR_NAME:-Jahid}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-$(gh api user --jq .email 2>/dev/null || echo mdjahid11978-design@users.noreply.github.com)}" \
      commit -q -m "Free MiniMax M3.1 Flash for OpenClaw + Hermes Agent

Both agents pinned to minimaxai/minimax-m3.1-flash on NVIDIA NIM's free
tier (no per-token billing).

- one-shot installer with NFS-safe workspace pre-seeding
- self-healing launchers (reinstall, re-onboard, re-pin model)
- OpenRouter's retired :free slug documented as the reason for the switch
- full visual setup report in docs/

Built by Jahid - AI Agent Developer & Full Stack Engineer"
  echo "    committed"
fi

echo "==> Creating GitHub repo"
if gh repo view "$OWNER/$REPO_NAME" >/dev/null 2>&1; then
  echo "    $OWNER/$REPO_NAME already exists"
else
  gh repo create "$OWNER/$REPO_NAME" --"$VISIBILITY" \
    --description "Run OpenClaw + Hermes Agent on free MiniMax M3.1 Flash via NVIDIA NIM" \
    --homepage "https://github.com/$OWNER/$REPO_NAME" >/dev/null
  echo "    created $OWNER/$REPO_NAME ($VISIBILITY)"
fi

echo "==> Pushing"
# Use the gh credential helper rather than a token-bearing URL — embedding the
# token in the remote URL would write it in plain text into .git/config.
gh auth setup-git >/dev/null 2>&1 || true
git remote add origin "https://github.com/$OWNER/$REPO_NAME.git" 2>/dev/null \
  || git remote set-url origin "https://github.com/$OWNER/$REPO_NAME.git"
git push -u origin "$BRANCH"

echo
echo "Done: https://github.com/$OWNER/$REPO_NAME"
