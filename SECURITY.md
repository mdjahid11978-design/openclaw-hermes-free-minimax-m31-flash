# Security Policy — JAHIDS.AI

## Supported scope

This repository installs and configures OpenClaw and Hermes Agent and connects them
to NVIDIA NIM. Treat local agent execution, model credentials, channel tokens,
and workspace files as sensitive.

## Report a vulnerability

Please do not publish secrets or exploitable details in a public issue. Contact
the repository owner privately through GitHub's security advisory feature.

## Credential handling

- Keep `NVIDIA_API_KEY` in the process environment or a local secret manager.
- Never commit `.env`, provider keys, bot tokens, or runtime config containing credentials.
- Rotate a credential immediately if it appears in logs, commits, screenshots, or issues.
- Review third-party scripts before running them; pin dependencies for production.
- The free NVIDIA endpoint is rate-limited and subject to NVIDIA's trial terms.
  Do not treat it as a production SLA.
