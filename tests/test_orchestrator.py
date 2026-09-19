"""Tests for OrchestratorEngine — agent registration, task dispatch, retry, routing."""
import asyncio
import pytest

from src.core.orchestrator import (
    OrchestratorEngine, AgentDescriptor, AgentState, TaskEnvelope, Priority,
)


def _agent(agent_id="a1", state=AgentState.IDLE, load=0.0, success_rate=1.0):
    return AgentDescriptor(
        agent_id=agent_id, capabilities=["test"],
        state=state, load=load, success_rate=success_rate,
    )


# ── Registration ──────────────────────────────────────────────────────────────

class TestAgentRegistration:

    def test_register_agent(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("a1"))
        assert "a1" in engine.agents

    def test_register_multiple_agents(self):
        engine = OrchestratorEngine()
        for i in range(5):
            engine.register_agent(_agent(f"agent_{i}"))
        assert len(engine.agents) == 5


# ── Agent selection ───────────────────────────────────────────────────────────

class TestAgentSelection:

    def test_select_idle_agent(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("idle_one"))
        task = TaskEnvelope(task_id="t1", payload={})
        assert engine._select_agent(task) == "idle_one"

    def test_no_agent_available_when_all_busy(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("busy", state=AgentState.RUNNING))
        task = TaskEnvelope(task_id="t1", payload={})
        assert engine._select_agent(task) is None

    def test_prefers_high_success_rate(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("low",  success_rate=0.5))
        engine.register_agent(_agent("high", success_rate=1.0))
        task = TaskEnvelope(task_id="t1", payload={})
        assert engine._select_agent(task) == "high"

    def test_no_agent_when_overloaded(self):
        engine = OrchestratorEngine(config={"scale_threshold": 0.5})
        engine.register_agent(_agent("overloaded", load=0.9))
        task = TaskEnvelope(task_id="t1", payload={})
        assert engine._select_agent(task) is None


# ── Task dispatch ─────────────────────────────────────────────────────────────

class TestTaskDispatch:

    @pytest.mark.asyncio
    async def test_submit_task_puts_in_queue(self):
        engine = OrchestratorEngine()
        task = TaskEnvelope(task_id="t1", payload={"x": 1})
        await engine.submit_task(task)
        assert engine.task_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_handler(self):
        engine = OrchestratorEngine(config={
            "handlers": {"a1": lambda payload: asyncio.coroutine(lambda: {"result": payload.get("v")})()}
        })

        async def handler(payload):
            return {"result": payload.get("v")}

        engine.config["handlers"] = {"a1": handler}
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t1", payload={"v": 42})
        await engine._execute_task("a1", task)
        assert engine.results["t1"]["status"] == "ok"
        assert engine.results["t1"]["data"]["result"] == 42

    @pytest.mark.asyncio
    async def test_execute_task_no_handler_echo_mode(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("echo_agent"))
        task = TaskEnvelope(task_id="t_echo", payload={"ping": True})
        await engine._execute_task("echo_agent", task)
        assert engine.results["t_echo"]["status"] == "ok"
        assert engine.results["t_echo"]["data"]["ping"] is True

    @pytest.mark.asyncio
    async def test_failed_task_retries(self):
        call_count = [0]

        async def failing(payload):
            call_count[0] += 1
            raise RuntimeError("fail")

        engine = OrchestratorEngine(config={"handlers": {"a1": failing}})
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t_retry", payload={}, max_retries=2)
        await engine._execute_task("a1", task)
        # First attempt fails, task is re-queued (retries <= max_retries)
        assert engine.task_queue.qsize() == 1
        assert task.retries == 1

    @pytest.mark.asyncio
    async def test_failed_task_marks_failed_after_max_retries(self):
        async def always_fail(payload):
            raise RuntimeError("permanent failure")

        engine = OrchestratorEngine(config={"handlers": {"a1": always_fail}})
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t_perm", payload={}, max_retries=0)
        await engine._execute_task("a1", task)
        assert engine.results["t_perm"]["status"] == "failed"
        assert "error" in engine.results["t_perm"]

    @pytest.mark.asyncio
    async def test_agent_load_restored_after_execution(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t1", payload={})
        initial_load = engine.agents["a1"].load
        await engine._execute_task("a1", task)
        assert engine.agents["a1"].load == initial_load

    @pytest.mark.asyncio
    async def test_agent_state_restored_to_idle(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t1", payload={})
        await engine._execute_task("a1", task)
        assert engine.agents["a1"].state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self):
        engine = OrchestratorEngine()
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t1", payload={})
        await engine._execute_task("a1", task)
        assert len(engine.metrics["throughput"]) == 1
        assert len(engine.metrics["latency"]) == 1

    @pytest.mark.asyncio
    async def test_error_metric_on_failure(self):
        async def bad(payload):
            raise RuntimeError("oops")

        engine = OrchestratorEngine(config={"handlers": {"a1": bad}})
        engine.register_agent(_agent("a1"))
        task = TaskEnvelope(task_id="t_err", payload={}, max_retries=0)
        await engine._execute_task("a1", task)
        assert len(engine.metrics["errors"]) == 1


# ── Priority ordering ─────────────────────────────────────────────────────────

class TestPriorityOrdering:

    @pytest.mark.asyncio
    async def test_critical_before_background(self):
        engine = OrchestratorEngine()
        bg = TaskEnvelope(task_id="bg",   payload={}, priority=Priority.BACKGROUND)
        crit = TaskEnvelope(task_id="cr", payload={}, priority=Priority.CRITICAL)
        await engine.submit_task(bg)
        await engine.submit_task(crit)
        pri1, t1 = await engine.task_queue.get()
        pri2, t2 = await engine.task_queue.get()
        assert t1.task_id == "cr"
        assert t2.task_id == "bg"
