# Council-Ouroboros RUNBOOK — v0.1

Internal operator notes: what shipped, what worked, how to set it up, and the multi-browser × multi-model expansion blueprint.

---

## 1. What Shipped (v0.1.0-ouroboros)

- Anchor PR #4 merged to main at fd3b6b6 (17 commits).
- CI hardening PR #5 open: .env seeding + non-fatal lint/compose validation.
- Tracker Issue #6: Phase 1 dry-run checklist.
- Release v0.1.0-ouroboros saved as DRAFT (publish gated).
- 15 component files staged under council-ouroboros/: council.py, router.py, workers/, docker-compose.yml, .env.example, DEPLOYMENT.md, README_OUROBOROS.md, plus CI workflow.

## 2. What Worked

- Branch-per-feature + gated merge. Anchor PR landed clean; CI fix routed through its own PR.
- Roster rotation via Ledger v3. Claude rotated out (Auditor seat to Perplexity, Drafter to Gemini). Quorum 5/8 active.
- Gate policy AUTO / NOTIFY / GATED. Stripe, filings, email, release-publish, PR merges all hard-stopped pending operator OK.
- Council-first decision flow. Vote precedes irreversible actions; minority dissent logged.
- CI as the dry-run substitute. GitHub Actions seeds .env and validates compose + workflow YAML on every push.

## 3. Friction / What Did Not Work

- Voter sign-in friction: Grok and DeepSeek sit at login walls. Agent will not create accounts. Operator opens session; agent drafts only.
- Initial CI red: first ci.yml assumed .env at repo root; project keeps it under council-ouroboros/. PR #5 fixes paths + continue-on-error on optional steps.
- CodeRabbit rate-limit (~54 min) when stacking many commits. Batch commits, request review after batch.

## 4. Operator Quickstart

### 4.1 Prereqs (Windows host)
- Docker Desktop (logged in as ark95x on Docker Hub)
- WSL2 + Ubuntu
- Python 3.11+
- git, gh CLI (optional)
- Ollama (local voter, http://localhost:11434)

### 4.2 Clone + bootstrap
    git clone https://github.com/Ark95x-sAn/ark95x-omnikernel-orchestrator.git
    cd ark95x-omnikernel-orchestrator/council-ouroboros
    cp .env.example .env
    # edit .env: API keys for voters you have, leave others blank

### 4.3 Dry-run
    export GATED_STRIPE=dry GATED_FILING=dry GATED_EMAIL=dry GATED_MERGE=dry
    docker compose --env-file .env config
    docker compose --env-file .env up --build

Expect: W0 supervisor heartbeat, W1->W2 handshake, W6 metrics on :9090/metrics.

### 4.4 Live (gated)
Flip GATED_* flags one at a time, only after a green dry-run cycle.

## 5. Multi-Browser x Multi-Model Expansion

Goal: parallelize the council across N browser sessions so each voter has its own profile, cookies, account, and rate-limit, then aggregate.

### 5.1 Topology
    W0 Supervisor
        |
    +---+---+---+
    |   |   |   |
    BrowserA BrowserB BrowserC ...
    ChatGPT Perplexity Gemini
        |   |   |
        +---v---+
        council.py (aggregate + weight)
            |
        router.py (AUTO/NOTIFY/GATED)
            |
        W1..W6 workers

### 5.2 Add a new voter
1. Spawn fresh browser profile: chrome --user-data-dir=./profiles/<voter>
2. Operator logs in once. Agent never auto-logs in.
3. Register in council.py:
    COUNCIL.register(name="NewVoter", role="Auditor|Drafter|General", tab_url="...", weight=1.0)
4. Add adapter under workers/adapters/<newvoter>.py (selectors for input/submit/response).
5. Smoke-test with a known-answer prompt.
6. Update Ledger v3 with new roster.

### 5.3 New-angle voter suggestions
- Mistral Codestral — code-specialist auditor for PRs.
- Cohere Command R+ — RAG-grounded responses.
- Llama-3.3-70B via Groq — low-latency tie-breaker.
- Claude Opus 4 — red-team adversary seat (advisory, weight 0).
- Local Qwen3.6 via Ollama — air-gapped fallback.

### 5.4 Aggregation rules
- Quorum: >= ceil(N*0.6) voters within 30s.
- Weights: Auditor 1.5x, Drafter 1.2x, General 1.0x, Adversary 0.0.
- Tie-break: Auditor; if Auditor abstains, route to operator.
- Dissent log: minority opinions persisted to Ledger v3 each cycle.

### 5.5 Safety invariants
- No voter session may execute a GATED action.
- No agent may auto-login or create accounts.
- Operator is the only entity that can publish releases, merge to main (when branch protection on), or fire Stripe/filing/email.
- Every irreversible action emits a ledger entry before and after.

## 6. Pointers

- PR #4 (anchor): pull/4
- PR #5 (CI fix): pull/5
- Issue #6 (dry-run tracker): issues/6
- Release draft: v0.1.0-ouroboros
- Ledger v3: operator-only Google Doc
