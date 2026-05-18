"""
council-ouroboros / learning.py
Drift detection + sigma-threshold reweighting.

Maintains a rolling z-score of each voter's pass-rate. If |z| > SIGMA,
emit a reweight signal. Persisted to Postgres `voter_history` table.
"""
from __future__ import annotations
import os, math, logging
from collections import deque
from dataclasses import dataclass, field

log = logging.getLogger("learning")

SIGMA = float(os.getenv("DRIFT_SIGMA_THRESHOLD", "2.0"))
WINDOW = int(os.getenv("LEARNING_WINDOW", "50"))

@dataclass
class VoterHistory:
    name: str
    pass_rate: deque = field(default_factory=lambda: deque(maxlen=WINDOW))

    def push(self, passed: bool) -> None:
        self.pass_rate.append(1.0 if passed else 0.0)

    def mean(self) -> float:
        return sum(self.pass_rate) / len(self.pass_rate) if self.pass_rate else 0.0

    def std(self) -> float:
        m = self.mean()
        if len(self.pass_rate) < 2: return 0.0
        var = sum((x - m) ** 2 for x in self.pass_rate) / (len(self.pass_rate) - 1)
        return math.sqrt(var)

    def zscore_last(self) -> float:
        if not self.pass_rate or self.std() == 0: return 0.0
        return (self.pass_rate[-1] - self.mean()) / self.std()

HISTORY: dict[str, VoterHistory] = {}

def observe(voter: str, passed: bool) -> float | None:
    h = HISTORY.setdefault(voter, VoterHistory(voter))
    h.push(passed)
    z = h.zscore_last()
    if abs(z) > SIGMA:
        log.warning("DRIFT detected voter=%s z=%.2f mean=%.2f", voter, z, h.mean())
        return z
    return None
