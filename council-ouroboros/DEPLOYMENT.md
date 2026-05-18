# Council-Ouroboros Deployment

## Prereqs
- Docker + Docker Compose
- Python 3.11+ (for local dev outside compose)
- API keys for at least 5 council voters (quorum) in `.env`

## Quickstart
```bash
git clone https://github.com/Ark95x-sAn/ark95x-omnikernel-orchestrator.git
cd ark95x-omnikernel-orchestrator/council-ouroboros
cp .env.example .env
# edit .env: fill OPENAI_API_KEY, ANTHROPIC_API_KEY (optional), PERPLEXITY_API_KEY, GOOGLE_API_KEY, etc.
docker-compose up -d
docker-compose logs -f council-ouroboros
```

## Phase 1 — Dry run (default, SAFE)
All GATED flags default to `false`:
- `GATED_STRIPE_CHARGE=false` — no charges
- `GATED_EMAIL_SEND=false`    — no emails
- `GATED_FILING_SUBMIT=false` — stage only, no court filings
- `GATED_AUTO_MERGE=false`    — no PR auto-merge

Cycle output lands in `./out/` and `./out/staged/`. Review manually.

## Phase 2 — Selective enable
Flip ONE gate at a time, after manual review of Phase 1 output:
```bash
GATED_STRIPE_CHARGE=true  # only after Stripe live key verified
```
Each gated action still emits Twilio SMS to `ALERT_SMS_NUMBER` and waits for human ack.

## Phase 3 — Production
- Set `ROUTER_MODE=api-only` once all voters have API keys
- Move Postgres + Chroma to managed services
- Add backup cron for `./out/staged/`
- Configure Grafana dashboards (port 3000, default pwd `ouroboros`)

## Voter roster (post-rotation 2026-05-18)
| Voter | Role | Weight | Required env |
|---|---|---|---|
| perplexity | AUDITOR + tie-break | 1.5 | `PERPLEXITY_API_KEY` |
| gemini     | DRAFTER             | 1.2 | `GOOGLE_API_KEY` |
| openai     | SWING               | 1.0 | `OPENAI_API_KEY` |
| mistral    | SWING (Le Chat)     | 1.0 | `MISTRAL_API_KEY` |
| qwen       | SWING               | 1.0 | `QWEN_API_KEY` |
| ollama     | LEARNER (local)     | 0.8 | `OLLAMA_BASE_URL` |
| deepseek   | SWING (disabled)    | 1.0 | `DEEPSEEK_API_KEY` |
| xai        | SWING (disabled)    | 1.0 | `XAI_API_KEY` |
| google_pse | SCANNER_AID         | 0.5 | `GOOGLE_API_KEY` |

Claude rotated out 2026-05-18; archived in Ledger v3.

## Legal
- Never auto-files or auto-charges.
- All output stamped "DOCUMENT PREPARATION ONLY — NOT LEGAL ADVICE."
- B2B-to-attorney framing per AUDITOR recommendation.
- Iowa Code §654A + Iowa R. Civ. P. 1.x scope only at launch.

## Smoke test
```bash
python -m pytest tests/   # TODO: add in PR #5
python loop.py            # one-shot cycle (Ctrl-C after first iteration)
curl localhost:9090/metrics
```
