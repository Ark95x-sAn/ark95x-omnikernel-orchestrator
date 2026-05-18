# Council Ouroboros — Self-Operational Cooperative-Compute OS

**Status:** Initial scaffold (PR #1)
**Owner:** Ark95x-sAn
**Home:** `Ark95x-sAn/ark95x-omnikernel-orchestrator`
**Subsystem:** `council-ouroboros`
**License:** TBD (recommend dual: AGPL for core, commercial for hosted)

---

## Mission

A self-operational, self-adapting agentic OS built on a 9-voter LLM council + 7-worker execution pool + closed learning loop. Browser-driven prototypes get replaced by an async API-first architecture that scans **~9x faster** end-to-end by firing all voters in parallel via `asyncio.gather`.

## The Ouroboros Loop

```
TRIGGER → COUNCIL (9 voters, Bayesian-weighted) → ROUTER (AUTO/NOTIFY/GATED)
        → WORKERS (W0 supervisor + W1-W6) → OUTCOME CAPTURE
        → LEARNING (weight update + vector memory + drift detector)
        → RE-ROUTE BACK TO COUNCIL (synthesize next question from outcome)
        → loop
```

## Council Voters (9)

| Slot | Model | Role lens |
|------|-------|-----------|
| C1 | ChatGPT (OpenAI) | RE-GTM + automation architect |
| C2 | Claude (Anthropic) | **Auditor** — veto holder on irreversible |
| C3 | Perplexity | Infra ROI analyst |
| C4 | Gemini (Google) | Automation architect |
| C5 | Ollama (local) | Cheap parallel votes (Llama/Qwen/Mistral) |
| C6 | Grok (x.ai) | Devil's-advocate / tie-break |
| C7 | DeepSeek | Heavy reasoner |
| C8 | Le Chat (Mistral) | EU low-latency lens |
| C9 | Qwen (DashScope) | Long-context auditor |

## Workers (7)

| Slot | Module | Purpose |
|------|--------|---------|
| W0 | supervisor | heartbeat + restart + load-balance |
| W1 | ingest | Iowa county foreclosure docket scraper |
| W2 | orchestration | n8n REST + LangGraph runner |
| W3 | docs | Google Docs/Sheets writer |
| W4 | crm | attorney outreach (**GATED**) |
| W5 | revenue | Stripe SDK (**GATED** for charges) |
| W6 | monitor | Prometheus + log tail |

## Gate Policy

- **AUTO**   : logs, ledger writes, scrapes, internal votes, weight updates, n8n reruns
- **NOTIFY** : drafts (docs/emails/pages), outreach prep, template gen
- **GATED**  : Stripe charges, email send, social post, repo push, domain buy, account create, delete, permission change

## Self-Operational Cron

- `5m`     — W6 health check → emergency council on anomaly
- `1h`     — W1 county-docket scrape → new leads
- `6h`     — Council re-vote on priorities
- `daily`  — Cycle review on yesterday's metrics
- `weekly` — Strategic re-vote (product/pricing/outreach drift)

## Epic Upgrades (baked in)

- **Self-healing** — W0 restarts crashed workers, redistributes Bayesian weight
- **Self-tuning** — weights shift per voter per domain
- **Self-questioning** — outcome packet synthesizes the next council prompt
- **Self-archiving** — every decision + outcome → Chroma vector store → RAG-grounds future votes
- **Self-defending** — drift detector (KL-divergence) catches degradation or prompt injection
- **Self-throttling** — cost governor caps daily spend; auto-fallback to Ollama at 80%
- **Human-sovereign** — every irreversible/financial action ALWAYS routes through GATED

## Deploy Phases

| Phase | Mission | Gate |
|-------|---------|------|
| P0 | Throne confirmations + entity decisions | GATED |
| P1 | Build the depot (this PR) | GATED |
| P2 | `docker compose up` locally (WSL2) | AUTO |
| P3 | First live council cycle on real Iowa filing | AUTO |
| P4 | First live worker chain (W1→W2→Ollama→W3→HITL) | AUTO |
| P5 | First revenue event (Stripe sandbox → real charge) | GATED |
| P6 | 7-day soak — weights stabilize | AUTO |
| P7 | Hand the wheel — fully self-operational | terminal |

## File Tree (planned full PR)

```
/council/
  voters/
    base_voter.py
    chatgpt_voter.py
    claude_voter.py
    perplexity_voter.py
    gemini_voter.py
    ollama_voter.py
    grok_voter.py
    deepseek_voter.py
    lechat_voter.py
    qwen_voter.py
  aggregator.py
  weights.json
/router/
  router.py
  gate_policy.py
/workers/
  w0_supervisor.py
  w1_ingest.py
  w2_orchestration.py
  w3_docs.py
  w4_crm.py
  w5_revenue.py
  w6_monitor.py
/learning/
  outcome_capture.py
  weight_updater.py
  memory.py
  drift_detector.py
/loop/
  ouroboros.py
  scheduler.py
  main.py
docker-compose.yml
.env.example
DEPLOYMENT.md
```

## Safety

- `.env.example` only — no real keys committed, ever
- Stripe + email + outreach modules ship **disabled by default** behind `GATED=true`
- Branch protection: signed commits, no force-push, owner-only merge
- All GATED actions require explicit per-action human approval via SMS/email link

## 9x Scanner

Current browser-driven flow: ~9 sequential tab interactions per cycle.
This subsystem: `asyncio.gather` across all 9 voters → ~5-8s end-to-end full cycle.

---

**This file is the anchor commit for PR #1. Remaining 15 files follow once anchor is verified green.**
