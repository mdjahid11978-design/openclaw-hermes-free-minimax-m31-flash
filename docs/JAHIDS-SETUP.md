# JAHIDS.AI Setup & Operations

This repository installs and configures OpenClaw and Hermes Agent with MiniMax M3.1 Flash via NVIDIA NIM, and includes an optional local mission API.

## Requirements
- Linux x86_64
- `bash`, `curl`, `git`, `tar`, `python3`
- Network access to Node.js, npm, NVIDIA NIM, and the Hermes installer host
- NVIDIA API key if you intend to call NIM: https://build.nvidia.com/settings/api-keys

## Install
From the repository root:
    chmod +x scripts/*.sh
    ./scripts/setup.sh

The installer uses `$HOME/tools/node24`, `$HOME/openclaw-state`, and `$HOME/.hermes`. It does not require provider credentials in tracked config files.

## Provider authentication
Use a hidden prompt so the key is not written into shell history:
    read -rsp "NVIDIA API key: " NVIDIA_API_KEY
    echo
    export NVIDIA_API_KEY

Then launch:
    ./scripts/run-openclaw.sh

In a separate terminal, repeat the secure prompt/export and run:
    ./scripts/run-hermes.sh

For a one-shot Hermes request:
    ./scripts/run-hermes.sh -z "Reply with a short greeting"

Never paste API keys into GitHub, chat, issue comments, screenshots, or source files. Revoke and replace an exposed key.

## Verify
`./scripts/setup.sh --verify` is read-only. It checks installed binaries and model configuration without installing or changing anything.
    ./scripts/setup.sh --verify
    bash -n scripts/setup.sh scripts/run-openclaw.sh scripts/run-hermes.sh

GitHub Actions validates Python tests, shell syntax, JSON5 syntax, and scans for exposed secrets. It cannot test your private provider key or install software on your host.

## Optional JAHIDS mission API
See [runtime/README.md](../runtime/README.md) and [Authentication and Ownership](AUTHENTICATION-AND-OWNERSHIP.md). The API has a separate owner token, defaults to observe-only autonomy, and listens on loopback.

## Automation boundary
Review commands and permissions before running agents. Do not enable unattended host shell, messaging, browser, or file tools without explicit policy and a sandbox.

## Provider terms and pricing
NVIDIA controls endpoint availability, rate limits, trial terms, and pricing. Confirm current terms in your NVIDIA account before production or commercial use. No paid fallback is configured by default.
