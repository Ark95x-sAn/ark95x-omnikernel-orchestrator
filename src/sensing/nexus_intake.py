"""
NEXUS-1 Sensor Intake — CAPTURE + SYNCHRONIZE

Implements the full 24-domain sensor taxonomy from the NEXUS-1 blueprint.
Every sensor feed enters here: the intake normalises it into a SensorReading,
timestamps it, and aligns readings from multiple domains for downstream fusion.

Pipeline position:  [CAPTURE] → [SYNCHRONIZE] → FusionEngine → …
"""
from __future__ import annotations

import time
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("nexus.intake")

# ── 24 Sensor Domains ─────────────────────────────────────────────────────────

class SensorDomain(str, Enum):
    """All 24 domains from the NEXUS-1 sensor intake blueprint."""
    HUMAN_BIOMETRICS        = "human_biometrics"        # HR, HRV, SpO2, body temp, EDA
    IDENTITY_AUTH           = "identity_auth"           # fingerprint, face, iris, voice
    BEHAVIORAL_BIOMETRICS   = "behavioral_biometrics"   # keystrokes, gait, touch patterns
    MOTION_INERTIAL         = "motion_inertial"         # accel, gyro, IMU, fall detection
    POSITIONING_SPATIAL     = "positioning_spatial"     # GPS, UWB, RTK, SLAM, geofencing
    RF_WIRELESS             = "rf_wireless"             # Wi-Fi, BT, NFC, UWB, SDR
    RADAR                   = "radar"                   # FMCW, mmWave, Doppler, presence
    LIDAR                   = "lidar"                   # ToF, 3-D mapping, obstacle detect
    SONAR_ACOUSTIC          = "sonar_acoustic"          # ultrasonic, echolocation, sound
    OPTICAL_IMAGING         = "optical_imaging"         # RGB, IR, thermal, depth, hyper
    AUDIO_ACOUSTICS         = "audio_acoustics"         # mic array, voice, env sound
    ENVIRONMENTAL           = "environmental"           # temp, humidity, air quality, light
    CHEMICAL_BIOCHEMICAL    = "chemical_biochemical"    # gas sensors, VOC, pathogens
    RADIATION_PARTICLE      = "radiation_particle"      # ionizing, gamma, cosmic ray
    ELECTRIC_MAGNETIC       = "electric_magnetic"       # EMF, magnetometer, power line
    MATERIAL_STRUCTURAL     = "material_structural"     # strain, vibration, acoustic emission
    FLUID_PROCESS           = "fluid_process"           # flow, pressure, viscosity, leaks
    MACHINE_DEVICE_STATE    = "machine_device_state"    # CPU/GPU, temps, fan, SMART
    NETWORK_SYSTEM          = "network_system"          # latency, jitter, DNS, security
    TIME_FREQUENCY_QUANTUM  = "time_frequency_quantum"  # atomic clocks, NTP, frequency
    PRESENCE_PROXIMITY      = "presence_proximity"      # occupancy, touchless, beacons
    REMOTE_PLANETARY        = "remote_planetary"        # satellite, SAR, earth obs
    CONTEXT_SEMANTIC        = "context_semantic"        # calendar, location context, intent
    SENSOR_HEALTH_META      = "sensor_health_meta"      # calibration, drift, SNR, confidence


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class SensorReading:
    """Normalised output of the CAPTURE stage for one sensor observation."""
    domain: SensorDomain
    timestamp: float                    # Unix epoch, set at capture
    raw: Any                            # Original payload — never modified
    metadata: Dict[str, Any]           # Source, units, location, device_id …
    confidence: float = 1.0            # [0, 1] source-reported quality
    quality_score: float = 1.0         # [0, 1] computed by intake validator
    seq: int = 0                        # Monotonic sequence per domain

    def summary(self) -> Dict[str, Any]:
        return {
            "domain": self.domain.value,
            "ts": self.timestamp,
            "confidence": round(self.confidence, 3),
            "quality": round(self.quality_score, 3),
            "seq": self.seq,
            "source": self.metadata.get("source", "unknown"),
        }


@dataclass
class SynchronizedBatch:
    """Output of the SYNCHRONIZE stage — time-aligned readings across domains."""
    batch_id: str
    anchor_ts: float                          # Reference timestamp for this batch
    window_s: float                           # Time window half-width in seconds
    readings: List[SensorReading] = field(default_factory=list)
    domains_present: List[str] = field(default_factory=list)
    completeness: float = 0.0                 # fraction of expected domains covered

    def __post_init__(self):
        self.domains_present = list({r.domain.value for r in self.readings})
        self.completeness = len(self.domains_present) / len(SensorDomain)


# ── Intake validator ──────────────────────────────────────────────────────────

_DOMAIN_QUALITY_RULES: Dict[SensorDomain, Dict] = {
    SensorDomain.HUMAN_BIOMETRICS: {
        "required_keys": [],
        "confidence_floor": 0.4,
    },
    SensorDomain.SENSOR_HEALTH_META: {
        "required_keys": [],
        "confidence_floor": 0.0,
    },
}

def _compute_quality(
    domain: SensorDomain,
    raw: Any,
    confidence: float,
) -> float:
    """Estimate reading quality from domain rules and input characteristics."""
    rules = _DOMAIN_QUALITY_RULES.get(domain, {})
    floor = rules.get("confidence_floor", 0.0)
    if confidence < floor:
        return 0.0
    score = confidence
    # Penalise None / empty payloads
    if raw is None or raw == {} or raw == []:
        score *= 0.5
    return min(1.0, max(0.0, score))


# ── NexusIntake ───────────────────────────────────────────────────────────────

_BUFFER_DEPTH = 500   # readings per domain


class NexusIntake:
    """
    Stage 1 + 2 of the NEXUS-1 pipeline: CAPTURE and SYNCHRONIZE.

    Usage:
        intake = NexusIntake()

        # Feed any sensor
        reading = intake.capture(
            SensorDomain.ENVIRONMENTAL,
            raw={"temp_c": 22.1, "humidity_pct": 45},
            metadata={"source": "BME680", "location": "room_a"},
            confidence=0.95,
        )

        # Pull a time-aligned batch across all active domains
        batch = intake.synchronize(window_s=0.5)
    """

    def __init__(self, buffer_depth: int = _BUFFER_DEPTH):
        self._buffers: Dict[SensorDomain, deque] = {
            d: deque(maxlen=buffer_depth) for d in SensorDomain
        }
        self._seq: Dict[SensorDomain, int] = {d: 0 for d in SensorDomain}
        self._batch_counter = 0
        self._total_captured = 0
        self._total_dropped = 0

    # ── CAPTURE ───────────────────────────────────────────────────────────────

    def capture(
        self,
        domain: SensorDomain,
        raw: Any,
        metadata: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
    ) -> SensorReading:
        """Validate, timestamp and buffer one sensor observation."""
        ts = time.time()
        quality = _compute_quality(domain, raw, confidence)
        self._seq[domain] += 1

        reading = SensorReading(
            domain=domain,
            timestamp=ts,
            raw=raw,
            metadata=metadata or {},
            confidence=confidence,
            quality_score=quality,
            seq=self._seq[domain],
        )

        if quality == 0.0:
            self._total_dropped += 1
            log.debug("DROP domain=%s seq=%d quality=0", domain.value, reading.seq)
        else:
            self._buffers[domain].append(reading)
            self._total_captured += 1
            log.debug(
                "CAPTURE domain=%-26s seq=%4d q=%.2f",
                domain.value, reading.seq, quality,
            )
        return reading

    def capture_batch(self, readings: List[Tuple[SensorDomain, Any, Dict, float]]) -> List[SensorReading]:
        """Capture multiple (domain, raw, metadata, confidence) tuples at once."""
        return [self.capture(d, r, m, c) for d, r, m, c in readings]

    # ── SYNCHRONIZE ───────────────────────────────────────────────────────────

    def synchronize(
        self,
        window_s: float = 0.1,
        anchor_ts: Optional[float] = None,
        domains: Optional[List[SensorDomain]] = None,
    ) -> SynchronizedBatch:
        """
        Collect the most-recent reading per domain within [anchor - window_s, anchor].
        Returns a SynchronizedBatch ready for the fusion engine.
        """
        anchor = anchor_ts or time.time()
        cutoff = anchor - window_s
        target_domains = domains or list(SensorDomain)

        gathered: List[SensorReading] = []
        for domain in target_domains:
            buf = self._buffers[domain]
            # Walk backward; take the newest reading that falls inside the window
            for reading in reversed(buf):
                if reading.timestamp >= cutoff:
                    gathered.append(reading)
                    break

        self._batch_counter += 1
        batch_id = f"batch_{self._batch_counter:06d}"
        return SynchronizedBatch(
            batch_id=batch_id,
            anchor_ts=anchor,
            window_s=window_s,
            readings=gathered,
        )

    # ── Inspection helpers ────────────────────────────────────────────────────

    def active_domains(self) -> List[str]:
        return [d.value for d, buf in self._buffers.items() if buf]

    def domain_depth(self, domain: SensorDomain) -> int:
        return len(self._buffers[domain])

    def latest(self, domain: SensorDomain) -> Optional[SensorReading]:
        buf = self._buffers[domain]
        return buf[-1] if buf else None

    def stats(self) -> Dict[str, Any]:
        return {
            "total_captured": self._total_captured,
            "total_dropped": self._total_dropped,
            "active_domains": len(self.active_domains()),
            "batches_issued": self._batch_counter,
            "domain_depths": {
                d.value: len(self._buffers[d])
                for d in SensorDomain
                if self._buffers[d]
            },
        }
