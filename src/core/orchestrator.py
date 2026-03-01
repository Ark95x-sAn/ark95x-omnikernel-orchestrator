"""ARK95X Omnikernel Orchestrator - Elite Self-Running Engine
Autonomous multi-agent orchestration with self-healing,
adaptive routing, and continuous optimization.
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger("ark95x.orchestrator")


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    RECOVERING = "recovering"
    SCALING = "scaling"


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskEnvelope:
    task_id: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    retries: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None


@dataclass
class AgentDescriptor:
    agent_id: str
    capabilities: List[str]
    state: AgentState = AgentState.IDLE
    load: float = 0.0
    success_rate: float = 1.0
    avg_latency: float = 0.0
    tasks_completed: int = 0


class OrchestratorEngine:
    """Core orchestration engine with adaptive scheduling."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.agents: Dict[str, AgentDescriptor] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.results: Dict[str, Any] = {}
        self.metrics: Dict[str, deque] = {
            "throughput": deque(maxlen=1000),
            "latency": deque(maxlen=1000),
            "errors": deque(maxlen=500),
        }
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._heal_interval = self.config.get("heal_interval", 30)
        self._scale_threshold = self.config.get("scale_threshold", 0.85)

    def register_agent(self, descriptor: AgentDescriptor) -> None:
        self.agents[descriptor.agent_id] = descriptor
        logger.info(f"Agent registered: {descriptor.agent_id}")

    async def submit_task(self, envelope: TaskEnvelope) -> str:
        await self.task_queue.put((envelope.priority.value, envelope))
        logger.debug(f"Task queued: {envelope.task_id} [{envelope.priority.name}]")
        return envelope.task_id

    def _select_agent(self, task: TaskEnvelope) -> Optional[str]:
        candidates = [
            (aid, a) for aid, a in self.agents.items()
            if a.state == AgentState.IDLE and a.load < self._scale_threshold
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[1].success_rate, x[1].avg_latency))
        return candidates[0][0]

    async def _execute_task(self, agent_id: str, task: TaskEnvelope) -> Any:
        agent = self.agents[agent_id]
        agent.state = AgentState.RUNNING
        agent.load = min(1.0, agent.load + 0.2)
        start = time.time()
        try:
            result = await self._dispatch(agent_id, task)
            elapsed = time.time() - start
            agent.avg_latency = (agent.avg_latency * 0.9) + (elapsed * 0.1)
            agent.tasks_completed += 1
            agent.success_rate = min(1.0, agent.success_rate + 0.01)
            self.metrics["throughput"].append(time.time())
            self.metrics["latency"].append(elapsed)
            self.results[task.task_id] = {"status": "ok", "data": result}
            return result
        except Exception as e:
            agent.success_rate = max(0.0, agent.success_rate - 0.1)
            self.metrics["errors"].append({"time": time.time(), "error": str(e)})
            if task.retries < task.max_retries:
                task.retries += 1
                await self.submit_task(task)
                logger.warning(f"Retry {task.retries}/{task.max_retries}: {task.task_id}")
            else:
                self.results[task.task_id] = {"status": "failed", "error": str(e)}
                logger.error(f"Task failed permanently: {task.task_id}")
        finally:
            agent.state = AgentState.IDLE
            agent.load = max(0.0, agent.load - 0.2)

    async def _dispatch(self, agent_id: str, task: TaskEnvelope) -> Any:
        handler = self.config.get("handlers", {}).get(agent_id)
        if handler and callable(handler):
            return await handler(task.payload)
        logger.warning(f"No handler for {agent_id}, echo mode")
        return task.payload

    async def _main_loop(self):
        logger.info("Orchestrator engine started")
        while self._running:
            try:
                priority, task = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                agent_id = self._select_agent(task)
                if agent_id:
                    asyncio.create_task(self._execute_task(agent_id, task))
                else:
                    await self.submit_task(task)
                    await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(1)

    async def start(self):
        self._running = True
        self._loop_task = asyncio.create_task(self._main_loop())
        asyncio.create_task(self._health_monitor())
        logger.info("Orchestrator fully operational")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info("Orchestrator stopped")

    async def _health_monitor(self):
        while self._running:
            await asyncio.sleep(self._heal_interval)
            for aid, agent in self.agents.items():
                if agent.success_rate < 0.5:
                    agent.state = AgentState.RECOVERING
                    logger.warning(f"Agent {aid} degraded, triggering recovery")
                    await self._recover_agent(aid)

    async def _recover_agent(self, agent_id: str):
        agent = self.agents.get(agent_id)
        if not agent:
            return
        agent.load = 0.0
        agent.success_rate = 0.7
        agent.state = AgentState.IDLE
        logger.info(f"Agent {agent_id} recovered")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "agents": {k: v.state.value for k, v in self.agents.items()},
            "queue_size": self.task_queue.qsize(),
            "completed": len(self.results),
            "throughput_1m": sum(
                1 for t in self.metrics["throughput"]
                if t > time.time() - 60
            ),
        }
