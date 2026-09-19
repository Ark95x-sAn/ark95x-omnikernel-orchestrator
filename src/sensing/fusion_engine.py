"""
NEXUS-1 Fusion Engine — FUSE → DECODE → VERIFY → ACT

Takes a SynchronizedBatch from NexusIntake and produces:
  1. EvidenceStream  — merged evidence from all domains (FUSE)
  2. DecodedState    — extracted patterns, meaning, state (DECODE)
  3. VerificationResult — validation of decoded state (VERIFY)
  4. ActionRecommendation — what to do next (ACT)

Pipeline position:  NexusIntake → [FUSE] → [DECODE] → [VERIFY] → [ACT]
"""
from __future__ import annotations

import time
import logging
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.sensing.nexus_intake import SynchronizedBatch, SensorDomain, SensorReading

log = logging.getLogger("nexus.fusion")


# ── Stage 1: FUSE ─────────────────────────────────────────────────────────────

@dataclass
class EvidenceStream:
    """Unified evidence produced by fusing a SynchronizedBatch."""
    stream_id: str
    batch_id: str
    timestamp: float
    # Weighted average of all reading quality scores
    fused_confidence: float
    # Domain → its most-informative scalar features (numeric extraction)
    domain_features: Dict[str, Dict[str, float]]
    # Raw readings that contributed
    contributing: List[SensorReading] = field(default_factory=list)
    # Hash over all raw payloads — serves as the evidence receipt
    evidence_hash: str = ""

    def __post_init__(self):
        if not self.evidence_hash:
            payload = json.dumps(
                {r.domain.value: str(r.raw) for r in self.contributing},
                sort_keys=True,
            )
            self.evidence_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Stage 2: DECODE ───────────────────────────────────────────────────────────

@dataclass
class DecodedState:
    """Patterns, meaning and state extracted from an EvidenceStream."""
    stream_id: str
    timestamp: float
    # High-level state labels (e.g. "occupied", "motion_detected", "anomaly")
    state_labels: List[str]
    # Confidence per label [0, 1]
    label_confidence: Dict[str, float]
    # Raw feature dict forwarded for verification
    features: Dict[str, Any]
    # Human-readable interpretation
    narrative: str = ""


# ── Stage 3: VERIFY ───────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    """Pass / Fail decision with evidence backing."""
    stream_id: str
    timestamp: float
    passed: bool
    score: float                    # [0, 1] — how strongly the evidence supports passing
    criteria_met: List[str]
    criteria_failed: List[str]
    evidence_hash: str              # From EvidenceStream for audit
    notes: str = ""


# ── Stage 4: ACT ─────────────────────────────────────────────────────────────

@dataclass
class ActionRecommendation:
    """Decision output of the ACT stage."""
    stream_id: str
    timestamp: float
    priority: str                  # "critical" | "high" | "normal" | "low"
    action_type: str               # e.g. "alert", "log", "trigger_pipeline", "no_action"
    target: Optional[str]          # Agent / system to route to
    payload: Dict[str, Any]        # Data to pass to the target
    rationale: str = ""


# ── Domain feature extractors ─────────────────────────────────────────────────

def _extract_features(reading: SensorReading) -> Dict[str, float]:
    """Pull numeric scalars from a reading's raw payload for fusion math."""
    raw = reading.raw
    features: Dict[str, float] = {}

    if not isinstance(raw, dict):
        # If raw is a bare number, wrap it
        if isinstance(raw, (int, float)):
            features["value"] = float(raw)
        return features

    for k, v in raw.items():
        if isinstance(v, (int, float)):
            features[k] = float(v)
        elif isinstance(v, bool):
            features[k] = 1.0 if v else 0.0
    return features


def _weighted_confidence(readings: List[SensorReading]) -> float:
    if not readings:
        return 0.0
    total_w = sum(r.quality_score for r in readings)
    if total_w == 0:
        return 0.0
    return sum(r.confidence * r.quality_score for r in readings) / total_w


# ── Domain-specific decoders ──────────────────────────────────────────────────

class _Decoders:
    """
    Stateless domain-specific pattern extractors.
    Each returns a dict of (label → confidence) for that domain's reading.
    """

    @staticmethod
    def human_biometrics(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        hr = features.get("heart_rate", features.get("hr", 0))
        if hr:
            if hr > 100:
                labels["tachycardia"] = min(1.0, (hr - 100) / 60)
            elif hr < 50:
                labels["bradycardia"] = min(1.0, (50 - hr) / 30)
            else:
                labels["normal_hr"] = 1.0
        spo2 = features.get("spo2", features.get("blood_oxygen", 0))
        if spo2 and spo2 < 95:
            labels["low_spo2"] = min(1.0, (95 - spo2) / 10)
        return labels

    @staticmethod
    def motion_inertial(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        accel = max(
            abs(features.get("ax", 0)),
            abs(features.get("ay", 0)),
            abs(features.get("az", 0)),
        )
        if accel > 2.0:
            labels["motion_detected"] = min(1.0, accel / 10.0)
        else:
            labels["stationary"] = 1.0
        if features.get("fall_detected", 0):
            labels["fall_event"] = 1.0
        return labels

    @staticmethod
    def environmental(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        co2 = features.get("co2_ppm", features.get("co2", 0))
        if co2 > 1000:
            labels["poor_air_quality"] = min(1.0, (co2 - 1000) / 2000)
        temp = features.get("temp_c", features.get("temperature", 0))
        if temp:
            if temp > 35:
                labels["high_temperature"] = min(1.0, (temp - 35) / 15)
            elif temp < 5:
                labels["low_temperature"] = min(1.0, (5 - temp) / 20)
        return labels

    @staticmethod
    def machine_device_state(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        cpu = features.get("cpu_pct", features.get("cpu_usage", 0))
        if cpu > 90:
            labels["cpu_critical"] = min(1.0, (cpu - 90) / 10)
        gpu_temp = features.get("gpu_temp", features.get("gpu_temperature", 0))
        if gpu_temp > 85:
            labels["gpu_thermal_throttle_risk"] = min(1.0, (gpu_temp - 85) / 15)
        mem = features.get("ram_pct", features.get("memory_usage", 0))
        if mem > 90:
            labels["memory_pressure"] = min(1.0, (mem - 90) / 10)
        return labels

    @staticmethod
    def network_system(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        latency = features.get("latency_ms", features.get("latency", 0))
        if latency > 200:
            labels["network_degraded"] = min(1.0, (latency - 200) / 800)
        packet_loss = features.get("packet_loss_pct", features.get("loss", 0))
        if packet_loss > 5:
            labels["packet_loss"] = min(1.0, packet_loss / 20)
        return labels

    @staticmethod
    def presence_proximity(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        occ = features.get("occupancy", features.get("presence", 0))
        if occ:
            labels["occupied"] = float(min(1.0, occ))
        else:
            labels["vacant"] = 1.0
        return labels

    @staticmethod
    def rf_wireless(features: Dict[str, float]) -> Dict[str, float]:
        labels: Dict[str, float] = {}
        rssi = features.get("rssi", features.get("signal_strength", -100))
        if rssi > -50:
            labels["strong_rf"] = 1.0
        elif rssi > -70:
            labels["moderate_rf"] = 1.0
        else:
            labels["weak_rf"] = min(1.0, (-70 - rssi) / 30)
        return labels

    @classmethod
    def decode_domain(
        cls, domain: SensorDomain, features: Dict[str, float]
    ) -> Dict[str, float]:
        _map = {
            SensorDomain.HUMAN_BIOMETRICS: cls.human_biometrics,
            SensorDomain.MOTION_INERTIAL: cls.motion_inertial,
            SensorDomain.ENVIRONMENTAL: cls.environmental,
            SensorDomain.MACHINE_DEVICE_STATE: cls.machine_device_state,
            SensorDomain.NETWORK_SYSTEM: cls.network_system,
            SensorDomain.PRESENCE_PROXIMITY: cls.presence_proximity,
            SensorDomain.RF_WIRELESS: cls.rf_wireless,
        }
        fn = _map.get(domain)
        return fn(features) if fn else {}


# ── Verification criteria ─────────────────────────────────────────────────────

_DEFAULT_CRITERIA = {
    "min_evidence_confidence": 0.3,
    "min_domain_coverage": 0.05,       # at least 5% of domains present
    "no_critical_labels": False,        # don't fail just because a label exists
}

_CRITICAL_LABELS = {"fall_event", "cpu_critical", "low_spo2"}


# ── FusionEngine ──────────────────────────────────────────────────────────────

_STREAM_COUNTER = 0


class FusionEngine:
    """
    Stateless pipeline: batch → EvidenceStream → DecodedState → VerificationResult → ActionRecommendation.

    Usage:
        fe = FusionEngine()
        stream    = fe.fuse(batch)
        decoded   = fe.decode(stream)
        verified  = fe.verify(decoded, stream)
        action    = fe.act(verified, decoded)
    """

    def __init__(self, criteria: Optional[Dict] = None):
        self.criteria = {**_DEFAULT_CRITERIA, **(criteria or {})}

    # ── FUSE ─────────────────────────────────────────────────────────────────

    def fuse(self, batch: SynchronizedBatch) -> EvidenceStream:
        global _STREAM_COUNTER
        _STREAM_COUNTER += 1
        stream_id = f"es_{_STREAM_COUNTER:08d}"

        domain_features: Dict[str, Dict[str, float]] = {}
        valid = [r for r in batch.readings if r.quality_score > 0]
        for r in valid:
            feats = _extract_features(r)
            if feats:
                domain_features[r.domain.value] = feats

        fused_conf = _weighted_confidence(valid)
        log.info(
            "FUSE stream=%s batch=%s domains=%d conf=%.2f",
            stream_id, batch.batch_id, len(valid), fused_conf,
        )
        return EvidenceStream(
            stream_id=stream_id,
            batch_id=batch.batch_id,
            timestamp=time.time(),
            fused_confidence=fused_conf,
            domain_features=domain_features,
            contributing=valid,
        )

    # ── DECODE ────────────────────────────────────────────────────────────────

    def decode(self, stream: EvidenceStream) -> DecodedState:
        all_labels: Dict[str, float] = {}
        for reading in stream.contributing:
            feats = stream.domain_features.get(reading.domain.value, {})
            domain_labels = _Decoders.decode_domain(reading.domain, feats)
            for label, conf in domain_labels.items():
                # Take the max confidence if the same label appears from multiple domains
                existing = all_labels.get(label, 0.0)
                all_labels[label] = max(existing, conf * reading.quality_score)

        # Sort by confidence descending for the narrative
        top = sorted(all_labels.items(), key=lambda x: x[1], reverse=True)
        top_labels = [lbl for lbl, _ in top[:5]]

        narrative = (
            f"Decoded {len(stream.contributing)} domain readings. "
            f"Top signals: {', '.join(top_labels) or 'none'}."
        ) if top_labels else "No patterns decoded from available evidence."

        log.info("DECODE stream=%s labels=%s", stream.stream_id, top_labels)
        return DecodedState(
            stream_id=stream.stream_id,
            timestamp=time.time(),
            state_labels=top_labels,
            label_confidence=all_labels,
            features={d: f for d, f in stream.domain_features.items()},
            narrative=narrative,
        )

    # ── VERIFY ────────────────────────────────────────────────────────────────

    def verify(
        self,
        decoded: DecodedState,
        stream: EvidenceStream,
    ) -> VerificationResult:
        met: List[str] = []
        failed: List[str] = []

        # Criterion 1: minimum evidence confidence
        min_conf = self.criteria["min_evidence_confidence"]
        if stream.fused_confidence >= min_conf:
            met.append(f"confidence≥{min_conf}")
        else:
            failed.append(f"confidence<{min_conf} ({stream.fused_confidence:.2f})")

        # Criterion 2: domain coverage
        min_cov = self.criteria["min_domain_coverage"]
        coverage = len(stream.contributing) / max(len(SensorDomain), 1)
        if coverage >= min_cov:
            met.append(f"coverage≥{min_cov:.0%}")
        else:
            failed.append(f"coverage<{min_cov:.0%} ({coverage:.0%})")

        # Criterion 3: critical label presence
        critical_found = [l for l in decoded.state_labels if l in _CRITICAL_LABELS]
        if critical_found:
            met.append(f"critical_labels={critical_found}")

        passed = len(failed) == 0
        score = len(met) / max(len(met) + len(failed), 1)
        log.info(
            "VERIFY stream=%s passed=%s score=%.2f met=%s failed=%s",
            stream.stream_id, passed, score, met, failed,
        )
        return VerificationResult(
            stream_id=stream.stream_id,
            timestamp=time.time(),
            passed=passed,
            score=score,
            criteria_met=met,
            criteria_failed=failed,
            evidence_hash=stream.evidence_hash,
            notes=f"Critical: {critical_found}" if critical_found else "",
        )

    # ── ACT ───────────────────────────────────────────────────────────────────

    def act(
        self,
        verification: VerificationResult,
        decoded: DecodedState,
    ) -> ActionRecommendation:
        critical = [l for l in decoded.state_labels if l in _CRITICAL_LABELS]

        if critical:
            priority = "critical"
            action_type = "alert"
            target = "network95.notify"
        elif not verification.passed:
            priority = "high"
            action_type = "log"
            target = "network95.learn"
        elif decoded.state_labels:
            priority = "normal"
            action_type = "trigger_pipeline"
            target = "network95.execute"
        else:
            priority = "low"
            action_type = "no_action"
            target = None

        rationale = (
            f"Verification {'passed' if verification.passed else 'failed'} "
            f"(score={verification.score:.2f}). "
            f"Labels: {decoded.state_labels[:3]}. "
            f"{decoded.narrative}"
        )

        log.info(
            "ACT stream=%s priority=%s action=%s target=%s",
            verification.stream_id, priority, action_type, target,
        )
        return ActionRecommendation(
            stream_id=verification.stream_id,
            timestamp=time.time(),
            priority=priority,
            action_type=action_type,
            target=target,
            payload={
                "labels": decoded.state_labels,
                "confidence": verification.score,
                "evidence_hash": verification.evidence_hash,
                "features": decoded.features,
            },
            rationale=rationale,
        )

    # ── One-shot pipeline ─────────────────────────────────────────────────────

    def run(self, batch: SynchronizedBatch) -> ActionRecommendation:
        """Run the full FUSE → DECODE → VERIFY → ACT pipeline in one call."""
        stream = self.fuse(batch)
        decoded = self.decode(stream)
        verified = self.verify(decoded, stream)
        return self.act(verified, decoded)
