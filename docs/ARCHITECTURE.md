# JAHIDS.AI Architecture

**Status:** Target architecture and current-state boundary  
**Repository:** `mdjahid11978-design/openclaw-hermes-free-minimax-m31-flash`  
**Product identity:** JAHIDS.AI Sovereign AI Platform  
**Attribution:** Built by Jahid

This document is the architecture source of truth for changes in this repository. It distinguishes implemented behavior from the target design. A diagram or target component is not evidence that the component exists.

## 1. Product boundary

This repository currently combines:
1. OpenClaw and Hermes installation/configuration scripts for the MiniMax M3.1 Flash model through NVIDIA NIM.
2. An optional local JAHIDS.AI mission runtime.
3. A browser-based JAHIDS.AI Control Center served by that runtime.

The long-term product is JAHIDS.AI. OpenClaw, Hermes, NVIDIA NIM, and future model providers are integrations or execution adapters. They do not own platform identity, authorization, mission state, or policy.

Do not introduce another company, product identity, tenant owner, or unrelated repository. Keep all work in this repository unless the owner explicitly changes that instruction.

## 2. Non-negotiable system invariants

- One JAHIDS.AI identity and one platform constitution.
- One identity and authorization model.
- One Governor and one policy decision point.
- One cognitive kernel and one mission runtime.
- One agent/assistant fleet registry and one MCP gateway.
- One control plane and one evidence/audit model.
- Many bounded workers; workers never become authorities.
- Computation proposes; it does not grant itself permission.
- Every consequential action is authorized before execution and produces verifiable evidence.
- Default autonomy is level 0 (observe-only). Raising autonomy is a governed configuration change, never a UI shortcut.

## 3. Current implementation (verified in source)

| Area | Current implementation | Boundary / gap |
|---|---|---|
| Installation | Bash setup and launch scripts for OpenClaw and Hermes | Host installation remains user-operated |
| Model access | NVIDIA NIM adapter using server-side `NVIDIA_API_KEY` | Provider-specific adapter; no provider-neutral routing policy yet |
| Runtime API | Python standard-library HTTP server | Small local integration API, not a production control plane |
| Identity | One owner bearer token | No user directory, OIDC, MFA, RBAC, or tenant isolation |
| Policy | Governor with autonomy 0–5, allowlisted low-risk categories, blocked high-impact categories | Policy persistence, policy versioning, and signed decisions are not implemented |
| Missions | SQLite persistence; approval expiry and single-use claim | No durable queue, worker leases, retries, DAG scheduler, or distributed execution |
| Agents | NVIDIA NIM plus opt-in OpenClaw/Hermes process adapters | No fleet registry, manifests, groups, health, or capability authorization |
| Email | SMTP relay with exact recipient allowlist | No mailbox provisioning, inbound email, templates, or delivery event store |
| UI | Single responsive HTML/JS Control Center | Not yet a separated frontend application |
| Operations | Dockerfile, loopback-published Compose service, GitHub Actions workflow | No production deployment approval, backup/restore proof, or full observability |

Treat this table as the baseline. Update it only when code, tests, and operational evidence support a status change.

## 4. Target logical architecture

```text
Web / Mobile / CLI / SDK
          |
     API Edge / BFF
          |
 Identity & Session Service ---- Directory / Organizations / Workspaces
          |
      Control Plane
          |
 Request -> Mission -> Planner -> Agent Router
                         |             |
                    Cognitive      Fleet Registry
                      Kernel       (bounded workers)
                         |             |
                    Knowledge       MCP Gateway
                    & Memory           |
                         |         Tool Adapters
                         +------> Governor <------ Policy / Risk / Budget
                                      |
                               Approval Service
                                      |
                               Mission Runtime
                                      |
                          Sandboxed Worker Execution
                                      |
                         Evidence / Audit / Telemetry
                                      |
                         Verification / Recovery
                                      |
                                Memory Fabric
```

### Authority and execution flow

1. Authenticate the human or service identity.
2. Resolve organization, workspace, role, and requested capability from trusted server-side identity data.
3. Create a mission with a stable ID, owner, scope, budget, deadline, and immutable input digest.
4. Planner and agents propose a plan. Proposals do not authorize execution.
5. Router selects a registered worker with a compatible, bounded manifest.
6. Governor evaluates policy, risk, autonomy, budget, target, and action category.
7. If required, Approval Service asks an authorized human to approve the exact action digest, target, environment, scope, and expiry.
8. Runtime executes only the approved, policy-authorized action in an isolated worker boundary.
9. Evidence is recorded for inputs, decisions, tool calls, outputs, and verification.
10. Verifier checks the result. Recovery uses a known-good checkpoint or rollback plan where available.
11. Memory stores only data permitted by its scope and retention policy.

No worker, model, browser session, plugin, or UI component can call around the Governor or manufacture approval.

## 5. Service ownership

| Domain | Owns | Must not own |
|---|---|---|
| Identity | Human/service identities, sessions, credentials, memberships | Mission policy decisions |
| Authorization | Role and attribute evaluation, workspace boundaries | Agent planning |
| Governor | Policy, risk, autonomy, budgets, approval requirements | Direct tool execution |
| Mission service | Mission lifecycle, DAG, state transitions, idempotency | Credential storage |
| Agent registry/router | Worker manifests, capabilities, health, selection | Permission grants |
| Cognitive kernel | Planning, reasoning, model selection proposals | Authority or policy bypass |
| MCP gateway | Tool discovery, schema validation, scoped invocation | Independent authorization |
| Runtime | Leases, sandboxing, execution, timeouts, cancellation | Changing approved payloads |
| Evidence/audit | Append-only decision and execution records | Secret or unrestricted prompt retention |
| Memory/knowledge | Scoped retrieval, provenance, retention | Cross-tenant retrieval |
| Notifications | Email and operational notifications | Authorization or identity proof |

## 6. Security model

### Identity and tenant boundaries
- Use OIDC Authorization Code + PKCE for interactive users; validate issuer, audience, signature, expiry, nonce, and state.
- Use MFA through the identity provider and require step-up authentication for sensitive actions.
- Model organization, workspace, membership, role, and service identity explicitly.
- Resolve tenant/workspace scope from validated identity and database membership. Never trust a tenant ID supplied only in a request header or browser body.
- Enforce authorization in the API and again at the data boundary (PostgreSQL RLS when PostgreSQL is introduced).
- Keep the current owner bearer token as a local bootstrap/development mechanism only. Do not extend it into a shared multi-user credential.

### Approval and execution
- Approval binds to the exact canonical payload digest, action, resource, environment, workspace, permission scope, and expiry.
- Approval is single-use and consumed atomically.
- Any payload, target, scope, or environment change invalidates approval.
- Destructive database/infra operations, deploy/rollback, finance/live trading, credentials/auth/RLS, billing, legal/ownership, and repository deletion require explicit human approval and remain blocked until a separately reviewed policy enables them.
- Workers receive short-lived, least-privilege credentials scoped to one task. Never pass the owner token to workers.

### Secrets and data
- Secrets come from a secret manager or deployment environment, never source, frontend bundles, logs, or mission result payloads.
- Redact authorization headers, provider keys, SMTP passwords, and sensitive personal data from logs.
- Encrypt transport and sensitive persisted data. Define retention and deletion per data class.
- Keep SMTP delivery allowlisted. Email content is untrusted input and must not grant access.
- Apply request size limits, rate limits, CSRF protection where cookie sessions are used, secure headers, and strict CORS.

## 7. Data model (target)

Core entities:
- `User`, `ServiceIdentity`, `Organization`, `Workspace`, `Membership`, `Role`, `Permission`
- `AgentManifest`, `AgentVersion`, `AgentGroup`, `CapabilityGrant`
- `Mission`, `MissionStep`, `MissionDependency`, `ExecutionAttempt`, `Lease`
- `Policy`, `PolicyVersion`, `RiskAssessment`, `Approval`, `BudgetReservation`
- `Tool`, `ToolInvocation`, `CredentialReference`
- `EvidenceRecord`, `AuditEvent`, `VerificationResult`, `RecoveryAction`
- `MemoryRecord`, `KnowledgeDocument`, `Notification`

Every tenant-owned row carries a server-derived organization/workspace scope. Every state transition has an actor, timestamp, correlation ID, and audit event. Store credential references, not raw secrets.

## 8. Repository organization target

Preserve the current installation paths and compatibility while refactoring the platform into clear modules:

```text
apps/
  control-center/       # Next.js UI when frontend migration is approved
  api/                  # versioned API composition
  worker/               # isolated worker process
packages/
  contracts/            # API schemas and event contracts
  identity/             # identity and session integration
  authorization/        # RBAC/ABAC and workspace scope
  governance/           # Governor, risk, approvals, budgets
  missions/             # mission model, DAG, state machine
  agents/               # manifests, registry, groups, router
  cognitive/            # planner, model router, reasoning
  tools/                # MCP gateway and adapters
  evidence/             # audit, provenance, verification
  memory/               # scoped memory and knowledge
  notifications/        # email and delivery adapters
runtime/                 # compatibility entrypoint during migration
scripts/                 # OpenClaw/Hermes install and launch
config/                  # non-secret provider/model configuration
docs/                    # architecture, ADRs, operations, security
```

Do not create empty packages merely to imitate this tree. Extract a module when it has a stable contract, tests, and a clear owner. Keep the existing `runtime/` entrypoint working until its replacement is tested and migrated.

## 9. Technology direction

- API/control plane: FastAPI with typed request/response contracts.
- Web: Next.js Control Center; keep server-side authorization authoritative.
- Persistence: PostgreSQL as the system of record; migrations and tenant-aware constraints.
- Cache/leases/short-lived coordination: Redis, introduced only when multi-process execution requires it.
- Durable asynchronous work: transactional outbox plus a queue/worker model; select a broker based on measured workload.
- Secrets: managed secret store; environment variables only for local development.
- Runtime isolation: containers with non-root users, read-only filesystems where possible, resource limits, network egress policy, and per-mission workspaces.
- Observability: structured logs, traces, metrics, correlation IDs, and redaction.
- Deployment: immutable artifacts, separate dev/staging/prod environments, protected production approvals, and rollback.

The current standard-library server and SQLite store are retained as a working local baseline until the replacement has feature parity and migration tests.

## 10. Definition of done

A platform capability is complete only when:
- its contract and threat boundary are documented;
- authorization is enforced server-side and covered by negative tests;
- tenant/workspace isolation is tested where applicable;
- failure, timeout, retry, cancellation, and idempotency behavior is tested;
- audit/evidence records are produced and secrets are redacted;
- migration and rollback are defined;
- CI passes on the exact commit;
- staging verification is recorded before production deployment.

A successful code review badge is not a substitute for runtime tests. A merged PR is not proof of deployment.
