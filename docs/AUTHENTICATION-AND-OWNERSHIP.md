# JAHIDS.AI Authentication and Ownership

## Current repository ownership

The GitHub repository is `mdjahid11978-design/openclaw-hermes-free-minimax-m31-flash`. The connected GitHub identity has administrator access. Source files cannot change repository ownership or visibility.

**Important:** repository visibility was reported as `public` during the 2026-11-01 inspection. Anyone can read public source. To restrict it, the account owner must open **Repository → Settings → General → Danger Zone → Change repository visibility → Make private**. Then review **Settings → Collaborators** and **Settings → Applications** to remove any access that should not remain. A private repository is still accessible to collaborators and installed apps that retain permission.

## Authenticate to GitHub from your own workstation

Use GitHub's official browser-based CLI login or SSH authentication. Do not put a personal access token in a repository file, script, Docker image, or shared environment file.

GitHub CLI:

```bash
gh auth login --hostname github.com --git-protocol ssh --web
gh auth status
gh repo view mdjahid11978-design/openclaw-hermes-free-minimax-m31-flash
```

For Git over SSH, add your public SSH key to your GitHub account and verify with:

```bash
ssh -T git@github.com
```

The GitHub account that owns this repository is `mdjahid11978-design`. The connected identity inspected for this change has administrator permission. Do not share account passwords, SSH private keys, recovery codes, or personal access tokens.

## Keep repository changes owner-controlled

After changing the repository to private:
- Review **Settings → Collaborators** and remove anyone who should not retain access.
- Review **Settings → Applications → Installed GitHub Apps** and revoke installations that do not need repository access.
- Protect `main`: require pull requests, require the validation workflow to pass, block force pushes and branch deletion, and restrict direct pushes where GitHub plan/settings allow.
- Keep Actions permissions read-only by default. Grant a workflow extra permissions only when a specific job needs them.
- Keep the owner as the required code owner. The added CODEOWNERS file requests review from `@mdjahid11978-design`; branch protection is still needed to enforce review.

## Runtime owner authentication

The runtime uses a single owner-held bearer secret, not GitHub OAuth and not an application username/password database.

1. Generate a secret on the host:
   ```bash
   python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```
2. Put the generated value in `runtime/.env` as `JAHIDS_API_TOKEN`. Set file permissions to `0600`.
3. Start the runtime. It refuses to start with a missing, short, or placeholder token.
4. Send the secret in the `Authorization: Bearer …` header for all `/v1/missions` endpoints.
5. Rotate it by replacing the value and restarting the service.

The API does not offer a route to create, reset, or retrieve owner tokens. The health endpoint is public but reveals only service liveness. All mission data and mutation routes require the owner secret.

## Provider authentication

`NVIDIA_API_KEY` is separate from `JAHIDS_API_TOKEN`. It authenticates requests from the NVIDIA adapter to NVIDIA NIM. Never reuse the owner API token as a provider key. OpenClaw and Hermes keep their own provider credentials in their local runtime environments/configuration.

## What this implementation does not claim

- It does not authenticate GitHub users to the runtime.
- It does not provide OIDC, OAuth login, SSO, multi-user RBAC, tenant isolation, or user provisioning.
- It does not secure a public network endpoint by itself. Keep the service on loopback; use a trusted TLS reverse proxy and a real identity provider before remote access.
- A private GitHub repository does not make the deployed runtime private automatically.

## GitHub Actions

The validation workflow uses the repository-scoped `GITHUB_TOKEN` with read-only `contents` permission. Do not add personal access tokens or provider API keys to workflow YAML. If a future job needs write access, grant only the specific permission required for that job.
