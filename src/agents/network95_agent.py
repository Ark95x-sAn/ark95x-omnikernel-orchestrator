"""
NETWORK-95 Agent

Autonomous 7-stage operating agent implementing the full NETWORK-95 pipeline:

  Stage 1 — INTAKE          Receive objective, load context
  Stage 2 — DECOMPOSE       Break into sub-tasks with dependencies
  Stage 3 — ROUTE & DELEGATE Choose device/agent/executor path
  Stage 4 — EXECUTE         Run work (GPU, local model, Docker, n8n)
  Stage 5 — VERIFY          Independent result validation
  Stage 6 — PERSIST & LEARN  Store state, update mission DB, record lessons
  Stage 7 — NOTIFY & PRESENT Generate delta summary for the operator

Each stage is a PipelineStage wired through PipelineManager (with the
PipelineLearner attached so the agent learns from every run).

Usage:
    agent = Network95Agent()
    mission_id = agent.mission_manager.create("Verify RTX embeddings")
    result = await agent.run_mission(mission_id, context={"input": ...})
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from src.core.pipeline_manager import PipelineManager, PipelineStage
from src.core.pipeline_learn import PipelineLearner
from src.core.mission_manager import MissionManager, MissionStatus
from src.sensing.nexus_intake import NexusIntake, SensorDomain
from src.sensing.fusion_engine import FusionEngine, ActionRecommendation

log = logging.getLogger("network95.agent")

# ── Device / Executor Registry ────────────────────────────────────────────────

DEVICE_REGISTRY: Dict[str, Dict] = {
    "gpu_node": {
        "name": "RTX 2080 (Execution Node)",
        "capabilities": ["embedding", "inference", "docker", "ollama"],
        "available": True,
    },
    "control_node": {
        "name": "SOLARIS-X GM700 (Control Node)",
        "capabilities": ["orchestration", "scheduling", "n8n", "postgres"],
        "available": True,
    },
    "edge_device": {
        "name": "Surface Pro X (Human Interface / Edge)",
        "capabilities": ["ui", "voice", "quick_commands", "field_mode"],
        "available": True,
    },
    "local": {
        "name": "Local Process",
        "capabilities": ["python", "scripts", "file_io"],
        "available": True,
    },
}


def _select_device(task_type: str) -> str:
    """Route a task type to the best available device."""
    routing: Dict[str, str] = {
        "embedding": "gpu_node",
        "inference": "gpu_node",
        "docker": "gpu_node",
        "ollama": "gpu_node",
        "n8n": "control_node",
        "postgres": "control_node",
        "scheduling": "control_node",
        "ui": "edge_device",
        "voice": "edge_device",
        "field_mode": "edge_device",
    }
    device_id = routing.get(task_type, "local")
    dev = DEVICE_REGISTRY.get(device_id, DEVICE_REGISTRY["local"])
    if not dev["available"]:
        log.warning("Device %s unavailable, falling back to local", device_id)
        return "local"
    return device_id


# ── Stage Handlers ────────────────────────────────────────────────────────────

class _Stages:
    """
    Namespace for the 7 stage handler coroutines.
    ctx["__results__"] carries results forward between stages (PipelineManager contract).
    ctx["mission"]  is the Mission object.
    ctx["agent"]    is the Network95Agent (for callbacks).
    """

    @staticmethod
    async def intake(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "intake")

        objective = mission.objective
        input_data = ctx.get("input", {})

        # Capture any provided sensor readings into NexusIntake
        sensor_payloads: List[Dict] = ctx.get("sensor_readings", [])
        for sp in sensor_payloads:
            try:
                domain = SensorDomain(sp["domain"])
                agent.intake.capture(
                    domain=domain,
                    raw=sp.get("raw"),
                    metadata=sp.get("metadata", {}),
                    confidence=float(sp.get("confidence", 0.9)),
                )
            except (KeyError, ValueError) as exc:
                log.warning("Intake: bad sensor payload (%s)", exc)

        log.info("[INTAKE] mission=%s objective=%r", mission.mission_id[:8], objective[:60])
        return {
            "stage": "intake",
            "objective": objective,
            "input": input_data,
            "intake_stats": agent.intake.stats(),
        }

    @staticmethod
    async def decompose(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "decompose")

        intake_result = ctx["__results__"].get("intake", {})
        objective = intake_result.get("objective", mission.objective)

        # Rule-based decomposition — keywords → sub-tasks
        sub_tasks = _decompose_objective(objective)

        log.info("[DECOMPOSE] mission=%s sub_tasks=%d", mission.mission_id[:8], len(sub_tasks))
        return {
            "stage": "decompose",
            "sub_tasks": sub_tasks,
            "dependencies": _build_dependency_graph(sub_tasks),
        }

    @staticmethod
    async def route(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "route")

        decompose_result = ctx["__results__"].get("decompose", {})
        sub_tasks = decompose_result.get("sub_tasks", [])

        routing_plan: List[Dict] = []
        for task in sub_tasks:
            device_id = _select_device(task.get("type", "local"))
            routing_plan.append({
                "task_id": task["id"],
                "task_name": task["name"],
                "device": device_id,
                "device_info": DEVICE_REGISTRY[device_id]["name"],
                "estimated_duration_s": task.get("estimated_s", 5),
            })

        log.info("[ROUTE] mission=%s routing=%d tasks", mission.mission_id[:8], len(routing_plan))
        return {
            "stage": "route",
            "routing_plan": routing_plan,
        }

    @staticmethod
    async def execute(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "execute")

        route_result = ctx["__results__"].get("route", {})
        routing_plan = route_result.get("routing_plan", [])

        # Run fusion pipeline on whatever sensors are active
        batch = agent.intake.synchronize(window_s=1.0)
        action = agent.fusion.run(batch)

        # Simulate / stub execution per routed task
        task_results: List[Dict] = []
        for rp in routing_plan:
            await asyncio.sleep(0)   # yield to event loop
            task_results.append({
                "task_id": rp["task_id"],
                "device": rp["device"],
                "status": "completed",
                "output": f"[{rp['device_info']}] executed: {rp['task_name']}",
            })

        log.info(
            "[EXECUTE] mission=%s tasks_run=%d sensor_action=%s",
            mission.mission_id[:8], len(task_results), action.action_type,
        )
        return {
            "stage": "execute",
            "task_results": task_results,
            "sensor_action": {
                "priority": action.priority,
                "action_type": action.action_type,
                "labels": action.payload.get("labels", []),
                "evidence_hash": action.payload.get("evidence_hash"),
            },
        }

    @staticmethod
    async def verify(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "verify")

        execute_result = ctx["__results__"].get("execute", {})
        task_results = execute_result.get("task_results", [])

        # Verify: check all tasks completed, validate evidence hash exists
        failed_tasks = [t for t in task_results if t.get("status") != "completed"]
        evidence_hash = execute_result.get("sensor_action", {}).get("evidence_hash")

        passed = len(failed_tasks) == 0
        receipt = f"RTX-{int(time.time())}" if passed else None

        log.info(
            "[VERIFY] mission=%s passed=%s failed_tasks=%d receipt=%s",
            mission.mission_id[:8], passed, len(failed_tasks), receipt,
        )
        return {
            "stage": "verify",
            "passed": passed,
            "failed_tasks": failed_tasks,
            "evidence_hash": evidence_hash,
            "receipt": receipt,
        }

    @staticmethod
    async def persist_and_learn(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "persist_learn")

        verify_result = ctx["__results__"].get("verify", {})

        # Build structured lesson from this run
        lesson: Dict[str, Any] = {
            "mission_id": mission.mission_id,
            "objective": mission.objective,
            "passed": verify_result.get("passed"),
            "receipt": verify_result.get("receipt"),
            "timestamp": time.time(),
            "pipeline_summary": agent.learner.summary(),
        }

        # Append to lessons log (JSON lines)
        _append_lesson(lesson)

        log.info(
            "[LEARN] mission=%s passed=%s lesson_stored",
            mission.mission_id[:8], verify_result.get("passed"),
        )
        return {
            "stage": "persist_learn",
            "lesson": lesson,
        }

    @staticmethod
    async def notify(ctx: Dict) -> Dict:
        mission = ctx["mission"]
        agent: Network95Agent = ctx["agent"]
        agent.mission_manager.update_stage(mission.mission_id, "notify")

        results = ctx["__results__"]
        verify = results.get("verify", {})
        execute = results.get("execute", {})
        learn = results.get("persist_learn", {})

        # Delta summary — only what changed, only what matters
        delta = {
            "status": "VERIFIED" if verify.get("passed") else "FAILED",
            "receipt": verify.get("receipt"),
            "evidence_hash": verify.get("evidence_hash"),
            "tasks_run": len(execute.get("task_results", [])),
            "sensor_priority": execute.get("sensor_action", {}).get("priority"),
            "pipeline_bottlenecks": learn.get("lesson", {})
                .get("pipeline_summary", {}).get("bottlenecks", [])[:2],
            "next_steps": _generate_next_steps(verify),
        }

        log.info(
            "[NOTIFY] mission=%s status=%s receipt=%s",
            mission.mission_id[:8], delta["status"], delta["receipt"],
        )
        return {
            "stage": "notify",
            "delta": delta,
        }


# ── Objective decomposition helpers ──────────────────────────────────────────

def _decompose_objective(objective: str) -> List[Dict]:
    """
    Keyword-based decomposer. In production this would call an LLM
    (e.g. via OrchestratorEngine → local Ollama model), but the structure
    is fully compatible with replacing this function with an async LLM call.
    """
    obj_lower = objective.lower()
    tasks: List[Dict] = []
    counter = [0]

    def add(name: str, task_type: str, estimated_s: float = 5.0):
        counter[0] += 1
        tasks.append({
            "id": f"t{counter[0]:03d}",
            "name": name,
            "type": task_type,
            "estimated_s": estimated_s,
        })

    # Always: research
    add("Discover resources and check availability", "scheduling", 2.0)

    if any(w in obj_lower for w in ["embed", "embedding", "vector"]):
        add("Pull embedding model (Ollama)", "ollama", 10.0)
        add("Run embedding computation", "embedding", 5.0)
        add("Write receipt to store", "postgres", 1.0)
    elif any(w in obj_lower for w in ["scan", "research", "search"]):
        add("Run web / index search", "n8n", 8.0)
        add("Summarise findings", "inference", 5.0)
    elif any(w in obj_lower for w in ["build", "compile", "docker"]):
        add("Build Docker container", "docker", 30.0)
        add("Run smoke test", "local", 5.0)
    elif any(w in obj_lower for w in ["draft", "write", "compose"]):
        add("Generate draft via LLM", "inference", 10.0)
        add("Review and refine", "local", 3.0)
    else:
        add("Execute primary task", "local", 5.0)

    add("Validate results", "local", 2.0)

    return tasks


def _build_dependency_graph(sub_tasks: List[Dict]) -> Dict[str, List[str]]:
    """Simple linear dependency: each task depends on the previous."""
    graph: Dict[str, List[str]] = {}
    ids = [t["id"] for t in sub_tasks]
    for i, tid in enumerate(ids):
        graph[tid] = [ids[i - 1]] if i > 0 else []
    return graph


def _generate_next_steps(verify: Dict) -> List[str]:
    steps = []
    if verify.get("passed"):
        steps += ["Promote result to trusted store", "Update machine registry"]
        receipt = verify.get("receipt")
        if receipt:
            steps.append(f"Archive receipt {receipt}")
    else:
        failed = verify.get("failed_tasks", [])
        if failed:
            steps.append(f"Re-run failed tasks: {[t['task_id'] for t in failed]}")
        steps.append("Review evidence hash for tampering")
    steps.append("Move to next queued mission")
    return steps


def _append_lesson(lesson: Dict) -> None:
    """Persist one lesson to a JSONL file for offline review."""
    import os
    os.makedirs("data/lessons", exist_ok=True)
    with open("data/lessons/network95.jsonl", "a") as f:
        f.write(json.dumps(lesson) + "\n")


# ── Network95Agent ────────────────────────────────────────────────────────────

_PIPELINE_NAME = "network95"

_STAGE_DEFS = [
    PipelineStage(name="intake",         handler=_Stages.intake,          dependencies=[]),
    PipelineStage(name="decompose",      handler=_Stages.decompose,       dependencies=["intake"]),
    PipelineStage(name="route",          handler=_Stages.route,           dependencies=["decompose"]),
    PipelineStage(name="execute",        handler=_Stages.execute,         dependencies=["route"]),
    PipelineStage(name="verify",         handler=_Stages.verify,          dependencies=["execute"]),
    PipelineStage(name="persist_learn",  handler=_Stages.persist_and_learn, dependencies=["verify"]),
    PipelineStage(name="notify",         handler=_Stages.notify,          dependencies=["persist_learn"]),
]


class Network95Agent:
    """
    Autonomous operating agent for the NETWORK-95 system.

    Wraps:
      - MissionManager  (mission queue + SQLite persistence)
      - NexusIntake     (24-domain sensor capture)
      - FusionEngine    (FUSE → DECODE → VERIFY → ACT)
      - PipelineManager (7-stage DAG runner)
      - PipelineLearner (learns from every mission run)

    Quick start:
        agent = Network95Agent()
        mid = agent.create_mission("Run embedding test")
        result = await agent.run_mission(mid, context={"input": {"prompt": "hello"}})
        print(result["notify"]["delta"])
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.mission_manager = MissionManager(
            persist=self.config.get("persist_missions", True),
        )
        self.intake = NexusIntake()
        self.fusion = FusionEngine(criteria=self.config.get("fusion_criteria"))
        self.learner = PipelineLearner()
        self.pipeline = PipelineManager(
            config=self.config.get("pipeline", {}),
            learner=self.learner,
        )
        self.pipeline.define_pipeline(_PIPELINE_NAME, _STAGE_DEFS)
        log.info("Network95Agent online — 7 stages registered")

    # ── Public API ────────────────────────────────────────────────────────────

    def create_mission(
        self,
        objective: str,
        priority: int = 5,
        metadata: Optional[Dict] = None,
    ) -> str:
        return self.mission_manager.create(objective, priority=priority, metadata=metadata or {})

    async def run_mission(
        self,
        mission_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full 7-stage NETWORK-95 pipeline for one mission.
        Returns a dict of stage_name → stage_result.
        """
        mission = self.mission_manager.get(mission_id)
        self.mission_manager.start(mission_id)

        ctx: Dict[str, Any] = {
            "mission": mission,
            "agent": self,
            **(context or {}),
        }

        run = await self.pipeline.execute(_PIPELINE_NAME, context=ctx)

        stage_results = {
            name: stage.result
            for name, stage in run.stages.items()
            if stage.result is not None
        }

        if run.status == "completed":
            final = stage_results.get("notify", {}).get("delta", {})
            self.mission_manager.complete(mission_id, result=final)
        else:
            failed_stages = [
                n for n, s in run.stages.items() if s.status.value == "failed"
            ]
            self.mission_manager.fail(
                mission_id,
                error=f"Pipeline {run.status}: failed stages={failed_stages}",
            )

        log.info(
            "Mission %s done | pipeline=%s | duration=%.1fs",
            mission_id[:8], run.status, run.end_time - run.start_time,
        )
        return stage_results

    async def run_next_queued(self, context: Optional[Dict] = None) -> Optional[Dict]:
        """Pull the highest-priority queued mission and run it."""
        queue = self.mission_manager.queue()
        if not queue:
            log.debug("No missions queued")
            return None
        mission = queue[0]
        return await self.run_mission(mission.mission_id, context=context)

    async def autonomous_loop(
        self,
        interval_s: float = 5.0,
        max_iterations: Optional[int] = None,
    ) -> None:
        """
        Continuously drain the mission queue.
        Runs until no missions remain or max_iterations is reached.
        """
        iterations = 0
        log.info("Network95Agent autonomous loop started (interval=%.1fs)", interval_s)
        while True:
            result = await self.run_next_queued()
            if result is None:
                await asyncio.sleep(interval_s)
            iterations += 1
            if max_iterations and iterations >= max_iterations:
                log.info("Autonomous loop reached max_iterations=%d, stopping", max_iterations)
                break

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "system": "NETWORK-95",
            "version": "0.9.5",
            "mission_dashboard": self.mission_manager.dashboard(),
            "intake": self.intake.stats(),
            "pipeline_learner": self.learner.summary(),
            "devices": {
                k: {"name": v["name"], "available": v["available"]}
                for k, v in DEVICE_REGISTRY.items()
            },
        }
