# JAHIDS.AI Delivery Plan

**Planning baseline:** 2026-11-02  
**Repository:** `mdjahid11978-design/openclaw-hermes-free-minimax-m31-flash`  
**Rule:** One repository, one product identity, one governed platform.

This plan sequences implementation by dependency and risk. Do not start later phases by creating disconnected UI screens or mock APIs.

## Current repository state

- OpenClaw and Hermes setup scripts configure MiniMax M3.1 Flash through NVIDIA NIM.
- Optional JAHIDS runtime provides an HTTP API, SQLite mission persistence, owner bearer authentication, Governor, NIM/OpenClaw/Hermes adapters, and a single-page Control Center.
- SMTP sending is server-side and restricted by an exact recipient allowlist.
- Runtime package/API version is 0.2.0.
- The current identity is single-owner bearer authentication; it is not multi-user OIDC/RBAC.
- The current mission store is SQLite; it is not a distributed worker queue.
- The current UI is a single HTML/JavaScript file; it is not yet a Next.js application.
- Production deployment and public exposure are not approved.

## Delivery sequence

### Phase 0 — Stabilize and establish engineering controls
**Goal:** Make the existing repository reproducible before adding platform complexity.

- [ ] Confirm the repository default branch, visibility, branch protection, CODEOWNERS, and required status checks.
- [ ] Run the complete Python suite, shell syntax checks, JSON5 validation, secret scan, and Docker build on a functioning runner.
- [ ] Fix runner startup/configuration failures separately from code/test failures.
- [ ] Pin CI actions and external tool versions; avoid unpinned `npx` execution in release checks.
- [ ] Add dependency and container vulnerability scanning.
- [ ] Add API contract and smoke tests.
- [ ] Add backup/restore tests for the current SQLite store.
- [ ] Record the exact tested commit and artifact digest.

**Exit gate:** CI passes on a clean commit; runtime starts from the documented Compose setup; health, auth, mission, and email paths have integration tests.

### Phase 1 — Define contracts and separate the runtime domains
**Goal:** Refactor the monolithic runtime without breaking existing users.

- [ ] Introduce typed request/response schemas and API versioning.
- [ ] Separate HTTP routing from application services, domain models, persistence, adapters, and configuration.
- [ ] Define mission state transitions and invalid-transition behavior.
- [ ] Add structured audit events and correlation IDs.
- [ ] Add adapter timeouts, bounded response sizes, retry classification, and cancellation.
- [ ] Add provider-neutral model routing behind a stable interface.
- [ ] Keep current routes and CLI/Compose behavior compatible during migration.

**Exit gate:** Existing behavior has regression coverage; domain modules can be tested without starting the HTTP server.

### Phase 2 — Identity, access control, and owner administration
**Goal:** Replace shared owner-token access with real human identities.

- [ ] Integrate OIDC Authorization Code + PKCE with a selected identity provider.
- [ ] Add MFA/step-up authentication through the identity provider.
- [ ] Add users, service identities, organizations, workspaces, memberships, roles, and permission assignments.
- [ ] Define RBAC plus ABAC rules for resource, workspace, action, risk, and environment.
- [ ] Enforce authorization at every API route and data access boundary.
- [ ] Add invitation, deactivation, session revocation, and recovery workflows.
- [ ] Keep the bootstrap owner path isolated, audited, and removable after migration.
- [ ] Add negative tests for privilege escalation, cross-workspace reads, and revoked sessions.

**Exit gate:** Two or more users with different roles can safely use separate workspaces; no shared owner bearer token is needed for normal use.

### Phase 3 — Data platform and operational reliability
**Goal:** Move mission and identity state to a production-capable system of record.

- [ ] Introduce PostgreSQL migrations and schema ownership.
- [ ] Implement tenant/workspace isolation with server-derived scope and database enforcement.
- [ ] Migrate SQLite data with checksums, reconciliation, and rollback.
- [ ] Add encrypted backups and a tested restore procedure.
- [ ] Add Redis only for required cache/leases/coordination.
- [ ] Implement transactional outbox and durable job dispatch.
- [ ] Add idempotency keys, worker leases, fencing tokens, retries, dead-letter handling, and cancellation.
- [ ] Add retention, export, and deletion policies.

**Exit gate:** A worker restart does not lose or duplicate mission state; backup restoration is demonstrated; isolation tests pass.

### Phase 4 — Governor, approvals, and mission execution
**Goal:** Make governance the mandatory execution boundary.

- [ ] Version policies and store policy decision inputs/results.
- [ ] Add risk scoring, budget reservations, autonomy scopes, and explicit deny-by-default rules.
- [ ] Bind approvals to exact payload hash, target, environment, workspace, scope, expiry, and one-time nonce.
- [ ] Consume approvals atomically and reject changed payloads.
- [ ] Add mission DAGs, checkpoints, execution plans, and state transition guards.
- [ ] Add sandbox profiles, network egress controls, resource/time limits, and per-mission credentials.
- [ ] Add kill switch, pause/resume, cancellation, and safe recovery.
- [ ] Add evidence-backed verification and rollback hooks.

**Exit gate:** Every execution path passes through the same Governor; tests prove workers cannot bypass approvals or expand their permissions.

### Phase 5 — Agent fleet, groups, assistants, and MCP
**Goal:** Manage workers as registered, bounded capabilities.

- [ ] Define signed/versioned agent manifests and capability declarations.
- [ ] Add registry, health, version, reputation, and drift tracking.
- [ ] Add agent groups and assistant profiles as policy-bound compositions, not separate authorities.
- [ ] Add supervisor and router that can propose/assign work but cannot override the Governor.
- [ ] Build one MCP gateway with tool schemas, scopes, credential references, timeouts, and audit events.
- [ ] Add model/provider adapters behind the model router.
- [ ] Keep OpenClaw and Hermes as optional worker adapters with explicit process and filesystem boundaries.
- [ ] Add conformance and adversarial tests for prompt injection and tool misuse.

**Exit gate:** Every worker has a manifest, scoped capability grant, bounded execution environment, and traceable evidence.

### Phase 6 — Control Center and developer surfaces
**Goal:** Build a UI that reflects real backend capabilities and authorization.

- [ ] Migrate the current single-page UI to Next.js in a controlled, tested transition.
- [ ] Build role-aware navigation and server-enforced permissions.
- [ ] Add mission timeline, approvals, agent fleet, groups, tools, memory/knowledge, audit, and system health views.
- [ ] Add owner administration, user lifecycle, workspace management, and policy administration.
- [ ] Add SDK/API docs and a CLI against the same versioned contracts.
- [ ] Add accessibility, responsive behavior, error states, loading states, and end-to-end tests.
- [ ] Never implement security by hiding a button; enforce it in the API.

**Exit gate:** UI actions map to tested APIs; role and workspace tests cover every protected surface.

### Phase 7 — Production readiness
**Goal:** Release only after evidence and operational ownership are in place.

- [ ] Separate development, staging, and production accounts/environments.
- [ ] Configure TLS, DNS, WAF, firewall, rate limits, and secure headers.
- [ ] Configure secret management, key rotation, and incident response.
- [ ] Configure SLOs, alerts, dashboards, tracing, log redaction, and on-call ownership.
- [ ] Run dependency, container, application, and authorization security reviews.
- [ ] Run load, soak, failure-injection, restore, and rollback tests.
- [ ] Require protected approval for production deployment.
- [ ] Verify the exact artifact, migration, health checks, and rollback plan before cutover.

**Exit gate:** Signed release evidence, successful staging rehearsal, tested rollback, and explicit owner approval.

## Work sequencing rules

1. Do not build UI before the underlying API contract and authorization model exist.
2. Do not add multi-user features on top of the shared owner bearer token.
3. Do not add distributed agents before durable mission state, scoped credentials, and the Governor boundary.
4. Do not add PostgreSQL/Redis as decorative infrastructure; add migrations and operational tests with them.
5. Do not enable unattended execution by default. Autonomy remains 0 until separately reviewed.
6. Do not change repository visibility, branch protection, DNS, production deployments, or credentials as part of code-only work.
7. Use short-lived feature branches and pull requests. Keep PRs focused on one architectural capability.
8. Report checks as PASS, FAIL, BLOCKED, or NOT RUN with commit SHA and evidence. Never infer a test pass from a successful code review.
