# JAHIDS.AI Control Center

## What it is

The Control Center is a browser interface served by the local JAHIDS.AI Agent Runtime. It provides a single-owner view of missions, the Governor's current autonomy level, configured agent adapters, and mission activity.

## Start

From the repository root:

    cp runtime/.env.example runtime/.env
    chmod 600 runtime/.env
    # Generate a token with: python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
    # Set JAHIDS_API_TOKEN in runtime/.env.
    docker compose -f runtime/compose.yaml up --build -d

Open http://127.0.0.1:8787/ and enter the owner token. The token remains in the current page's JavaScript memory and is not persisted by the UI.

For a non-Docker run, follow the local setup in runtime/README.md. Start the runtime from the repository's runtime directory so the source-tree web assets resolve.

## Pages

- Overview: mission counts, recent missions, runtime connection state and adapter summary.
- Missions: list stored missions, create a mission and request owner approval for pending work.
- Agents & models: configured adapter types and model route notes.
- Governance: autonomy level and blocked categories reported by the server.
- Audit activity: recent mission records from the SQLite store.

## API contract

All API calls require Authorization: Bearer <JAHIDS_API_TOKEN>.

- GET /v1/status
- GET /v1/missions
- GET /v1/missions/{id}
- POST /v1/missions
- POST /v1/missions/{id}/approve
- POST /v1/missions/{id}/execute

The UI does not receive provider API keys and cannot alter autonomy policy. The server remains the policy authority.

## Security notes

- The HTML shell is public; it contains no credentials. The API remains protected.
- Use only on localhost. Docker publishes the port on 127.0.0.1.
- The UI keeps the bearer token in page memory only. Closing or refreshing the tab clears it.
- Do not paste the token into browser extensions, shared devices, screenshots, or support tickets.
- The UI does not provide multi-user login, OIDC, RBAC, tenant isolation, signed audit records, or a production deployment workflow.
- Agent labels are configuration metadata, not live health checks. The activity feed is derived from mission rows, not a tamper-evident audit log.

## Validation

Run:

    cd runtime
    PYTHONPATH=. python -m unittest discover -s tests -v

The Control Center HTTP tests verify that the UI shell is served, the status API requires owner authentication, and the status response does not disclose secrets.
