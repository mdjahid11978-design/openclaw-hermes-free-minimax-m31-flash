# Free MiniMax M3.1 Flash for OpenClaw + Hermes Agent

Run **OpenClaw** and **Hermes Agent** on `MiniMax-M3.1-Flash` with **no per-token billing**.

[![Built by Jahid](https://img.shields.io/badge/Built%20by-Jahid-a855f7?style=flat-square&logo=github)](https://github.com/mdjahid11978-design)

> The obvious free route is **gone**. OpenRouter retired `minimax/minimax-m3.1-flash:free` on
> **2026-10-22** — a live check of `/api/v1/models` now returns only the paid slug. This repo
> rebuilds the setup around the one route that is still genuinely free.

---

## Why not OpenRouter's `:free` slug?

| Route | Status | Cost | Notes |
|---|---|---|---|
| `openrouter/minimax/minimax-m3.1-flash:free` | ❌ Retired 2026-10-22 | — | No `:free` variant exists any more |
| `openrouter/minimax/minimax-m3.1-flash` | ✅ Live | $0.15 / $0.60 per 1M | Pays per token |
| `minimax/MiniMax-M3.1-Flash` (API key) | ✅ Live | $0.15 / $0.60 per 1M | Pay-as-you-go on MiniMax |
| `minimax-portal/MiniMax-M3.1-Flash` (OAuth) | ✅ Live | Needs M Plan | Subscription isn't free |
| **`nvidia/minimaxai/minimax-m3.1-flash`** | ✅ **Live, free** | **$0** | Rate limited, no per-token billing |

**Same weights, same context, same effort ladder** — only the billing endpoint changes:

- 23B active / 428B total MoE, **1M token context**
- Always-on reasoning: `low → medium → high → xhigh → max`
- Free tier: ~40 RPM shared across the catalog, no credit card required

---

## Quick start

```bash
# 1. Get a free NVIDIA key (no credit card)
#    https://build.nvidia.com/settings/api-keys

# 2. Install everything
./scripts/setup.sh

# 3. Export the key
export NVIDIA_API_KEY=nvapi-YOUR_KEY_HERE

# 4. Run either agent
./scripts/run-openclaw.sh          # OpenClaw gateway + TUI
./scripts/run-hermes.sh             # Hermes Agent
./scripts/run-hermes.sh -z "hi"     # Hermes one-shot
```

Both launchers **self-heal**: if the Node runtime, the OpenClaw package, or the state directory
goes missing, they rebuild it and re-pin the model before starting.

---

## What gets configured

### OpenClaw — `~/.home/openclaw-state/openclaw.json`

```json5
{
  agents: {
    defaults: {
      model: {
        primary: "nvidia/minimaxai/minimax-m3.1-flash",
        fallbacks: []                    // ← intentionally empty
      },
      utilityModel: "nvidia/minimaxai/minimax-m3.1-flash",
      models: {
        "nvidia/minimaxai/minimax-m3.1-flash": { alias: "minimax" }
      }
    }
  },
  models: {
    providers: {
      nvidia: {
        baseUrl: "https://integrate.api.nvidia.com/v1",
        api: "openai-completions",
        models: [
          {
            id: "minimaxai/minimax-m3.1-flash",
            reasoning: true,
            input: ["text", "image"],
            contextWindow: 1000000,
            maxTokens: 131072
          }
        ]
      }
    }
  }
}
```

### Hermes Agent — `~/.hermes/config.yaml`

```yaml
model:
  default: "minimaxai/minimax-m3.1-flash"
  provider: "nvidia"
  base_url: "https://integrate.api.nvidia.com/v1"
  context_length: 1000000

agent:
  reasoning_effort: "medium"
```

---

## Why `fallbacks: []` matters

A fallback to any paid provider would **silently spend real money** the moment the free tier
rate-limits you. With an empty fallback list, OpenClaw surfaces the error instead of quietly
switching to a billable route.

You can confirm this in the logs:

```
[model-fallback/decision] model fallback decision: decision=candidate_failed
  requested=nvidia/minimaxai/minimax-m3.1-flash reason=auth next=none
```

---

## Keeping the key out of the config

Neither tool writes the secret into its config file:

- **OpenClaw** maps `NVIDIA_API_KEY` → the `nvidia` provider automatically. Verify with:
  ```bash
  openclaw models status --probe
  # → nvidia:default=ref(env:NVIDIA_API_KEY) | source=env: NVIDIA_API_KEY
  ```
- **Hermes** reads `~/.hermes/.env`.

---

## Troubleshooting

### `unsafe workspace file "IDENTITY.md"`

OpenClaw publishes workspace bootstrap files with an atomic write that uses hardlinks. On an
**NFS-backed** mount the fs-safe layer rejects hardlinked paths, so onboarding aborts.

**Fix:** pre-seed the workspace templates before onboarding — `scripts/setup.sh` already does this:

```bash
TPL=~/.home/tools/node24/lib/node_modules/openclaw/docs/reference/templates
WS=~/.home/openclaw-state/workspace
mkdir -p "$WS"
for f in AGENTS.md SOUL.md IDENTITY.md USER.md BOOTSTRAP.md; do
  cp -n "$TPL/$f" "$WS/$f"
done
```

OpenClaw then publishes them via the plain (non-atomic) path and onboarding succeeds.

### OpenClaw won't install — "requires Node >=24.22.1"

```bash
npm install -g openclaw@latest --prefix ~/.home/tools/node24 \
  --allow-scripts=@google/genai,esbuild,koffi,protobufjs,openclaw
```

The `--allow-scripts` flag is required or the bundled-plugin postinstall is skipped.

### Hermes install fails resolving `setuptools`

The environment pins `UV_INDEX_URL` to an unreachable mirror. Override it:

```bash
export UV_INDEX_URL=https://pypi.org/simple
export UV_DEFAULT_INDEX=https://pypi.org/simple
```

Hermes' installer also supports running stages individually:

```bash
bash install.sh --stage venv
bash install.sh --stage python-deps
bash install.sh --stage config
bash install.sh --stage products
bash install.sh --stage complete
```

### `Unknown model: minimax/MiniMax-M3`

The provider isn't configured. Check `openclaw models list`, and confirm the model id is
**case-sensitive**: `minimaxai/minimax-m3.1-flash` on the NVIDIA route.

### HTTP 403 on every request

The key is wrong or expired. A 403 with `{"status":403,"title":"Forbidden","detail":"Authorization failed"}`
means the request path is correct and only the credential is missing.

### HTTP 429

Rate limit, not a billing problem. The free tier allows ~40 RPM shared across the whole
catalog. Wait, or switch to a paid route.

---

## Verifying the install

Both tools were driven with a real agent turn using a placeholder key. A **403** is the correct
result — it proves the whole request path works and only the key is missing:

```
# OpenClaw
[provider-transport-fetch] response provider=nvidia api=openai-completions
  model=minimaxai/minimax-m3.1-flash status=403

# Hermes
NVIDIA NIM rejected your API key, so the model can't be reached.
Provider said: HTTP 403: {"status":403,"title":"Forbidden","detail":"Authorization failed"}
```

With a real key the same commands return normal completions.

---

## Repo layout

```
.
├── scripts/
│   ├── setup.sh              # one-shot installer for both agents
│   ├── run-openclaw.sh       # OpenClaw launcher (self-healing)
│   └── run-hermes.sh         # Hermes launcher
├── config/
│   └── openclaw-m31-flash.patch.json5   # model pin, applied on every launch
├── docs/
│   └── index.html            # full visual setup report
├── NOTICE.md                 # third-party model + endpoint terms
└── LICENSE                   # MIT (this repo's code only)
```

---

## Terms

NVIDIA's hosted catalog is governed by the **NVIDIA API Trial Terms of Service** and the
**NVIDIA Software and Model Evaluation License** — trial, evaluation, or academic prototyping.
The base model is under the **MiniMax Community License** (commercial use allowed with
"Built with MiniMax M3.1-Flash" attribution and a one-time notice to MiniMax).

For production or business-critical workloads, use a paid route.

---

## Credits

**Built by [Jahid](https://github.com/mdjahid11978-design)** — AI Agent Developer & Full Stack
Engineer building the future of automation with OpenClaw, Web3, and modern web technologies.

See [NOTICE.md](NOTICE.md) for the model and endpoint terms.

| | |
|---|---|
| OpenClaw | 2026.10.9 |
| Hermes Agent | v0.22.5 |
| Node.js | v24.22.1 |
| Python | 3.14.9 |
| Model | MiniMax-M3.1-Flash · 1M ctx |
| Endpoint | `integrate.api.nvidia.com/v1` |

## JAHIDS.AI Agent Runtime v0.1

This repository now includes an optional governed mission API for NVIDIA NIM, OpenClaw, and Hermes. It is a separate integration layer; the original setup and launch scripts remain unchanged.

- Runtime source, API lifecycle, safety defaults, and run instructions: [runtime/README.md](runtime/README.md)
- Local API defaults to loopback and observe-only autonomy.
- Missions require an explicit approval step; high-impact categories are blocked.
- Docker Compose keeps the service bound to localhost and persists SQLite state in a named volume.
- This is an early integration runtime, not the full JAHIDS.AI Control Plane or production platform.
