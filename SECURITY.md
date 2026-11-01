# Security and access policy

## Repository ownership
This source repository is maintained under the personal GitHub account `mdjahid11978-design`. It was observed as **public** on 2026-11-01. Public source is readable by anyone. To restrict source access, the account owner must change visibility to private in GitHub Settings and review collaborators and installed applications. See [Authentication and Ownership](docs/AUTHENTICATION-AND-OWNERSHIP.md).

## Runtime authentication
The runtime uses a single-owner bearer secret. It has no public registration, password login, token issuance, or anonymous mission access.
- Generate a random secret locally with Python `secrets.token_urlsafe(48)`.
- Set `JAHIDS_API_TOKEN` to a non-placeholder secret of at least 32 characters.
- The runtime refuses to start if the owner credential is missing or weak.
- Send it only as `Authorization: Bearer <secret>`.
- Every mission list/read/create/approve/execute route requires the owner credential.
- `GET /healthz` is the only unauthenticated route and returns liveness only.
- Rotate the key by stopping the service, replacing the secret, and restarting.
- Keep local `.env` files mode 0600 and outside version control. Never commit provider keys, owner keys, bot tokens, or credential-bearing config.

The bearer key grants owner-level access to all mission endpoints. Do not share it with agents, plugins, collaborators, or client-side applications. For multiple people, use OIDC and role-based authorization instead of sharing this key.

## Network boundary
- Default bind is `127.0.0.1`.
- Docker Compose publishes the service only on host loopback.
- Do not expose the port directly to the internet.
- Remote deployment requires a TLS reverse proxy, firewall restrictions, rate limiting, and a reviewed identity layer.
- This is a single-owner development integration, not a multi-tenant production identity service.

## Provider credentials
Keep `NVIDIA_API_KEY` in a local secret manager or protected environment file. Rotate it immediately if exposed. Local OpenClaw/Hermes process adapters remain disabled by default.

## Vulnerability reporting
Do not publish secrets or exploitable details in public issues. Use GitHub's private vulnerability reporting/security advisory feature where available.
