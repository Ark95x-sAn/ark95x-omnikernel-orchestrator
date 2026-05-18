# Council-Ouroboros

Self-operating, multi-LLM, multi-worker automation kernel for the ARK95X omnikernel orchestrator. Selected by 9-voter council (majority C — Litigation/Foreclosure Doc-Prep, Iowa-first) on the feat/council-ouroboros branch.

## Architecture

- **Router (`router.py`)** — hybrid api/browser dispatch. Modes: `api-only`, `browser-only`, `hybrid`.
- **Council (`council.py`)** — 9 voters: openai, anthropic, perplexity, gemini, mistral, deepseek, qwen, xai, ollama. Quorum 5. Tie-breaker: anthropic.
- **Workers (W0–W6)**
  - W0 scanner — Iowa county foreclosure feeds (Winnebago, Hancock, Cerro Gordo, Wright, Franklin)
  - W1 drafter — doc-prep templates (notice, response, motion shells)
  - W2 auditor — unauthorized-practice-of-law guardrails + citation check
  - W3 filer — GATED submission (never auto-files)
  - W4 collector — GATED Stripe charge (never auto-charges)
  - W5 monitor — prometheus + grafana + twilio alerts
  - W6 learner — drift-sigma weight updates into chroma + postgres
- **Loop (`loop.py`)** — cycle every `CYCLE_INTERVAL_SEC` (default 300s). Ouroboros: each cycle feeds W6 → council weights.
- **Learning (`learning.py`)** — sigma threshold default 2.0. Updates voter weights at rate 0.05.

## Gating (SAFE defaults)

All irreversible / external-spend / external-send actions are GATED behind `.env` flags, default `false`:

| Flag | Action gated |
|---|---|
| `GATED_STRIPE_CHARGE` | W4 collector charges |
| `GATED_EMAIL_SEND` | SMTP outbound |
| `GATED_FILING_SUBMIT` | W3 court filings |
| `GATED_AUTO_MERGE` | PR auto-merge |

Gated actions emit a Twilio SMS via `ALERT_SMS_NUMBER` and wait for human ack.

## Legal safety

This system **does not practice law**. W2 auditor enforces:
- No legal advice rendered to end users.
- All output marked "document preparation only — review by licensed attorney required."
- Iowa-specific templates reviewed against current rules of civil procedure.

## Deployment

See `DEPLOYMENT.md`. TL;DR:
```bash
cp .env.example .env   # fill keys
docker-compose up -d   # chroma, postgres, prometheus, grafana, ollama
python loop.py         # start ouroboros cycle
```

## Status

- PR #1 — anchor (merged)
- PR #4 — this build (in progress)
- Voters online: 6/9 (Grok, DeepSeek, Stripe-onboarding pending user sign-in — never auto-created)
