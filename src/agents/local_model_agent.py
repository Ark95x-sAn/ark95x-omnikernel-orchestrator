"""
local_model_agent.py - FLAME Agent for Local Model Operations
ARK95X Omnikernel Orchestrator - Agent Integration Layer

Bridges the SLVSS orchestration layer with the local model
infrastructure. Runs as a sovereign agent in the HLM-9 chamber
system with full hybrid routing capabilities.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class AgentRole(Enum):
    ANALYST = "analyst"
    EXECUTOR = "executor"
    MONITOR = "monitor"
    ROUTER = "router"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentTask:
    task_id: str
    description: str
    required_role: str = "analyst"
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 50
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentMetrics:
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    local_requests: int = 0
    cloud_requests: int = 0
    total_cost: float = 0.0
    tokens_processed: int = 0


class LocalModelAgent:
    """Sovereign agent for local model processing in the ARK95X system."""

    def __init__(self, agent_id: str, role: AgentRole = AgentRole.ANALYST):
        self.agent_id = agent_id
        self.role = role
        self.status = AgentStatus.IDLE
        self.capabilities: List[str] = ["local_model_processing", "hybrid_routing", "perf_monitoring"]
        self.metrics = AgentMetrics()
        self.task_history: List[AgentTask] = []
        self.loaded_models: List[str] = []
        self._router = None
        self._model_manager = None
        self._optimizer = None

    def init_subsystems(
        self,
        ollama_host: str = "http://localhost:11434",
    ) -> None:
        """Initialize model subsystems (lazy import to avoid hard deps)."""
        try:
            from models.hybrid_router import HybridModelRouter
            self._router = HybridModelRouter(ollama_host)
        except ImportError:
            print(f"[Agent {self.agent_id}] HybridModelRouter not available")

        try:
            from models.local_model_manager import LocalModelManager
            self._model_manager = LocalModelManager()
        except ImportError:
            print(f"[Agent {self.agent_id}] LocalModelManager not available")

        try:
            from models.performance_optimizer import ModelPerformanceOptimizer
            self._optimizer = ModelPerformanceOptimizer()
        except ImportError:
            print(f"[Agent {self.agent_id}] PerformanceOptimizer not available")

        self.status = AgentStatus.ACTIVE
        print(f"[Agent {self.agent_id}] Subsystems initialized - role: {self.role.value}")

    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute a task using local/hybrid model routing."""
        self.status = AgentStatus.PROCESSING
        start = time.time()

        try:
            # Build requirements from task parameters
            requirements = {
                "task_type": task.parameters.get("task_type", "general"),
                "privacy_required": task.parameters.get("privacy_required", False),
                "max_tokens": task.parameters.get("max_tokens", 500),
                "temperature": task.parameters.get("temperature", 0.7),
                "budget": task.parameters.get("budget", 1.0),
                "offline_capable": task.parameters.get("offline_capable", False),
            }

            # Model selection via manager
            selected_model = None
            if self._model_manager:
                result = self._model_manager.get_best_model_for_task({
                    "type": requirements["task_type"],
                    "hardware": "gpu",
                    "priority": "high" if task.priority > 70 else "normal",
                })
                if result:
                    selected_model = result[0]
                    print(f"[Agent {self.agent_id}] Selected model: {selected_model} (score: {result[1]:.1f})")

            # Apply performance optimization
            if self._optimizer and selected_model:
                ollama_opts = self._optimizer.get_ollama_config(selected_model)
                requirements["ollama_options"] = ollama_opts

            # Route and execute
            if self._router:
                routing_result = await self._router.route_request(
                    task.description, requirements
                )

                latency = (time.time() - start) * 1000
                self._update_metrics(routing_result, latency)

                task.result = {
                    "success": routing_result.success,
                    "provider": routing_result.provider,
                    "model": routing_result.model,
                    "response": routing_result.response,
                    "tokens_used": routing_result.tokens_used,
                    "cost": routing_result.cost,
                    "latency_ms": latency,
                    "cached": routing_result.cached,
                }
            else:
                task.result = {
                    "success": False,
                    "error": "Router not initialized",
                }

            task.completed_at = time.time()
            self.task_history.append(task)
            self.status = AgentStatus.ACTIVE
            return task.result

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.metrics.tasks_failed += 1
            task.error = str(e)
            task.completed_at = time.time()
            self.task_history.append(task)
            self.status = AgentStatus.ERROR
            return {"success": False, "error": str(e), "latency_ms": latency}

    def _update_metrics(self, result: Any, latency_ms: float) -> None:
        """Update agent metrics from routing result."""
        if result.success:
            self.metrics.tasks_completed += 1
        else:
            self.metrics.tasks_failed += 1

        self.metrics.total_latency_ms += latency_ms
        total = self.metrics.tasks_completed + self.metrics.tasks_failed
        if total > 0:
            self.metrics.avg_latency_ms = self.metrics.total_latency_ms / total

        if result.provider == "local":
            self.metrics.local_requests += 1
        else:
            self.metrics.cloud_requests += 1

        self.metrics.total_cost += result.cost
        self.metrics.tokens_processed += result.tokens_used

        # Record in model manager
        if self._model_manager and result.model:
            self._model_manager.record_usage(result.model, latency_ms)

    async def health_check(self) -> Dict[str, Any]:
        """Run health check on all subsystems."""
        health = {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "status": self.status.value,
            "router_available": self._router is not None,
            "model_manager_available": self._model_manager is not None,
            "optimizer_available": self._optimizer is not None,
        }

        if self._optimizer:
            health["hardware"] = self._optimizer.get_summary()["hardware"]

        if self._model_manager:
            health["models"] = self._model_manager.get_inventory()

        if self._router:
            health["routing"] = self._router.get_status()

        return health

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "status": self.status.value,
            "tasks_completed": self.metrics.tasks_completed,
            "tasks_failed": self.metrics.tasks_failed,
            "avg_latency_ms": round(self.metrics.avg_latency_ms, 2),
            "local_requests": self.metrics.local_requests,
            "cloud_requests": self.metrics.cloud_requests,
            "total_cost": round(self.metrics.total_cost, 4),
            "tokens_processed": self.metrics.tokens_processed,
            "task_history_size": len(self.task_history),
        }

    def __repr__(self) -> str:
        return (
            f"LocalModelAgent(id={self.agent_id}, role={self.role.value}, "
            f"status={self.status.value}, completed={self.metrics.tasks_completed})"
        )
