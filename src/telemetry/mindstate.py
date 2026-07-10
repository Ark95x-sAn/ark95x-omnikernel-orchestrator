"""ARK95X Inner Telemetry — MindState Engine
Derives system consciousness state from live telemetry patterns.
Maps computational behaviour to human-legible mind states.
"""
import time
import random
import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger("ark95x.telemetry.mindstate")


class MindState(Enum):
    FLOW       = "flow"       # Peak: high throughput, low error, low latency
    FOCUSED    = "focused"    # Narrow task cluster, deliberate agent selection
    LEARNING   = "learning"   # High memory writes, embedding growth, slow output
    STRESSED   = "stressed"   # Error spikes, circuit breakers, latency chaos
    CLARITY    = "clarity"    # Post-recovery: stable, coherent, integrating
    DORMANT    = "dormant"    # Low activity across all agents


# Dimensional scores driving state detection
@dataclass
class StateVector:
    stress:    float = 0.0   # 0=calm → 1=crisis
    focus:     float = 0.0   # 0=scattered → 1=laser
    flow:      float = 0.0   # 0=blocked → 1=effortless
    clarity:   float = 0.0   # 0=noisy → 1=crystalline
    activity:  float = 0.0   # 0=dormant → 1=saturated
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "stress":   round(self.stress, 3),
            "focus":    round(self.focus, 3),
            "flow":     round(self.flow, 3),
            "clarity":  round(self.clarity, 3),
            "activity": round(self.activity, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class StateTransition:
    from_state: MindState
    to_state:   MindState
    timestamp:  float = field(default_factory=time.time)
    trigger:    str = ""


_STATE_DESCRIPTORS = {
    MindState.FLOW:     ("FLOW STATE",    "#0d9488", "Peak operational coherence. All systems aligned."),
    MindState.FOCUSED:  ("FOCUSED",       "#8b5cf6", "Deliberate execution. Single-domain deep work."),
    MindState.LEARNING: ("LEARNING",      "#7c3aed", "Memory consolidation active. Patterns being encoded."),
    MindState.STRESSED: ("STRESSED",      "#b91c1c", "Elevated error signature. Circuit pressure rising."),
    MindState.CLARITY:  ("CLARITY",       "#b45309", "Integration cycle. Post-stress coherence returning."),
    MindState.DORMANT:  ("DORMANT",       "#4b5380", "Low-energy maintenance mode. Ready state."),
}


class MindStateEngine:
    """
    Derives mind state from rolling telemetry windows.
    Tracks dimensional scores (stress/focus/flow/clarity) and maps them
    to one of 6 system consciousness states via a scored classifier.
    """

    def __init__(self, window: int = 60):
        self.window = window
        self._history: deque = deque(maxlen=1000)
        self._transitions: List[StateTransition] = []
        self._current: MindState = MindState.DORMANT
        self._vector: StateVector = StateVector()
        self._tick = 0
        # Seed with a realistic trajectory
        self._seed_history()

    def sample(self, metrics: Optional[Dict] = None) -> Tuple[MindState, StateVector]:
        """Ingest a telemetry snapshot and recompute state."""
        self._tick += 1
        vector = self._compute_vector(metrics)
        self._vector = vector
        self._history.append(vector)
        new_state = self._classify(vector)
        if new_state != self._current:
            self._transitions.append(StateTransition(
                from_state=self._current,
                to_state=new_state,
                trigger=f"tick_{self._tick}",
            ))
            logger.info(f"MindState: {self._current.value} → {new_state.value}")
        self._current = new_state
        return new_state, vector

    def get_state(self) -> Dict:
        label, color, desc = _STATE_DESCRIPTORS[self._current]
        return {
            "state":       self._current.value,
            "label":       label,
            "color":       color,
            "description": desc,
            "vector":      self._vector.to_dict(),
            "transitions": len(self._transitions),
            "history_len": len(self._history),
        }

    def get_history(self, n: int = 120) -> List[Dict]:
        return [v.to_dict() for v in list(self._history)[-n:]]

    def get_transitions(self) -> List[Dict]:
        return [
            {"from": t.from_state.value, "to": t.to_state.value,
             "ts": t.timestamp, "trigger": t.trigger}
            for t in self._transitions[-20:]
        ]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _compute_vector(self, m: Optional[Dict]) -> StateVector:
        if m:
            return StateVector(
                stress=    float(m.get("error_rate", 0)),
                focus=     float(m.get("agent_focus", 0.5)),
                flow=      float(m.get("throughput_norm", 0.5)),
                clarity=   float(m.get("memory_coherence", 0.5)),
                activity=  float(m.get("activity", 0.5)),
            )
        # Simulate realistic oscillating telemetry
        t = self._tick * 0.08
        phase = math.sin(t) * 0.5 + 0.5
        noise = lambda: random.gauss(0, 0.05)
        return StateVector(
            stress=   max(0, min(1, 0.1 + abs(math.sin(t * 1.7)) * 0.3 + noise())),
            focus=    max(0, min(1, 0.6 + math.cos(t * 0.9) * 0.25 + noise())),
            flow=     max(0, min(1, phase * 0.8 + 0.15 + noise())),
            clarity=  max(0, min(1, 0.55 + math.sin(t * 0.4 + 1) * 0.3 + noise())),
            activity= max(0, min(1, 0.4 + phase * 0.4 + noise())),
        )

    def _classify(self, v: StateVector) -> MindState:
        if v.activity < 0.15:
            return MindState.DORMANT
        if v.stress > 0.65:
            return MindState.STRESSED
        # Previous state was stressed → clarity transition
        if self._current == MindState.STRESSED and v.stress < 0.3:
            return MindState.CLARITY
        if v.flow > 0.75 and v.stress < 0.2 and v.focus > 0.6:
            return MindState.FLOW
        if v.focus > 0.75 and v.activity > 0.4:
            return MindState.FOCUSED
        if v.clarity < 0.35 and v.activity > 0.3:
            return MindState.LEARNING
        if self._current == MindState.CLARITY and v.stress < 0.15:
            return MindState.FLOW
        return self._current  # inertia — states don't flicker

    def _seed_history(self):
        states = [MindState.DORMANT, MindState.FOCUSED, MindState.FLOW,
                  MindState.LEARNING, MindState.CLARITY, MindState.FLOW]
        for i in range(80):
            phase = i / 80.0
            t = phase * 6 * math.pi
            v = StateVector(
                stress=   max(0, 0.08 + math.sin(t * 2.1) * 0.15),
                focus=    max(0, 0.65 + math.cos(t) * 0.2),
                flow=     max(0, 0.5 + math.sin(t * 0.7) * 0.35),
                clarity=  max(0, 0.6 + math.cos(t * 1.3) * 0.25),
                activity= max(0, 0.5 + math.sin(t * 0.5) * 0.3),
                timestamp=time.time() - (80 - i) * 10,
            )
            self._history.append(v)
