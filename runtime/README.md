# JAHIDS.AI Agent Runtime v0.2

A local-first mission API and responsive web Control Center integrating NVIDIA NIM, OpenClaw, and Hermes. This is an early single-owner integration, not the complete JAHIDS.AI Control Plane.

## Control Center

Start the runtime, then open http://127.0.0.1:8787/ in your browser. The web console includes:
- Overview cards for mission totals, pending approvals, completed runs, and autonomy level.
- Mission creation and listing with provider/category selection.
- Owner approval requests through the existing Governor API.
- Agent adapter and model configuration summaries.
- Governance policy display and mission activity view.

The UI asks for the owner token when you connect. It keeps the token in page memory only; it does not write it to localStorage, cookies, or a config file. The browser never receives NVIDIA provider credentials. The UI is served by the same-origin runtime API; mission data and actions remain authenticated. The static UI itself is not an authentication boundary.

Adapter labels are configuration summaries, not live process probes. Activity is derived from mission records and is not a signed append-only audit ledger.

## Security defaults

- Single-owner bearer authentication; no public registration or shared default password.
- Runtime refuses to start unless JAHIDS_API_TOKEN is a non-placeholder secret at least 32 characters long.
- Every /v1 API route requires the owner bearer token.
- Only the static UI and GET /healthz are public; health exposes liveness only.
- Autonomy defaults to 0 (observe-only); high-impact categories are blocked.
- Approvals bind to provider, prompt, and category; expire after 10 minutes and can be consumed once.
- OpenClaw/Hermes process execution is disabled unless explicitly enabled.
- Default listener is loopback. Docker publishes the service on host loopback.
- Provider and SMTP credentials are not stored in SQLite.
- SMTP delivery is optional, owner-authenticated, and limited to exact recipient addresses in an environment allowlist.

Read Authentication and Ownership, the Control Center guide, and SECURITY.md before enabling execution.

## Run locally

    cd runtime
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -e .
    cp .env.example .env
    chmod 600 .env

Generate an owner token on your host:

    python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

Put the generated value in JAHIDS_API_TOKEN in .env. Add your NVIDIA key to NVIDIA_API_KEY only if you intend to call NIM. Keep the file private.

Load the environment and start:

    set -a
    . ./.env
    set +a
    python -m jahids_runtime.server

Open http://127.0.0.1:8787/. The API binds to 127.0.0.1:8787.

## Docker Compose

Run from the repository root:

    cp runtime/.env.example runtime/.env
    chmod 600 runtime/.env
    # Set JAHIDS_API_TOKEN and any required provider key in runtime/.env.
    docker compose -f runtime/compose.yaml up --build -d
    docker compose -f runtime/compose.yaml logs -f

Open http://127.0.0.1:8787/. Compose publishes port 8787 only on host loopback and persists SQLite in a named volume. Do not change the port mapping to a public interface.

## API authentication

Every route under /v1 requires:

    Authorization: Bearer <JAHIDS_API_TOKEN>

- GET /v1/status — runtime version and Governor policy summary.
- GET /v1/missions — mission list.
- GET /v1/missions/{id} — mission details.
- POST /v1/missions — create a mission.
- POST /v1/missions/{id}/approve — request Governor approval.
- POST /v1/missions/{id}/execute — execute with the returned approval ID.
- POST /v1/email/send — send plain-text mail through the configured SMTP relay; recipient must appear in `JAHIDS_EMAIL_ALLOWED_RECIPIENTS`.

The owner token is separate from NVIDIA_API_KEY and SMTP credentials. Never reuse one for another. Rotate the owner token by stopping the service, replacing the secret, and restarting.

## Business email relay

This repository integrates with an SMTP provider; it does not create or host mailboxes or control DNS. Configure a mailbox and SMTP relay with your chosen provider, then set `JAHIDS_SMTP_HOST`, `JAHIDS_SMTP_PORT`, `JAHIDS_SMTP_SECURITY` (`ssl` or `starttls`), `JAHIDS_SMTP_USERNAME`, `JAHIDS_SMTP_PASSWORD`, `JAHIDS_EMAIL_FROM`, and a comma-separated exact-address `JAHIDS_EMAIL_ALLOWED_RECIPIENTS` in the protected environment file. The API endpoint requires the owner bearer token. Do not put SMTP credentials in browser code, GitHub, or the image.

Example request:

    curl -X POST http://127.0.0.1:8787/v1/email/send \\
      -H 'Authorization: Bearer YOUR_OWNER_TOKEN' \\
      -H 'Content-Type: application/json' \\
      -d '{"to":"owner@example.com","subject":"Test","text":"JAHIDS.AI email test"}'

The address above is an example only. Configure the real sender and recipient allowlist with your mail provider first.

## Mission lifecycle

1. POST /v1/missions with provider, prompt, and category.
2. POST /v1/missions/{id}/approve.
3. POST /v1/missions/{id}/execute with the returned approval_id.

At autonomy 0, execution remains blocked. The Control Center cannot change autonomy or bypass server policy.

## Tests

    cd runtime
    PYTHONPATH=. python -m unittest discover -s tests -v

## Production gaps

Before remote or multi-user use, add a supported OIDC provider, RBAC, tenant isolation, TLS, rate limiting, durable workers, signed audit events, managed secrets, backup/restore tests, adapter health probes, adapter integration tests, and independent security review. Do not expose this development service directly to the public internet.
