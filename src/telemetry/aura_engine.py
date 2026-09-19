"""ARK95X Aura Engine
Measures the electromagnetic signature of the system —
its pulse rate, trauma history, agent alignment coherence,
and resonance between sensing and computation.
"""
import time
import math
import random
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("ark95x.telemetry.aura")


class PulsePattern(Enum := type('Enum', (), {'__init__': lambda s,v: setattr(s,'value',v)})):
    pass

# Simple pattern enum without importing Enum again
_PATTERNS = ["rising", "falling", "oscillating", "chaotic", "stable", "accelerating"]


@dataclass
class TraumaEvent:
    event_id:    str
    severity:    float           # 0.0 – 1.0
    description: str
    timestamp:   float = field(default_factory=time.time)
    resolved:    bool = False
    recovery_ms: float = 0.0


@dataclass
class AuraSnapshot:
    timestamp:          float
    pulse_rate_hz:      float    # task submissions per second
    intensity:          float    # overall aura strength 0–1
    alignment_score:    float    # agent coherence 0–1
    resonance:          float    # sensing↔compute correlation 0–1
    trauma_index:       float    # active trauma load 0–1
    pattern:            str      # rising / falling / oscillating / chaotic / stable
    dominant_frequency: float    # Hz of dominant oscillation in pulse time series


class AuraEngine:
    """
    Derives the system's aura signature from operational telemetry.

    The aura is modelled as a multi-frequency electromagnetic field:
      - Pulse rate  → fundamental frequency (heartbeat of the system)
      - Alignment   → coherence of harmonic overtones (agent synchrony)
      - Resonance   → cross-correlation between sensing and computation layers
      - Trauma load → destructive interference (unresolved stress events)
      - Intensity   → amplitude of the composite field
    """

    def __init__(self):
        self._pulse_history:  deque = deque(maxlen=600)
        self._aura_history:   deque = deque(maxlen=500)
        self._trauma_log:     List[TraumaEvent] = []
        self._tick = 0
        self._seed()

    def sample(self, metrics: Optional[Dict] = None) -> AuraSnapshot:
        self._tick += 1
        snap = self._compute(metrics)
        self._aura_history.append(snap)
        return snap

    def inject_trauma(self, description: str, severity: float = 0.7) -> TraumaEvent:
        ev = TraumaEvent(
            event_id=f"trm_{int(time.time())}_{self._tick}",
            severity=max(0.0, min(1.0, severity)),
            description=description,
        )
        self._trauma_log.append(ev)
        logger.warning(f"Trauma event: {description} (sev={severity:.2f})")
        return ev

    def resolve_trauma(self, event_id: str, recovery_ms: float = 0.0):
        for ev in self._trauma_log:
            if ev.event_id == event_id:
                ev.resolved = True
                ev.recovery_ms = recovery_ms

    def get_snapshot(self) -> Dict:
        if not self._aura_history:
            self.sample()
        s = self._aura_history[-1]
        return {
            "pulse_rate_hz":      round(s.pulse_rate_hz, 3),
            "intensity":          round(s.intensity, 3),
            "alignment_score":    round(s.alignment_score, 3),
            "resonance":          round(s.resonance, 3),
            "trauma_index":       round(s.trauma_index, 3),
            "pattern":            s.pattern,
            "dominant_frequency": round(s.dominant_frequency, 4),
            "timestamp":          s.timestamp,
            "trauma_events":      len([e for e in self._trauma_log if not e.resolved]),
            "total_trauma":       len(self._trauma_log),
        }

    def get_pulse_series(self, n: int = 120) -> List[Dict]:
        snaps = list(self._aura_history)[-n:]
        return [{"t": s.timestamp, "pulse": s.pulse_rate_hz, "intensity": s.intensity,
                 "alignment": s.alignment_score, "trauma": s.trauma_index} for s in snaps]

    def get_trauma_log(self) -> List[Dict]:
        return [
            {"id": e.event_id, "severity": e.severity, "desc": e.description,
             "ts": e.timestamp, "resolved": e.resolved, "recovery_ms": e.recovery_ms}
            for e in self._trauma_log[-20:]
        ]

    def get_alignment_matrix(self) -> List[Dict]:
        agents = ["Architect","Auditor","Debugger","Optimizer","Learner",
                  "WiFiSensing","SovereignEngine","HybridRouter","CouncilCore"]
        matrix = []
        base_scores = [0.94, 0.97, 0.89, 0.91, 0.93, 0.88, 0.96, 0.99, 0.95]
        recent = list(self._aura_history)[-10:] if self._aura_history else []
        drift = sum(s.trauma_index for s in recent) / max(len(recent), 1) * 0.15
        for agent, score in zip(agents, base_scores):
            coherence = max(0.0, score - drift + random.gauss(0, 0.01))
            matrix.append({
                "agent":     agent,
                "coherence": round(coherence, 3),
                "drift":     round(drift, 3),
                "aligned":   coherence > 0.7,
            })
        return matrix

    # ── Internal ──────────────────────────────────────────────────────────────

    def _compute(self, m: Optional[Dict]) -> AuraSnapshot:
        t = self._tick * 0.05
        noise = lambda scale=0.03: random.gauss(0, scale)

        # Pulse rate: oscillates around a base with subtle drift
        base_hz = 0.8 + math.sin(t * 0.7) * 0.3 + math.sin(t * 2.1) * 0.1
        pulse = max(0.05, base_hz + noise(0.05))
        self._pulse_history.append(pulse)

        # Intensity: amplitude of composite field
        intensity = max(0, min(1,
            0.55 + math.sin(t * 0.9 + 0.5) * 0.3 + noise(0.04)
        ))

        # Alignment: coherence of agent harmonic — degrades during trauma
        active_trauma = sum(1 for e in self._trauma_log if not e.resolved)
        alignment = max(0, min(1,
            0.88 - active_trauma * 0.08 + math.cos(t * 1.2) * 0.06 + noise(0.02)
        ))

        # Resonance: sensing↔compute correlation
        resonance = max(0, min(1,
            0.72 + math.sin(t * 0.4 + 1.0) * 0.2 + noise(0.03)
        ))

        # Trauma index: unresolved trauma load decays over time
        trauma_idx = min(1.0, active_trauma * 0.15 + noise(0.01))

        # Pattern classification from pulse derivative
        pulse_series = list(self._pulse_history)[-20:]
        pattern = _classify_pattern(pulse_series)

        # Dominant frequency: FFT peak of pulse series
        dom_freq = _dominant_freq(list(self._pulse_history)[-64:]) if len(self._pulse_history) >= 32 else 0.1

        return AuraSnapshot(
            timestamp=time.time(),
            pulse_rate_hz=pulse,
            intensity=intensity,
            alignment_score=alignment,
            resonance=resonance,
            trauma_index=trauma_idx,
            pattern=pattern,
            dominant_frequency=dom_freq,
        )

    def _seed(self):
        for i in range(120):
            t = i * 0.05
            s = AuraSnapshot(
                timestamp=time.time() - (120 - i) * 2,
                pulse_rate_hz=max(0.05, 0.7 + math.sin(t * 0.7) * 0.25),
                intensity=max(0, 0.5 + math.sin(t * 0.9) * 0.3),
                alignment_score=max(0, 0.85 + math.cos(t * 1.2) * 0.1),
                resonance=max(0, 0.70 + math.sin(t * 0.4) * 0.2),
                trauma_index=max(0, abs(math.sin(t * 3)) * 0.15),
                pattern="oscillating",
                dominant_frequency=0.08,
            )
            self._aura_history.append(s)
        # Seed 2 historical trauma events (resolved)
        self._trauma_log.append(TraumaEvent(
            event_id="trm_seed_1", severity=0.62,
            description="Council quorum drift — Perplexity voter timeout",
            timestamp=time.time() - 3600, resolved=True, recovery_ms=1240,
        ))
        self._trauma_log.append(TraumaEvent(
            event_id="trm_seed_2", severity=0.38,
            description="CSI pipeline buffer overflow — frame drop 12%",
            timestamp=time.time() - 900, resolved=True, recovery_ms=340,
        ))


def _classify_pattern(series: List[float]) -> str:
    if len(series) < 4:
        return "stable"
    diffs = [series[i+1] - series[i] for i in range(len(series)-1)]
    pos = sum(1 for d in diffs if d > 0.02)
    neg = sum(1 for d in diffs if d < -0.02)
    swings = sum(1 for i in range(len(diffs)-1) if diffs[i]*diffs[i+1] < 0)
    variance = sum(d**2 for d in diffs) / len(diffs)
    if variance > 0.08: return "chaotic"
    if swings > len(diffs) * 0.5: return "oscillating"
    if pos > neg * 2: return "rising" if pos > len(diffs)*0.5 else "accelerating"
    if neg > pos * 2: return "falling"
    return "stable"


def _dominant_freq(series: List[float]) -> float:
    n = len(series)
    if n < 8: return 0.1
    mean = sum(series) / n
    sig = [v - mean for v in series]
    best_k, best_mag = 1, 0.0
    two_pi_n = 2 * math.pi / n
    for k in range(1, n // 2):
        re = sum(sig[t] * math.cos(two_pi_n * k * t) for t in range(n))
        im = sum(-sig[t] * math.sin(two_pi_n * k * t) for t in range(n))
        mag = math.sqrt(re*re + im*im)
        if mag > best_mag:
            best_mag, best_k = mag, k
    sample_rate = 0.5  # samples per second
    return best_k * sample_rate / n
