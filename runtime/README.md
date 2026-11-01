# JAHIDS.AI Agent Runtime v0.1

A dependency-free mission API providing a governed execution boundary around NVIDIA NIM, OpenClaw, and Hermes. This is an integration runtime for this repository, not the complete JAHIDS.AI sovereign platform.

## Safety defaults
- Autonomy is 0 (observe-only) by default.
- Every mission requires a separate approval call. Approval binds to the exact provider, prompt, and category hash.
- Deploy, finance, credentials, destructive, legal, and ownership categories are blocked.
- API writes and mission reads require JAHIDS_API_TOKEN.
- Remote binding is blocked unless JAHIDS_ALLOW_REMOTE_BIND=true.
- OpenClaw/Hermes execution is disabled unless JAHIDS_ENABLE_LOCAL_AGENTS=true. Commands use JSON argv arrays and never a shell.
- Mission state is stored in SQLite; provider keys are not stored.

## Run locally
    cd runtime
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -e .
    cp .env.example .env
    export JAHIDS_API_TOKEN='replace-this-before-running'
    python -m jahids_runtime.server

The API binds to 127.0.0.1:8787. Check GET /healthz.

## Mission lifecycle
All mission endpoints except healthz require Authorization: Bearer $JAHIDS_API_TOKEN.
1. POST /v1/missions with provider, prompt, and category.
2. POST /v1/missions/{id}/approve.
3. POST /v1/missions/{id}/execute with the returned approval_id.
At autonomy level 0, execution remains blocked. At level 1, approved model/read/analysis missions can run.

## NVIDIA NIM
Set NVIDIA_API_KEY in the runtime environment. The model identifier is configurable with JAHIDS_NIM_MODEL; verify the identifier enabled for your NVIDIA account. NVIDIA usage and rate limits are controlled by NVIDIA.

## OpenClaw and Hermes
Adapters require local binaries and explicit opt-in. Configure JAHIDS_OPENCLAW_ARGV and JAHIDS_HERMES_ARGV as JSON arrays containing the approved executable and fixed arguments. The runtime appends the prompt as the final argument. Test commands manually before enabling local execution.

## Tests
    cd runtime
    PYTHONPATH=. python -m unittest discover -s tests -v

## Production gaps
Before internet exposure, add OIDC/RBAC, tenant isolation, TLS/reverse proxy, rate limiting, durable workers, signed audit events, encrypted secret management, backup/restore tests, adapter integration tests, and independent security review. Do not expose this service directly to the public internet.
