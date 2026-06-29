"""ARK95X Motion Detector
AI-driven presence, motion, and breathing analysis from CSI frames.

Detection pipeline:
  1. Presence  — amplitude variance threshold over a short window
  2. Motion    — frame-to-frame mean-amplitude delta (gross movement)
  3. Breathing — FFT of per-subcarrier amplitude series; peak in 0.1–0.6 Hz
                 (6–36 breaths/min, typical adult resting range is 12–20 bpm)
"""
import time
import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

from src.sensing.csi_processor import CSIFrame

logger = logging.getLogger("ark95x.sensing.motion")

# ── Defaults ─────────────────────────────────────────────────────────────────
_PRESENCE_WINDOW = 30          # frames for presence decision
_MOTION_WINDOW = 10            # frames for gross-motion delta
_BREATHING_WINDOW = 300        # frames for FFT (~30 s at 10 Hz)
_PRESENCE_VAR_THRESHOLD = 2e-3 # normalized amplitude variance threshold
_MOTION_DELTA_THRESHOLD = 0.03 # mean-amplitude delta per frame
_MIN_BREATHING_HZ = 0.1        # 6 bpm
_MAX_BREATHING_HZ = 0.6        # 36 bpm
_SAMPLE_RATE_HZ = 10.0         # expected CSI frame rate


class PresenceState(Enum):
    EMPTY = "empty"
    OCCUPIED = "occupied"
    UNCERTAIN = "uncertain"


@dataclass
class SensingResult:
    timestamp: float
    presence: PresenceState
    presence_confidence: float          # 0.0–1.0
    motion_detected: bool
    motion_intensity: float             # 0.0–1.0
    breathing_rate_bpm: Optional[float] # None if undetectable
    breathing_confidence: float         # 0.0–1.0
    frame_count: int                    # frames analysed this cycle
    raw_variance: float
    extra: Dict[str, Any] = field(default_factory=dict)


class MotionDetector:
    """
    Stateful detector that maintains a sliding window of CSIFrames and
    emits SensingResult on each call to analyse().

    Configuration keys (all optional):
      presence_threshold  float  amplitude variance cutoff for presence (default 2e-3)
      motion_threshold    float  mean-amplitude delta cutoff for motion (default 0.03)
      sample_rate_hz      float  expected frame rate in Hz (default 10.0)
      presence_window     int    frames used for presence decision (default 30)
      motion_window       int    frames used for gross-motion delta (default 10)
      breathing_window    int    frames used for FFT (default 300)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._presence_threshold: float = self.config.get("presence_threshold", _PRESENCE_VAR_THRESHOLD)
        self._motion_threshold: float = self.config.get("motion_threshold", _MOTION_DELTA_THRESHOLD)
        self._sample_rate: float = self.config.get("sample_rate_hz", _SAMPLE_RATE_HZ)
        self._presence_window: int = self.config.get("presence_window", _PRESENCE_WINDOW)
        self._motion_window: int = self.config.get("motion_window", _MOTION_WINDOW)
        self._breathing_window: int = self.config.get("breathing_window", _BREATHING_WINDOW)

        # Ring buffer of CSI frames
        max_buf = max(self._presence_window, self._motion_window, self._breathing_window) + 10
        self._frames: deque = deque(maxlen=max_buf)

        self._event_history: deque = deque(maxlen=200)
        self._total_analysed = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def ingest(self, frame: CSIFrame) -> None:
        """Push a new CSIFrame into the detector's sliding window."""
        self._frames.append(frame)

    def analyse(self) -> Optional[SensingResult]:
        """
        Run a detection cycle on the current frame buffer.
        Returns None if not enough frames have been collected yet.
        """
        if len(self._frames) < self._presence_window:
            return None

        frames = list(self._frames)
        presence, presence_conf, raw_var = self._detect_presence(frames)
        motion, motion_intensity = self._detect_motion(frames)
        bpm, breath_conf = self._estimate_breathing(frames)

        result = SensingResult(
            timestamp=time.time(),
            presence=presence,
            presence_confidence=presence_conf,
            motion_detected=motion,
            motion_intensity=motion_intensity,
            breathing_rate_bpm=bpm,
            breathing_confidence=breath_conf,
            frame_count=len(frames),
            raw_variance=raw_var,
        )
        self._event_history.append(result)
        self._total_analysed += 1
        logger.debug(
            f"Sensing: presence={presence.value}({presence_conf:.2f}) "
            f"motion={motion}({motion_intensity:.2f}) "
            f"bpm={bpm}"
        )
        return result

    def ingest_and_analyse(self, frame: CSIFrame) -> Optional[SensingResult]:
        """Convenience: ingest a frame then run analysis."""
        self.ingest(frame)
        return self.analyse()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "buffered_frames": len(self._frames),
            "total_analysed": self._total_analysed,
            "event_history": len(self._event_history),
            "thresholds": {
                "presence_variance": self._presence_threshold,
                "motion_delta": self._motion_threshold,
                "sample_rate_hz": self._sample_rate,
            },
        }

    # ── Detection helpers ────────────────────────────────────────────────────

    def _detect_presence(
        self, frames: List[CSIFrame]
    ) -> Tuple[PresenceState, float, float]:
        """
        Measure amplitude variance over the presence window.
        Higher variance → body present (disturbing the signal).
        """
        window = frames[-self._presence_window:]
        means = [f.mean_amplitude for f in window]
        global_mean = sum(means) / len(means)
        variance = sum((m - global_mean) ** 2 for m in means) / len(means)

        if variance >= self._presence_threshold:
            # Map variance to confidence: sigmoid-like normalisation
            ratio = variance / self._presence_threshold
            confidence = min(1.0, ratio / (ratio + 1.0) + 0.5)
            return PresenceState.OCCUPIED, round(confidence, 3), variance
        elif variance >= self._presence_threshold * 0.4:
            return PresenceState.UNCERTAIN, 0.5, variance
        else:
            empty_conf = min(1.0, 1.0 - (variance / self._presence_threshold))
            return PresenceState.EMPTY, round(empty_conf, 3), variance

    def _detect_motion(self, frames: List[CSIFrame]) -> Tuple[bool, float]:
        """
        Frame-to-frame mean-amplitude delta over the motion window.
        Large deltas → gross body motion.
        """
        window = frames[-self._motion_window:]
        if len(window) < 2:
            return False, 0.0
        deltas = [
            abs(window[i].mean_amplitude - window[i - 1].mean_amplitude)
            for i in range(1, len(window))
        ]
        max_delta = max(deltas)
        avg_delta = sum(deltas) / len(deltas)
        intensity = min(1.0, avg_delta / max(self._motion_threshold, 1e-9))
        detected = max_delta > self._motion_threshold
        return detected, round(intensity, 3)

    def _estimate_breathing(
        self, frames: List[CSIFrame]
    ) -> Tuple[Optional[float], float]:
        """
        Run an FFT on the mean-amplitude time series of the breathing window.
        Look for the dominant peak in [0.1, 0.6] Hz (6–36 bpm).
        Returns (bpm, confidence) or (None, 0.0) when undetectable.
        """
        window = frames[-self._breathing_window:]
        if len(window) < 30:
            return None, 0.0

        signal = [f.mean_amplitude for f in window]
        n = len(signal)
        # Remove DC component (subtract mean)
        mean_sig = sum(signal) / n
        signal = [v - mean_sig for v in signal]

        # DFT (pure Python — no numpy dependency required)
        spectrum = _dft_magnitude(signal)

        # Frequency resolution
        freq_res = self._sample_rate / n
        min_bin = max(1, int(_MIN_BREATHING_HZ / freq_res))
        max_bin = min(n // 2, int(_MAX_BREATHING_HZ / freq_res) + 1)

        if min_bin >= max_bin:
            return None, 0.0

        band = spectrum[min_bin:max_bin]
        if not band:
            return None, 0.0

        peak_idx = band.index(max(band))
        peak_freq = (min_bin + peak_idx) * freq_res
        peak_bpm = round(peak_freq * 60.0, 1)

        # Confidence: ratio of peak power to out-of-band mean
        out_of_band = spectrum[:min_bin] + spectrum[max_bin:]
        noise_floor = (sum(out_of_band) / len(out_of_band)) if out_of_band else 1.0
        snr = band[peak_idx] / max(noise_floor, 1e-9)
        confidence = min(1.0, round((snr - 1.0) / (snr + 1.0), 3)) if snr > 1.0 else 0.0

        if confidence < 0.15:
            return None, 0.0
        return peak_bpm, confidence


# ── Lightweight pure-Python DFT ───────────────────────────────────────────────

def _dft_magnitude(signal: List[float]) -> List[float]:
    """
    Compute |X[k]| for k = 0..N-1 using the naive O(N²) DFT.
    For N <= 300 frames this is fast enough (< 2 ms on modern hardware).
    """
    n = len(signal)
    magnitudes: List[float] = []
    two_pi_over_n = 2.0 * math.pi / n
    for k in range(n):
        re = sum(signal[t] * math.cos(two_pi_over_n * k * t) for t in range(n))
        im = sum(-signal[t] * math.sin(two_pi_over_n * k * t) for t in range(n))
        magnitudes.append(math.sqrt(re * re + im * im))
    return magnitudes
