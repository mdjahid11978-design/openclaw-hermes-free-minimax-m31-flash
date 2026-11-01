# OpenClaw + Hermes on MiniMax M3.1 Flash via NVIDIA NIM

**Built by Jahid** · [GitHub owner](https://github.com/mdjahid11978-design)

This repository contains setup scripts for OpenClaw and Hermes Agent, plus an optional JAHIDS.AI governed mission API.

> Provider pricing, free-tier eligibility, rate limits, model identifiers, and terms can change. Check the current NVIDIA NIM catalog and your account before relying on any free-tier or production assumption. The project deliberately configures no paid fallback.

## Quick start
1. Create an NVIDIA API key in your NVIDIA account if you intend to use NIM.
2. Install:
       chmod +x scripts/*.sh
       ./scripts/setup.sh
3. Read the key without placing it in shell history:
       read -rsp "NVIDIA API key: " NVIDIA_API_KEY
       echo
       export NVIDIA_API_KEY
4. Start one agent:
       ./scripts/run-openclaw.sh
       # or, in a separate terminal:
       ./scripts/run-hermes.sh

## Authentication and security
- NVIDIA credentials use `NVIDIA_API_KEY`; they are not written into tracked model configuration.
- The optional JAHIDS runtime has a separate single-owner `JAHIDS_API_TOKEN`.
- Runtime mission endpoints require `Authorization: Bearer <owner-token>`; only liveness is unauthenticated.
- Runtime autonomy defaults to 0 (observe-only), high-impact categories are blocked, and local agent execution is disabled by default.
- Keep credentials in a local secret manager or protected environment file. Never commit them.
- See [Security Policy](SECURITY.md) and [Authentication & Ownership](docs/AUTHENTICATION-AND-OWNERSHIP.md).

## Repository contents
- `scripts/setup.sh` — installs OpenClaw and Hermes.
- `scripts/run-openclaw.sh` — launches OpenClaw and reapplies the model configuration.
- `scripts/run-hermes.sh` — launches Hermes.
- `config/openclaw-m31-flash.patch.json5` — provider/model configuration; no API key.
- `runtime/` — mission API, owner authentication, Governor, SQLite store, adapters, Docker setup, and tests.
- `docs/` — setup and ownership documentation.

## Verify
    ./scripts/setup.sh --verify
    bash -n scripts/setup.sh scripts/run-openclaw.sh scripts/run-hermes.sh
    cd runtime && PYTHONPATH=. python -m unittest discover -s tests -v

## Limitations
This is an agent setup and integration project, not the full JAHIDS.AI Control Plane. It does not provide multi-user OIDC/RBAC or tenant isolation and must not be exposed directly to the public internet. Production use requires a reviewed identity provider, TLS, network controls, durable execution, audit evidence, secret management, backups, and security review.

## Credits and third-party terms
Built by [Jahid](https://github.com/mdjahid11978-design). See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE). Provider and model use remains subject to upstream terms.
