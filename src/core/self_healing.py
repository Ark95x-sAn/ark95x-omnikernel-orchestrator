"""ARK95X Self-Healing Module
Autonomous fault detection, diagnosis, and recovery
with circuit breaker patterns and adaptive retry logic.
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger("ark95x.self_healing")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class FailureType(Enum):
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    LOGIC = "logic"
    NETWORK = "network"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    name: str
    check_fn: Optional[Callable] = None
    interval: float = 30.0
    timeout: float = 10.0
    healthy: bool = True
    last_check: float = 0.0
    consecutive_failures: int = 0


@dataclass
class IncidentRecord:
    incident_id: str
    failure_type: FailureType
    component: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""
    recovery_time: float = 0.0


class CircuitBreaker:
    """Circuit breaker to prevent cascade failures."""

    def __init__(self, name: str, failure_threshold: int = 5,
                 recovery_timeout: float = 60.0, half_open_max: int = 3):
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self.last_failure_time = 0.0
        self.metrics = deque(maxlen=200)

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        return self.success_count < self.half_open_max

    def record_success(self):
        self.metrics.append({"time": time.time(), "success": True})
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.name} closed (recovered)")
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.metrics.append({"time": time.time(), "success": False})
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} OPEN after {self.failure_count} failures")


class SelfHealingEngine:
    """Autonomous fault detection and recovery system."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.circuits: Dict[str, CircuitBreaker] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.incidents: List[IncidentRecord] = []
        self.recovery_strategies: Dict[FailureType, Callable] = {}
        self._running = False
        self._max_incidents = self.config.get("max_incidents", 1000)

    def add_circuit(self, name: str, **kwargs) -> CircuitBreaker:
        cb = CircuitBreaker(name, **kwargs)
        self.circuits[name] = cb
        return cb

    def register_health_check(self, check: HealthCheck) -> None:
        self.health_checks[check.name] = check

    def register_recovery(self, failure_type: FailureType, fn: Callable):
        self.recovery_strategies[failure_type] = fn

    async def execute_with_healing(
        self, circuit_name: str, fn: Callable, *args, **kwargs
    ) -> Any:
        circuit = self.circuits.get(circuit_name)
        if not circuit:
            circuit = self.add_circuit(circuit_name)

        if not circuit.can_execute():
            logger.warning(f"Circuit {circuit_name} is open, skipping")
            raise RuntimeError(f"Circuit breaker {circuit_name} is open")

        try:
            result = await fn(*args, **kwargs)
            circuit.record_success()
            return result
        except Exception as e:
            circuit.record_failure()
            failure_type = self._classify_failure(e)
            incident = IncidentRecord(
                incident_id=f"inc_{int(time.time())}_{circuit_name}",
                failure_type=failure_type,
                component=circuit_name,
            )
            self.incidents.append(incident)
            if len(self.incidents) > self._max_incidents:
                self.incidents = self.incidents[-self._max_incidents:]
            await self._attempt_recovery(incident, e)
            raise

    def _classify_failure(self, error: Exception) -> FailureType:
        err_str = str(error).lower()
        if "timeout" in err_str:
            return FailureType.TIMEOUT
        if "memory" in err_str or "resource" in err_str:
            return FailureType.RESOURCE
        if "connection" in err_str or "network" in err_str:
            return FailureType.NETWORK
        if "dependency" in err_str or "import" in err_str:
            return FailureType.DEPENDENCY
        return FailureType.UNKNOWN

    async def _attempt_recovery(self, incident: IncidentRecord, error: Exception):
        strategy = self.recovery_strategies.get(incident.failure_type)
        if strategy:
            try:
                start = time.time()
                await strategy(incident, error)
                incident.resolved = True
                incident.recovery_time = time.time() - start
                incident.resolution = f"auto_{incident.failure_type.value}"
                logger.info(f"Recovered {incident.incident_id} in {incident.recovery_time:.2f}s")
            except Exception as re:
                logger.error(f"Recovery failed for {incident.incident_id}: {re}")

    async def _health_loop(self):
        while self._running:
            for name, check in self.health_checks.items():
                if time.time() - check.last_check < check.interval:
                    continue
                check.last_check = time.time()
                if check.check_fn:
                    try:
                        await asyncio.wait_for(check.check_fn(), timeout=check.timeout)
                        check.healthy = True
                        check.consecutive_failures = 0
                    except Exception:
                        check.consecutive_failures += 1
                        if check.consecutive_failures >= 3:
                            check.healthy = False
                            logger.warning(f"Health check failed: {name}")
            await asyncio.sleep(5)

    async def start(self):
        self._running = True
        asyncio.create_task(self._health_loop())
        logger.info("Self-healing engine active")

    async def stop(self):
        self._running = False

    def get_report(self) -> Dict[str, Any]:
        return {
            "circuits": {
                k: {"state": v.state.value, "failures": v.failure_count}
                for k, v in self.circuits.items()
            },
            "health": {
                k: {"healthy": v.healthy, "failures": v.consecutive_failures}
                for k, v in self.health_checks.items()
            },
            "incidents_total": len(self.incidents),
            "incidents_resolved": sum(1 for i in self.incidents if i.resolved),
        }
