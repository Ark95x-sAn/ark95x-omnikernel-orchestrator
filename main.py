#!/usr/bin/env python3
"""ARK95X Omnikernel Orchestrator - Live Entry Point
Bootstraps all core systems and runs the full autonomous engine.

Usage:
    python main.py                  # Run with defaults
    python main.py --config cfg.json # Run with custom config
    python main.py --api             # Run with FastAPI server
"""
import asyncio
import signal
import sys
import os
import logging
import argparse
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.core.config import ConfigManager
from src.core.orchestrator import (
    OrchestratorEngine, AgentDescriptor, TaskEnvelope, Priority
)
from src.core.self_healing import SelfHealingEngine, HealthCheck, FailureType
from src.core.pipeline_manager import PipelineManager, PipelineStage
from src.core.telemetry import TelemetryCollector

logger = logging.getLogger("ark95x")


def setup_logging(config: ConfigManager):
    level = config.get("logging.level", "INFO")
    fmt = config.get("logging.format", "%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    logging.basicConfig(level=getattr(logging, level), format=fmt)
    log_file = config.get("logging.file")
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(fh)


class Ark95xRuntime:
    """Main runtime that wires and runs all subsystems."""

    def __init__(self, config_path: str = None):
        self.config = ConfigManager(config_path=config_path)
        self.orchestrator = OrchestratorEngine({
            "heal_interval": self.config.get("orchestrator.heal_interval", 30),
            "scale_threshold": self.config.get("orchestrator.scale_threshold", 0.85),
        })
        self.healer = SelfHealingEngine({
            "max_incidents": self.config.get("self_healing.max_incidents", 1000),
        })
        self.pipeline = PipelineManager({
            "max_parallel": self.config.get("pipeline.max_parallel", 10),
        })
        self.telemetry = TelemetryCollector({
            "retention_points": self.config.get("telemetry.retention_points", 10000),
        })
        self._running = False

    def _register_default_agents(self):
        agents = [
            AgentDescriptor(agent_id="router", capabilities=["routing", "dispatch"]),
            AgentDescriptor(agent_id="analyzer", capabilities=["analysis", "patterns"]),
            AgentDescriptor(agent_id="executor", capabilities=["execution", "tasks"]),
            AgentDescriptor(agent_id="monitor", capabilities=["monitoring", "alerts"]),
        ]
        for agent in agents:
            self.orchestrator.register_agent(agent)
            self.healer.add_circuit(agent.agent_id)
        logger.info(f"Registered {len(agents)} default agents")

    def _register_health_checks(self):
        async def check_orchestrator():
            status = self.orchestrator.get_status()
            assert status["running"], "Orchestrator not running"

        async def check_healer():
            report = self.healer.get_report()
            open_circuits = sum(
                1 for c in report["circuits"].values()
                if c["state"] == "open"
            )
            assert open_circuits == 0, f"{open_circuits} circuits open"

        self.healer.register_health_check(
            HealthCheck(name="orchestrator", check_fn=check_orchestrator, interval=15)
        )
        self.healer.register_health_check(
            HealthCheck(name="circuits", check_fn=check_healer, interval=20)
        )

    def _register_recovery_strategies(self):
        async def recover_timeout(incident, error):
            logger.info(f"Timeout recovery: restarting component {incident.component}")
            self.telemetry.increment("recovery.timeout")

        async def recover_resource(incident, error):
            logger.info(f"Resource recovery: freeing resources for {incident.component}")
            self.telemetry.increment("recovery.resource")

        self.healer.register_recovery(FailureType.TIMEOUT, recover_timeout)
        self.healer.register_recovery(FailureType.RESOURCE, recover_resource)

    def _setup_telemetry_thresholds(self):
        self.telemetry.set_threshold("orchestrator.queue_size", warn=100, critical=500)
        self.telemetry.set_threshold("orchestrator.error_rate", warn=0.1, critical=0.3)
        self.telemetry.set_threshold("system.memory_pct", warn=80, critical=95)

    async def _telemetry_loop(self):
        import psutil
        while self._running:
            status = self.orchestrator.get_status()
            self.telemetry.gauge("orchestrator.queue_size", status["queue_size"])
            self.telemetry.gauge("orchestrator.completed", status["completed"])
            self.telemetry.gauge("orchestrator.throughput_1m", status["throughput_1m"])
            self.telemetry.gauge("system.memory_pct", psutil.virtual_memory().percent)
            self.telemetry.gauge("system.cpu_pct", psutil.cpu_percent(interval=0))
            await asyncio.sleep(10)

    async def start(self):
        logger.info("=" * 60)
        logger.info("ARK95X OMNIKERNEL ORCHESTRATOR v1.0.0")
        logger.info("Initializing all subsystems...")
        logger.info("=" * 60)

        self._running = True
        self._register_default_agents()
        self._register_health_checks()
        self._register_recovery_strategies()
        self._setup_telemetry_thresholds()

        await self.orchestrator.start()
        await self.healer.start()
        asyncio.create_task(self._telemetry_loop())

        logger.info("All systems ONLINE - Orchestrator fully operational")
        logger.info(f"Agents: {len(self.orchestrator.agents)}")
        logger.info(f"Circuits: {len(self.healer.circuits)}")
        logger.info(f"Health checks: {len(self.healer.health_checks)}")

    async def stop(self):
        logger.info("Shutting down ARK95X...")
        self._running = False
        await self.orchestrator.stop()
        await self.healer.stop()
        dashboard = self.telemetry.get_dashboard()
        logger.info(f"Final metrics: {dashboard['total_series']} series, {dashboard['total_points']} points")
        logger.info("ARK95X shutdown complete")

    def get_full_status(self):
        return {
            "orchestrator": self.orchestrator.get_status(),
            "healing": self.healer.get_report(),
            "telemetry": self.telemetry.get_dashboard(),
            "config": {"profile": self.config._active_profile},
        }


def create_api(runtime: Ark95xRuntime):
    """Create FastAPI server for the runtime."""
    from fastapi import FastAPI
    app = FastAPI(title="ARK95X Omnikernel", version="1.0.0")

    @app.on_event("startup")
    async def startup():
        await runtime.start()

    @app.on_event("shutdown")
    async def shutdown():
        await runtime.stop()

    @app.get("/status")
    async def status():
        return runtime.get_full_status()

    @app.get("/health")
    async def health():
        report = runtime.healer.get_report()
        all_healthy = all(v["healthy"] for v in report["health"].values())
        return {"healthy": all_healthy, "details": report}

    @app.get("/metrics")
    async def metrics():
        return runtime.telemetry.get_snapshot(window_seconds=300)

    @app.post("/task")
    async def submit_task(payload: dict):
        task = TaskEnvelope(
            task_id=f"api_{int(__import__('time').time())}",
            payload=payload,
            priority=Priority.NORMAL,
        )
        task_id = await runtime.orchestrator.submit_task(task)
        return {"task_id": task_id, "status": "queued"}

    return app


async def run_standalone(config_path: str = None):
    runtime = Ark95xRuntime(config_path=config_path)
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    await runtime.start()

    logger.info("System running. Press Ctrl+C to stop.")
    await stop_event.wait()
    await runtime.stop()


def main():
    parser = argparse.ArgumentParser(description="ARK95X Omnikernel Orchestrator")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument("--api", action="store_true", help="Run with FastAPI server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    args = parser.parse_args()

    if args.api:
        import uvicorn
        runtime = Ark95xRuntime(config_path=args.config)
        setup_logging(runtime.config)
        app = create_api(runtime)
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        runtime = Ark95xRuntime(config_path=args.config)
        setup_logging(runtime.config)
        try:
            asyncio.run(run_standalone(config_path=args.config))
        except KeyboardInterrupt:
            logger.info("Interrupted")


if __name__ == "__main__":
    main()
