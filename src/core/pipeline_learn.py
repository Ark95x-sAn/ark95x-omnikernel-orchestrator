"""
Data pipeline learning layer.

PipelineLearner attaches to PipelineManager and observes every stage
execution. From those observations it builds per-stage profiles and
surfaces actionable recommendations:

  - Timeout auto-tune  (p95 * safety_factor replaces the static default)
  - Failure-rate drift (z-score alert when a stage starts failing unusually)
  - Duration spike     (z-score alert when a single run is an outlier)
  - Bottleneck rank    (stages sorted by mean duration so the slowest is obvious)
"""
from __future__ import annotations

import math
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger("ark95x.pipeline.learn")

# ── tunables ────────────────────────────────────────────────────────────────
WINDOW: int = 100          # max observations kept per stage
ANOMALY_SIGMA: float = 2.5  # z-score threshold for spike / drift alerts
TIMEOUT_SAFETY: float = 1.5  # p95 * this factor → recommended timeout
MIN_SAMPLES: int = 5        # skip inference until we have this many runs


# ── per-stage rolling stats ──────────────────────────────────────────────────
@dataclass
class StageProfile:
    name: str
    durations: deque = field(default_factory=lambda: deque(maxlen=WINDOW))
    outcomes: deque = field(default_factory=lambda: deque(maxlen=WINDOW))  # 1=ok 0=fail
    retries: deque = field(default_factory=lambda: deque(maxlen=WINDOW))
    last_seen: float = 0.0

    # ── primitive stats ──────────────────────────────────────────────────────
    def _mean(self, buf: deque) -> float:
        return sum(buf) / len(buf) if buf else 0.0

    def _std(self, buf: deque) -> float:
        if len(buf) < 2:
            return 0.0
        m = self._mean(buf)
        var = sum((x - m) ** 2 for x in buf) / (len(buf) - 1)
        return math.sqrt(var)

    def _percentile(self, buf: deque, p: float) -> float:
        if not buf:
            return 0.0
        s = sorted(buf)
        idx = (p / 100) * (len(s) - 1)
        lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
        return s[lo] + (s[hi] - s[lo]) * (idx - lo)

    # ── derived metrics ──────────────────────────────────────────────────────
    def mean_duration(self) -> float:
        return self._mean(self.durations)

    def p95_duration(self) -> float:
        return self._percentile(self.durations, 95)

    def success_rate(self) -> float:
        return self._mean(self.outcomes)

    def zscore_duration(self, duration: float) -> float:
        std = self._std(self.durations)
        if std == 0 or len(self.durations) < MIN_SAMPLES:
            return 0.0
        return (duration - self._mean(self.durations)) / std

    def zscore_outcome(self) -> float:
        """Z-score of the most-recent outcome vs the rolling pass-rate."""
        std = self._std(self.outcomes)
        if std == 0 or len(self.outcomes) < MIN_SAMPLES:
            return 0.0
        return (self.outcomes[-1] - self._mean(self.outcomes)) / std

    def recommended_timeout(self) -> Optional[float]:
        if len(self.durations) < MIN_SAMPLES:
            return None
        return self.p95_duration() * TIMEOUT_SAFETY

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "samples": len(self.durations),
            "mean_duration_s": round(self.mean_duration(), 3),
            "p95_duration_s": round(self.p95_duration(), 3),
            "success_rate": round(self.success_rate(), 3),
            "recommended_timeout_s": (
                round(self.recommended_timeout(), 1)
                if self.recommended_timeout() is not None else None
            ),
        }


# ── learner ──────────────────────────────────────────────────────────────────
class PipelineLearner:
    """
    Observe pipeline stage outcomes and expose learned insights.

    Usage (attach to PipelineManager):
        learner = PipelineLearner()
        manager = PipelineManager(config, learner=learner)

    After runs:
        recs = learner.recommendations()
        profile = learner.stage("ingest")
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, StageProfile] = {}
        self._alerts: List[dict] = []

    def _profile(self, stage_name: str) -> StageProfile:
        return self._profiles.setdefault(stage_name, StageProfile(name=stage_name))

    def observe(
        self,
        stage_name: str,
        duration: float,
        success: bool,
        retries: int = 0,
    ) -> None:
        """Record one stage execution. Called by PipelineManager after each stage."""
        p = self._profile(stage_name)
        p.last_seen = time.time()

        # append BEFORE computing z-scores so the new value is included
        p.durations.append(duration)
        p.outcomes.append(1.0 if success else 0.0)
        p.retries.append(float(retries))

        # ── anomaly detection ───────────────────────────────────────────────
        z_dur = p.zscore_duration(duration)
        if abs(z_dur) > ANOMALY_SIGMA:
            self._emit_alert(
                kind="duration_spike",
                stage=stage_name,
                detail=f"duration={duration:.2f}s z={z_dur:+.2f} (mean={p.mean_duration():.2f}s)",
            )

        z_out = p.zscore_outcome()
        if not success and abs(z_out) > ANOMALY_SIGMA:
            self._emit_alert(
                kind="failure_rate_drift",
                stage=stage_name,
                detail=(
                    f"failure z={z_out:+.2f} "
                    f"success_rate={p.success_rate():.2%}"
                ),
            )

    def _emit_alert(self, kind: str, stage: str, detail: str) -> None:
        alert = {"ts": time.time(), "kind": kind, "stage": stage, "detail": detail}
        self._alerts.append(alert)
        log.warning("[PipelineLearner] %s stage=%s %s", kind, stage, detail)

    # ── public API ────────────────────────────────────────────────────────────
    def stage(self, name: str) -> Optional[StageProfile]:
        return self._profiles.get(name)

    def all_profiles(self) -> Dict[str, dict]:
        return {name: p.snapshot() for name, p in self._profiles.items()}

    def bottlenecks(self, top: int = 5) -> List[dict]:
        """Stages ranked by mean duration (slowest first)."""
        ranked = sorted(
            self._profiles.values(),
            key=lambda p: p.mean_duration(),
            reverse=True,
        )
        return [p.snapshot() for p in ranked[:top]]

    def recommendations(self) -> List[dict]:
        """
        Return actionable tuning recommendations, one entry per stage that has
        enough data for a confident suggestion.
        """
        recs = []
        for p in self._profiles.values():
            if len(p.durations) < MIN_SAMPLES:
                continue

            rec_timeout = p.recommended_timeout()
            if rec_timeout is not None:
                recs.append({
                    "stage": p.name,
                    "type": "timeout",
                    "recommended_timeout_s": round(rec_timeout, 1),
                    "basis": f"p95={p.p95_duration():.2f}s × safety={TIMEOUT_SAFETY}",
                })

            if p.success_rate() < 0.9:
                recs.append({
                    "stage": p.name,
                    "type": "reliability",
                    "success_rate": round(p.success_rate(), 3),
                    "message": (
                        f"Success rate {p.success_rate():.1%} is below 90%. "
                        "Consider adding retry logic or investigating root cause."
                    ),
                })

        return recs

    def recent_alerts(self, limit: int = 20) -> List[dict]:
        return list(reversed(self._alerts[-limit:]))

    def summary(self) -> dict:
        return {
            "tracked_stages": len(self._profiles),
            "total_alerts": len(self._alerts),
            "bottlenecks": self.bottlenecks(3),
            "recommendations": self.recommendations(),
        }
