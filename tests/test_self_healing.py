"""Tests for CircuitBreaker and SelfHealingEngine."""
import asyncio
import pytest
import time

from src.core.self_healing import (
    CircuitBreaker, CircuitState,
    SelfHealingEngine, FailureType, HealthCheck,
)


# ── CircuitBreaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_does_not_open_before_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_transitions_to_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # recovery_timeout=0 means it should immediately allow half-open
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_closed_after_enough_successes_in_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.0, half_open_max=2)
        cb.record_failure()
        cb.can_execute()  # trigger half-open
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_success_in_closed_state_decrements_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        cb.record_success()
        assert cb.failure_count == 1

    def test_half_open_allows_limited_requests(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.0, half_open_max=2)
        cb.record_failure()
        assert cb.can_execute() is True   # first half-open check
        assert cb.can_execute() is True   # second (success_count still 0)

    def test_metrics_recorded(self):
        cb = CircuitBreaker("test")
        cb.record_success()
        cb.record_failure()
        assert len(cb.metrics) == 2


# ── SelfHealingEngine ─────────────────────────────────────────────────────────

class TestSelfHealingEngine:

    def test_add_circuit_creates_breaker(self):
        engine = SelfHealingEngine()
        cb = engine.add_circuit("svc_a")
        assert isinstance(cb, CircuitBreaker)
        assert "svc_a" in engine.circuits

    def test_get_report_structure(self):
        engine = SelfHealingEngine()
        engine.add_circuit("svc_a")
        report = engine.get_report()
        for key in ("circuits", "health", "incidents_total", "incidents_resolved"):
            assert key in report

    @pytest.mark.asyncio
    async def test_execute_success_records_success(self):
        engine = SelfHealingEngine()
        engine.add_circuit("ok_svc")

        async def good():
            return 42

        result = await engine.execute_with_healing("ok_svc", good)
        assert result == 42
        assert engine.circuits["ok_svc"].failure_count == 0

    @pytest.mark.asyncio
    async def test_execute_failure_records_failure_and_raises(self):
        engine = SelfHealingEngine()
        engine.add_circuit("bad_svc")

        async def bad():
            raise ValueError("network error")

        with pytest.raises(ValueError):
            await engine.execute_with_healing("bad_svc", bad)

        assert engine.circuits["bad_svc"].failure_count == 1

    @pytest.mark.asyncio
    async def test_open_circuit_raises_immediately(self):
        engine = SelfHealingEngine()
        cb = engine.add_circuit("tripped", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        async def would_run():
            return "should not get here"

        with pytest.raises(RuntimeError, match="open"):
            await engine.execute_with_healing("tripped", would_run)

    @pytest.mark.asyncio
    async def test_incident_recorded_on_failure(self):
        engine = SelfHealingEngine()

        async def bad():
            raise RuntimeError("timeout error")

        with pytest.raises(RuntimeError):
            await engine.execute_with_healing("svc", bad)

        assert len(engine.incidents) == 1

    @pytest.mark.asyncio
    async def test_failure_classified_as_timeout(self):
        engine = SelfHealingEngine()

        async def bad():
            raise RuntimeError("timeout after 30s")

        with pytest.raises(RuntimeError):
            await engine.execute_with_healing("svc", bad)

        assert engine.incidents[0].failure_type == FailureType.TIMEOUT

    @pytest.mark.asyncio
    async def test_failure_classified_as_network(self):
        engine = SelfHealingEngine()

        async def bad():
            raise RuntimeError("connection refused")

        with pytest.raises(RuntimeError):
            await engine.execute_with_healing("svc", bad)

        assert engine.incidents[0].failure_type == FailureType.NETWORK

    @pytest.mark.asyncio
    async def test_recovery_strategy_called(self):
        engine = SelfHealingEngine()
        recovered = []

        async def strategy(incident, error):
            recovered.append(incident.component)

        engine.register_recovery(FailureType.UNKNOWN, strategy)

        async def bad():
            raise RuntimeError("generic error")

        with pytest.raises(RuntimeError):
            await engine.execute_with_healing("comp", bad)

        assert "comp" in recovered

    @pytest.mark.asyncio
    async def test_auto_create_circuit_if_missing(self):
        engine = SelfHealingEngine()

        async def ok():
            return "hi"

        result = await engine.execute_with_healing("auto_circuit", ok)
        assert result == "hi"
        assert "auto_circuit" in engine.circuits

    def test_classify_failure_types(self):
        engine = SelfHealingEngine()
        assert engine._classify_failure(RuntimeError("timeout")) == FailureType.TIMEOUT
        assert engine._classify_failure(RuntimeError("connection lost")) == FailureType.NETWORK
        assert engine._classify_failure(RuntimeError("out of memory")) == FailureType.RESOURCE
        assert engine._classify_failure(RuntimeError("import failed")) == FailureType.DEPENDENCY
        assert engine._classify_failure(RuntimeError("some other issue")) == FailureType.UNKNOWN
