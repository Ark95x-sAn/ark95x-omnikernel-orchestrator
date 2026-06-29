"""ARK95X CSI Processor
Ingests and preprocesses Channel State Information frames from
ESP32-S3 hardware (serial/UDP) or replayed capture files.

CSI frame format follows ESP-IDF CSI tool output:
  CSI_DATA,<len>,<mac>,<rssi>,<noise_floor>,<channel>,<ts>,<ant>,<data...>

Data bytes are interleaved imaginary/real signed 8-bit pairs per subcarrier.
"""
import math
import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("ark95x.sensing.csi")

# ESP32-S3 HT40 mode: 128 subcarriers (64 per sideband)
DEFAULT_SUBCARRIER_COUNT = 64
_HAMPEL_WINDOW = 5
_HAMPEL_SIGMA = 3.0


class CSIParseError(ValueError):
    """Raised when a raw CSI frame cannot be parsed."""


@dataclass
class CSIFrame:
    timestamp: float
    source_mac: str
    rssi: float
    noise_floor: float
    channel: int
    antenna: int
    # Per-subcarrier amplitude and phase (length == subcarrier_count)
    amplitudes: List[float]
    phases: List[float]
    # Derived scalar features computed after preprocessing
    mean_amplitude: float = 0.0
    variance: float = 0.0
    snr: float = 0.0

    def __post_init__(self):
        if self.amplitudes:
            self.mean_amplitude = sum(self.amplitudes) / len(self.amplitudes)
            self.variance = sum(
                (a - self.mean_amplitude) ** 2 for a in self.amplitudes
            ) / max(len(self.amplitudes), 1)
            self.snr = max(0.0, self.rssi - self.noise_floor)


def _iq_to_amplitude_phase(raw_bytes: List[int]) -> Tuple[List[float], List[float]]:
    """Convert interleaved (imag, real) signed byte pairs to amplitude/phase."""
    amplitudes: List[float] = []
    phases: List[float] = []
    # raw_bytes layout: [imag0, real0, imag1, real1, ...]
    for i in range(0, len(raw_bytes) - 1, 2):
        imag = float(raw_bytes[i])
        real = float(raw_bytes[i + 1])
        amplitudes.append(math.sqrt(real ** 2 + imag ** 2))
        phases.append(math.atan2(imag, real))
    return amplitudes, phases


def _hampel_filter(values: List[float]) -> List[float]:
    """Replace outliers using a median-based Hampel filter."""
    if len(values) < _HAMPEL_WINDOW:
        return values
    result = list(values)
    half = _HAMPEL_WINDOW // 2
    for i in range(half, len(values) - half):
        window = values[i - half: i + half + 1]
        median = sorted(window)[len(window) // 2]
        mad = sorted(abs(v - median) for v in window)[len(window) // 2]
        if abs(values[i] - median) > _HAMPEL_SIGMA * 1.4826 * mad:
            result[i] = median
    return result


def _normalize(values: List[float]) -> List[float]:
    """Min-max normalize a list to [0, 1]."""
    lo, hi = min(values, default=0.0), max(values, default=1.0)
    span = hi - lo or 1.0
    return [(v - lo) / span for v in values]


class CSIProcessor:
    """
    Ingests raw CSI records and emits cleaned, feature-enriched CSIFrame objects.

    Supported ingestion modes:
      - parse_esp32_line(): single serial log line (ESP-IDF CSI format)
      - parse_json(): dict with keys matching CSIFrame fields (for replays / tests)
      - simulate_frame(): synthetic frame for offline testing

    All parsed frames pass through Hampel outlier filtering and min-max normalization
    before being stored in the ring buffer.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.subcarrier_count: int = self.config.get("subcarrier_count", DEFAULT_SUBCARRIER_COUNT)
        self.buffer_size: int = self.config.get("buffer_size", 500)
        self.frames: deque = deque(maxlen=self.buffer_size)
        self._total_parsed = 0
        self._total_errors = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def parse_esp32_line(self, line: str) -> CSIFrame:
        """
        Parse a single ESP-IDF CSI_DATA log line.
        Expected format (comma-separated):
          CSI_DATA,<len>,<mac>,<rssi>,<noise_floor>,<channel>,<ts>,<ant>,<b0>,<b1>,...
        """
        line = line.strip()
        if not line.startswith("CSI_DATA"):
            raise CSIParseError(f"Not a CSI_DATA line: {line[:40]!r}")
        parts = line.split(",")
        if len(parts) < 9:
            raise CSIParseError(f"Too few fields ({len(parts)}): {line[:60]!r}")
        try:
            mac = parts[2].strip()
            rssi = float(parts[3])
            noise = float(parts[4])
            channel = int(parts[5])
            antenna = int(parts[7]) if parts[7].strip().lstrip("-").isdigit() else 0
            raw_bytes = [int(x) for x in parts[8:] if x.strip().lstrip("-").isdigit()]
        except (ValueError, IndexError) as exc:
            raise CSIParseError(f"Field parse error: {exc}") from exc

        return self._build_frame(
            mac=mac, rssi=rssi, noise=noise,
            channel=channel, antenna=antenna, raw_bytes=raw_bytes,
        )

    def parse_json(self, record: Dict[str, Any]) -> CSIFrame:
        """Accept a dict (from replay files or REST ingest) and emit a CSIFrame."""
        try:
            mac = record.get("mac", "00:00:00:00:00:00")
            rssi = float(record.get("rssi", -70))
            noise = float(record.get("noise_floor", -95))
            channel = int(record.get("channel", 6))
            antenna = int(record.get("antenna", 0))
            raw_bytes: List[int] = record.get("csi_raw", [])
            if not raw_bytes:
                # Accept pre-computed amplitudes/phases directly
                amps = [float(v) for v in record.get("amplitudes", [])]
                phases = [float(v) for v in record.get("phases", [])]
                if not amps:
                    raise CSIParseError("Record has neither csi_raw nor amplitudes")
                return self._build_frame_from_ap(
                    mac, rssi, noise, channel, antenna, amps, phases
                )
        except (TypeError, ValueError) as exc:
            raise CSIParseError(f"JSON parse error: {exc}") from exc
        return self._build_frame(
            mac=mac, rssi=rssi, noise=noise,
            channel=channel, antenna=antenna, raw_bytes=raw_bytes,
        )

    def simulate_frame(
        self,
        rssi: float = -65.0,
        motion: bool = False,
        noise_amplitude: float = 0.05,
    ) -> CSIFrame:
        """
        Produce a synthetic CSI frame for offline testing.
        If motion=True, amplitude variance is increased to mimic body movement.
        """
        import random
        base = 20.0 + (10.0 * random.random() if motion else 0.0)
        amps = [
            max(0.0, base + random.gauss(0, noise_amplitude * base + (5.0 if motion else 1.0)))
            for _ in range(self.subcarrier_count)
        ]
        phases = [random.uniform(-math.pi, math.pi) for _ in range(self.subcarrier_count)]
        return self._build_frame_from_ap(
            mac="02:00:00:00:00:00",
            rssi=rssi,
            noise=-95.0,
            channel=6,
            antenna=0,
            amplitudes=amps,
            phases=phases,
        )

    def get_amplitude_matrix(self, n_frames: Optional[int] = None) -> List[List[float]]:
        """Return amplitude vectors for the last n_frames as a 2-D list [frame][subcarrier]."""
        frames = list(self.frames) if n_frames is None else list(self.frames)[-n_frames:]
        return [f.amplitudes for f in frames]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_parsed": self._total_parsed,
            "total_errors": self._total_errors,
            "buffered_frames": len(self.frames),
            "buffer_capacity": self.buffer_size,
            "subcarrier_count": self.subcarrier_count,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_frame(
        self, mac: str, rssi: float, noise: float,
        channel: int, antenna: int, raw_bytes: List[int],
    ) -> CSIFrame:
        amps, phases = _iq_to_amplitude_phase(raw_bytes)
        return self._build_frame_from_ap(mac, rssi, noise, channel, antenna, amps, phases)

    def _build_frame_from_ap(
        self, mac: str, rssi: float, noise: float,
        channel: int, antenna: int,
        amplitudes: List[float], phases: List[float],
    ) -> CSIFrame:
        amps = _hampel_filter(amplitudes)
        amps = _normalize(amps)
        frame = CSIFrame(
            timestamp=time.time(),
            source_mac=mac,
            rssi=rssi,
            noise_floor=noise,
            channel=channel,
            antenna=antenna,
            amplitudes=amps,
            phases=phases,
        )
        self.frames.append(frame)
        self._total_parsed += 1
        logger.debug(
            f"CSI frame: mac={mac} rssi={rssi:.1f} var={frame.variance:.4f} "
            f"amp_mean={frame.mean_amplitude:.4f}"
        )
        return frame
