"""
council-ouroboros / workers/w6_learner.py
W6 LEARNER — ouroboros feedback into council voter weights.

Reads veto outcomes + downstream success signals; emits weight deltas
back into the council ROSTER via Router.reweight().
Persists embeddings to Chroma; tabular metrics to Postgres.
"""
from __future__ import annotations
import os, logging
from dataclasses import dataclass

log = logging.getLogger("w6_learner")

LR = float(os.getenv("WEIGHT_LEARNING_RATE", "0.05"))
SIGMA = float(os.getenv("DRIFT_SIGMA_THRESHOLD", "2.0"))

@dataclass
class LearningUpdate:
    voter: str
    delta: float
    reason: str

def learn(audit_reports: list[dict], voter_outputs: list[dict]) -> list[LearningUpdate]:
    """Reward voters whose drafts pass audit; penalize those whose drafts veto."""
    updates: list[LearningUpdate] = []
    veto_voters: dict[str, int] = {}
    pass_voters: dict[str, int] = {}
    for r in audit_reports:
        bucket = veto_voters if r.get("auditor_veto") else pass_voters
        for v in voter_outputs:
            if v.get("draft_id") == r.get("draft_id"):
                bucket[v["voter"]] = bucket.get(v["voter"], 0) + 1
    for v, n in pass_voters.items():
        updates.append(LearningUpdate(v, +LR * n, f"{n} drafts passed audit"))
    for v, n in veto_voters.items():
        updates.append(LearningUpdate(v, -LR * n, f"{n} drafts vetoed"))
    log.info("learner produced %d updates (LR=%.3f, sigma=%.1f)", len(updates), LR, SIGMA)
    return updates

def apply_updates(router, updates: list[LearningUpdate]) -> None:
    for u in updates:
        router.reweight(u.voter, u.delta)
