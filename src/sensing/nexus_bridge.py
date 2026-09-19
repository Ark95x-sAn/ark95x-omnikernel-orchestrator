"""
NEXUS Bridge — WiFi sensing → NEXUS-1 CAPTURE pipeline

Translates WiFiSensingAgent analysis results into NexusIntake domain readings
so that presence/motion/breathing data surfaces in the fusion pipeline
automatically every sensing cycle.

Domains populated:
  RF_WIRELESS         — raw RSSI / CSI channel info
  MOTION_INERTIAL     — motion_detected, variance
  PRESENCE_PROXIMITY  — occupancy flag, confidence
  HUMAN_BIOMETRICS    — breathing_rate_bpm
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

log = logging.getLogger("network95.nexus_bridge")


def ingest_sensing_result(intake, result: Dict[str, Any]) -> int:
    """
    Push one WiFiSensingAgent analysis dict into *intake* (NexusIntake).
    Returns the number of domain readings captured.
    """
    from src.sensing.nexus_intake import SensorDomain

    last = result.get("last_analysis") or result.get("analysis")
    if not last:
        return 0

    captured = 0
    confidence = float(last.get("presence_confidence", 0.5))

    # RF_WIRELESS — signal-layer snapshot
    rssi = last.get("rssi") or last.get("mean_rssi")
    rf_raw: Dict[str, Any] = {}
    if rssi is not None:
        rf_raw["rssi"] = rssi
    variance = last.get("variance") or last.get("mean_variance")
    if variance is not None:
        rf_raw["variance"] = variance
    if rf_raw:
        intake.capture(SensorDomain.RF_WIRELESS, raw=rf_raw, confidence=min(confidence + 0.1, 1.0))
        captured += 1

    # MOTION_INERTIAL — motion flag
    motion = last.get("motion_detected")
    if motion is not None:
        intake.capture(
            SensorDomain.MOTION_INERTIAL,
            raw={"motion_detected": int(bool(motion)), "variance": variance or 0.0},
            confidence=confidence,
        )
        captured += 1

    # PRESENCE_PROXIMITY — occupancy
    presence = last.get("presence")
    if presence is not None:
        intake.capture(
            SensorDomain.PRESENCE_PROXIMITY,
            raw={"occupancy": 1 if presence == "occupied" else 0, "state": presence},
            confidence=confidence,
        )
        captured += 1

    # HUMAN_BIOMETRICS — breathing
    bpm = last.get("breathing_rate_bpm")
    if bpm is not None and float(bpm) > 0:
        intake.capture(
            SensorDomain.HUMAN_BIOMETRICS,
            raw={"breathing_bpm": float(bpm)},
            confidence=confidence * 0.85,  # breathing est. has inherent uncertainty
        )
        captured += 1

    if captured:
        log.debug(
            "NexusBridge ingested %d domain readings (presence=%s motion=%s bpm=%s)",
            captured, presence, motion, bpm,
        )

    return captured
