"""ARK95X Wi-Fi Sensing Agent
Bridges the CSI sensing pipeline into the OrchestratorEngine agent framework.

Registers as an AgentDescriptor and handles TaskEnvelopes whose payload
specifies a sensing operation.  Emits real-time metrics to TelemetryCollector.

Supported task payload actions:
  "ingest_frame"    — parse and ingest a single CSI frame (dict or ESP32 line)
  "simulate"        — generate N synthetic frames and return analysis
  "analyse"         — run detection on the current buffer and return result
  "status"          — return processor + detector stats
"""
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List

from src.core.orchestrator import AgentDescriptor, AgentState, TaskEnvelope
from src.core.telemetry import TelemetryCollector
from src.sensing.csi_processor import CSIProcessor, CSIParseError
from src.sensing.motion_detector import MotionDetector, SensingResult, PresenceState

logger = logging.getLogger("ark95x.sensing.agent")

AGENT_ID = "wifi_sensing"
CAPABILITIES = ["presence_detection", "motion_detection", "breathing_estimation", "csi_ingest"]


class WiFiSensingAgent:
    """
    Self-contained Wi-Fi sensing subsystem that can be registered with the
    OrchestratorEngine.  It owns a CSIProcessor and MotionDetector, handles
    task dispatch, and publishes metrics to TelemetryCollector.

    Usage:
        agent = WiFiSensingAgent(config={...}, telemetry=collector)
        engine.register_agent(agent.descriptor)
        engine.config["handlers"][AGENT_ID] = agent.handle_task
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        telemetry: Optional[TelemetryCollector] = None,
    ):
        self.config = config or {}
        self.telemetry = telemetry
        self.processor = CSIProcessor(config=self.config.get("processor", {}))
        self.detector = MotionDetector(config=self.config.get("detector", {}))
        self._tasks_handled = 0
        self._errors = 0
        self._last_result: Optional[SensingResult] = None

        self.descriptor = AgentDescriptor(
            agent_id=AGENT_ID,
            capabilities=CAPABILITIES,
            state=AgentState.IDLE,
        )
        logger.info(f"WiFiSensingAgent ready | capabilities={CAPABILITIES}")

    # ── Task handler (registered with OrchestratorEngine) ─────────────────────

    async def handle_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a TaskEnvelope payload to the correct sensing action."""
        action = payload.get("action", "status")
        start = time.time()
        try:
            if action == "ingest_frame":
                result = await self._handle_ingest(payload)
            elif action == "simulate":
                result = await self._handle_simulate(payload)
            elif action == "analyse":
                result = await self._handle_analyse()
            elif action == "status":
                result = self._handle_status()
            else:
                result = {"error": f"Unknown action: {action!r}"}

            self._tasks_handled += 1
            elapsed = time.time() - start
            self._emit_metric("sensing.task_latency_ms", elapsed * 1000, action=action)
            self._emit_metric("sensing.tasks_total", float(self._tasks_handled))
            return result

        except Exception as exc:
            self._errors += 1
            self._emit_metric("sensing.errors_total", float(self._errors))
            logger.error(f"WiFiSensingAgent error [{action}]: {exc}")
            return {"error": str(exc), "action": action}

    # ── Action handlers ───────────────────────────────────────────────────────

    async def _handle_ingest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest one CSI frame and optionally return sensing analysis."""
        raw = payload.get("raw")
        if isinstance(raw, str):
            frame = self.processor.parse_esp32_line(raw)
        elif isinstance(raw, dict):
            frame = self.processor.parse_json(raw)
        else:
            raise CSIParseError("payload.raw must be an ESP32 log string or a CSI dict")

        result = self.detector.ingest_and_analyse(frame)
        self._last_result = result
        self._publish_result_metrics(result)

        return {
            "frame": {
                "timestamp": frame.timestamp,
                "mac": frame.source_mac,
                "rssi": frame.rssi,
                "mean_amplitude": round(frame.mean_amplitude, 5),
                "variance": round(frame.variance, 6),
            },
            "analysis": _result_to_dict(result),
        }

    async def _handle_simulate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate N synthetic CSI frames with optional motion flag."""
        n: int = max(1, min(int(payload.get("n", 50)), 1000))
        motion: bool = bool(payload.get("motion", False))
        noise: float = float(payload.get("noise_amplitude", 0.05))

        analyses: List[Optional[Dict]] = []
        for _ in range(n):
            frame = self.processor.simulate_frame(motion=motion, noise_amplitude=noise)
            result = self.detector.ingest_and_analyse(frame)
            self._last_result = result
            if result:
                self._publish_result_metrics(result)
                analyses.append(_result_to_dict(result))
            # Yield control every 10 frames so the event loop stays responsive
            if _ % 10 == 9:
                await asyncio.sleep(0)

        last = analyses[-1] if analyses else None
        return {
            "frames_simulated": n,
            "motion_flag": motion,
            "last_analysis": last,
        }

    async def _handle_analyse(self) -> Dict[str, Any]:
        """Run analysis on whatever frames are currently buffered."""
        result = self.detector.analyse()
        if result is None:
            needed = self.detector._presence_window
            buffered = len(self.detector._frames)
            return {
                "status": "insufficient_data",
                "buffered_frames": buffered,
                "needed": needed,
            }
        self._last_result = result
        self._publish_result_metrics(result)
        return _result_to_dict(result)

    def _handle_status(self) -> Dict[str, Any]:
        return {
            "agent_id": AGENT_ID,
            "capabilities": CAPABILITIES,
            "tasks_handled": self._tasks_handled,
            "errors": self._errors,
            "processor": self.processor.get_stats(),
            "detector": self.detector.get_stats(),
            "last_result": _result_to_dict(self._last_result) if self._last_result else None,
        }

    # ── Telemetry helpers ──────────────────────────────────────────────────────

    def _emit_metric(self, name: str, value: float, **labels):
        if self.telemetry:
            self.telemetry.gauge(name, value, **labels)

    def _publish_result_metrics(self, result: Optional[SensingResult]):
        if not result or not self.telemetry:
            return
        self.telemetry.gauge("sensing.presence_confidence", result.presence_confidence)
        self.telemetry.gauge("sensing.motion_intensity", result.motion_intensity)
        self.telemetry.gauge("sensing.raw_variance", result.raw_variance)
        if result.breathing_rate_bpm is not None:
            self.telemetry.gauge("sensing.breathing_bpm", result.breathing_rate_bpm)
            self.telemetry.gauge("sensing.breathing_confidence", result.breathing_confidence)
        occupied = 1.0 if result.presence == PresenceState.OCCUPIED else 0.0
        self.telemetry.gauge("sensing.occupied", occupied)


# ── Serialisation helper ──────────────────────────────────────────────────────

def _result_to_dict(result: Optional[SensingResult]) -> Optional[Dict[str, Any]]:
    if result is None:
        return None
    return {
        "timestamp": result.timestamp,
        "presence": result.presence.value,
        "presence_confidence": result.presence_confidence,
        "motion_detected": result.motion_detected,
        "motion_intensity": result.motion_intensity,
        "breathing_rate_bpm": result.breathing_rate_bpm,
        "breathing_confidence": result.breathing_confidence,
        "frame_count": result.frame_count,
        "raw_variance": round(result.raw_variance, 6),
    }
