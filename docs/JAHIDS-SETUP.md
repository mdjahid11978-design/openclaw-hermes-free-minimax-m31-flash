# JAHIDS.AI Setup & Operations

This repository provides scripts to install and configure OpenClaw and Hermes Agent
with MiniMax M3.1 Flash via NVIDIA NIM.

## Requirements

- Linux x86_64 (the Node download in this repo targets linux-x64)
- `bash`, `curl`, `git`, `tar`, `python3`
- Network access to Node.js, npm, NVIDIA NIM, and Hermes installer hosts
- NVIDIA API key: https://build.nvidia.com/settings/api-keys

## Install

From the repository root:

```bash
chmod +x scripts/*.sh
./scripts/setup.sh
```

Then supply the key securely in your shell (do not paste it into GitHub issues or commit it):

```bash
export NVIDIA_API_KEY="nvapi-…"
./scripts/run-openclaw.sh
# In a separate terminal:
./scripts/run-hermes.sh
```

For a one-shot Hermes request:

```bash
./scripts/run-hermes.sh -z "Reply with a short greeting"
```

## Verify

```bash
./scripts/setup.sh --verify
bash -n scripts/setup.sh scripts/run-openclaw.sh scripts/run-hermes.sh
```

The GitHub Actions validation workflow checks shell syntax and scans commits
for exposed secrets. It cannot install services on your personal device or
validate your private NVIDIA key.

## Safe automation boundary

The scripts install software and modify local OpenClaw/Hermes configuration.
Review the requested permissions and commands before running them. Do not enable
unattended execution of host shell, messaging, browser, or file tools without
an explicit policy and sandbox.

## Free-tier note

NVIDIA NIM free endpoints may impose rate limits, availability restrictions,
and trial/evaluation terms. No fallback to a paid provider is configured by
default. Review NVIDIA's current terms before commercial or production use.
