# JAHIDS.AI Agent Runtime v0.1

A local-first mission API integrating NVIDIA NIM, OpenClaw, and Hermes. This is an early integration runtime, not the complete JAHIDS.AI Control Plane.

## Security defaults
- Single-owner bearer authentication; no public registration or shared default password.
- Runtime refuses to start unless `JAHIDS_API_TOKEN` is a non-placeholder secret at least 32 characters long.
- Every mission read and write requires the owner bearer token.
- Only `GET /healthz` is unauthenticated and exposes liveness only.
- Autonomy defaults to 0 (observe-only); high-impact categories are blocked.
- Approvals bind to provider, prompt, and category; expire after 10 minutes and can be consumed once.
- OpenClaw/Hermes process execution is disabled unless explicitly enabled.
- Default listener is loopback. Docker publishes the service on host loopback.
- Provider secrets are not stored in SQLite.

Read [Authentication and Ownership](../docs/AUTHENTICATION-AND-OWNERSHIP.md) and [SECURITY.md](../SECURITY.md) before enabling execution.

## Run locally
    cd runtime
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -e .
    cp .env.example .env
    chmod 600 .env

Generate an owner token on your host:
    python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

Put the generated value in `JAHIDS_API_TOKEN` in `.env`. Add your NVIDIA key to `NVIDIA_API_KEY` only if you intend to call NIM. Keep the file private.

Load the environment and start:
    set -a
    . ./.env
    set +a
    python -m jahids_runtime.server

The API binds to `127.0.0.1:8787`.

## Docker Compose
    cd runtime
    cp .env.example .env
    chmod 600 .env
    # Set JAHIDS_API_TOKEN and any required provider key in .env.
    docker compose -f compose.yaml up --build -d
    docker compose -f compose.yaml logs -f

Compose publishes port 8787 only on host loopback and persists SQLite in a named volume. Do not change the port mapping to a public interface.

## API authentication
Every route under `/v1` requires:
    Authorization: Bearer <JAHIDS_API_TOKEN>

The owner token is separate from `NVIDIA_API_KEY`. Never reuse one for the other. Rotate the owner token by stopping the service, replacing the secret, and restarting.

## Mission lifecycle
1. `POST /v1/missions` with provider, prompt, and category.
2. `POST /v1/missions/{id}/approve`.
3. `POST /v1/missions/{id}/execute` with the returned approval_id.

At autonomy 0, execution remains blocked. At autonomy 1, approved model/read/analysis missions can run.

## Tests
    cd runtime
    PYTHONPATH=. python -m unittest discover -s tests -v

## Production gaps
Before remote or multi-user use, add a supported OIDC provider, RBAC, tenant isolation, TLS, rate limiting, durable workers, signed audit events, managed secrets, backup/restore tests, adapter integration tests, and independent security review. Do not expose this development service directly to the public internet.
