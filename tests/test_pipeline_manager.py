"""Tests for PipelineManager — DAG execution, retries, timeouts, dependency resolution."""
import asyncio
import pytest

from src.core.pipeline_manager import PipelineManager, PipelineStage, StageStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok_handler(value):
    async def h(ctx):
        ctx["__results__"][f"_side_{value}"] = value
        return {"value": value}
    return h

def _fail_handler(msg="boom"):
    async def h(ctx):
        raise RuntimeError(msg)
    return h

def _slow_handler(seconds=10):
    async def h(ctx):
        await asyncio.sleep(seconds)
        return {"done": True}
    return h

def _pm():
    return PipelineManager(config={"max_parallel": 5})


# ── Dependency resolution ─────────────────────────────────────────────────────

class TestDependencyResolution:

    def test_linear_chain_resolves_in_order(self):
        pm = _pm()
        stages = [
            PipelineStage(name="a", dependencies=[]),
            PipelineStage(name="b", dependencies=["a"]),
            PipelineStage(name="c", dependencies=["b"]),
        ]
        levels = pm._resolve_order(stages)
        assert levels[0] == ["a"]
        assert levels[1] == ["b"]
        assert levels[2] == ["c"]

    def test_parallel_stages_in_same_level(self):
        pm = _pm()
        stages = [
            PipelineStage(name="root", dependencies=[]),
            PipelineStage(name="b1",   dependencies=["root"]),
            PipelineStage(name="b2",   dependencies=["root"]),
        ]
        levels = pm._resolve_order(stages)
        assert levels[0] == ["root"]
        assert set(levels[1]) == {"b1", "b2"}

    def test_circular_dependency_raises(self):
        pm = _pm()
        stages = [
            PipelineStage(name="a", dependencies=["b"]),
            PipelineStage(name="b", dependencies=["a"]),
        ]
        with pytest.raises(ValueError, match="Circular"):
            pm._resolve_order(stages)

    def test_no_dependencies_all_in_one_level(self):
        pm = _pm()
        stages = [PipelineStage(name=n, dependencies=[]) for n in ("x", "y", "z")]
        levels = pm._resolve_order(stages)
        assert len(levels) == 1
        assert set(levels[0]) == {"x", "y", "z"}


# ── Execution ─────────────────────────────────────────────────────────────────

class TestPipelineExecution:

    @pytest.mark.asyncio
    async def test_simple_pipeline_completes(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="step1", handler=_ok_handler(1), dependencies=[]),
            PipelineStage(name="step2", handler=_ok_handler(2), dependencies=["step1"]),
        ])
        run = await pm.execute("test")
        assert run.status == "completed"

    @pytest.mark.asyncio
    async def test_stage_results_in_context(self):
        pm = _pm()
        collected = {}
        async def capture(ctx):
            collected.update(ctx["__results__"])
            return {"ok": True}
        pm.define_pipeline("test", [
            PipelineStage(name="a", handler=_ok_handler("a_val"), dependencies=[]),
            PipelineStage(name="b", handler=capture, dependencies=["a"]),
        ])
        await pm.execute("test")
        assert "a" in collected
        assert collected["a"]["value"] == "a_val"

    @pytest.mark.asyncio
    async def test_failed_stage_marks_run_failed(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="bad", handler=_fail_handler(), dependencies=[], max_retries=0),
        ])
        run = await pm.execute("test")
        assert run.status == "failed"
        assert run.stages["bad"].status == StageStatus.FAILED

    @pytest.mark.asyncio
    async def test_downstream_skipped_on_upstream_failure(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="fail", handler=_fail_handler(), dependencies=[], max_retries=0),
            PipelineStage(name="after", handler=_ok_handler(1), dependencies=["fail"]),
        ])
        run = await pm.execute("test")
        assert run.stages["after"].status == StageStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_pipeline_not_found_raises(self):
        pm = _pm()
        with pytest.raises(KeyError):
            await pm.execute("nonexistent")

    @pytest.mark.asyncio
    async def test_context_passed_through(self):
        pm = _pm()
        received = {}
        async def capture(ctx):
            received["custom_key"] = ctx.get("custom_key")
            return {}
        pm.define_pipeline("test", [
            PipelineStage(name="s", handler=capture, dependencies=[]),
        ])
        await pm.execute("test", context={"custom_key": "hello"})
        assert received["custom_key"] == "hello"

    @pytest.mark.asyncio
    async def test_parallel_stages_run_concurrently(self):
        pm = _pm()
        order = []
        async def record(name, ctx):
            order.append(name)
            return {"name": name}

        pm.define_pipeline("test", [
            PipelineStage(name="root", handler=lambda ctx: record("root", ctx), dependencies=[]),
            PipelineStage(name="b1",   handler=lambda ctx: record("b1", ctx), dependencies=["root"]),
            PipelineStage(name="b2",   handler=lambda ctx: record("b2", ctx), dependencies=["root"]),
        ])
        run = await pm.execute("test")
        assert run.status == "completed"
        assert order[0] == "root"
        assert set(order[1:]) == {"b1", "b2"}

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        attempts = [0]
        async def flaky(ctx):
            attempts[0] += 1
            if attempts[0] < 2:
                raise RuntimeError("transient")
            return {"ok": True}

        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="flaky", handler=flaky, dependencies=[], max_retries=2),
        ])
        run = await pm.execute("test")
        assert run.stages["flaky"].status == StageStatus.COMPLETED
        assert attempts[0] == 2

    @pytest.mark.asyncio
    async def test_timeout_causes_failure(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(
                name="slow", handler=_slow_handler(10),
                dependencies=[], max_retries=0, timeout=0.05,
            ),
        ])
        run = await pm.execute("test")
        assert run.stages["slow"].status == StageStatus.FAILED
        assert "Timeout" in (run.stages["slow"].error or "")

    @pytest.mark.asyncio
    async def test_run_summary_structure(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="s", handler=_ok_handler(1), dependencies=[]),
        ])
        run = await pm.execute("test")
        summary = pm.get_run_summary(run.run_id)
        for key in ("run_id", "status", "duration", "stages"):
            assert key in summary

    @pytest.mark.asyncio
    async def test_no_handler_stage_still_completes(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="noop", handler=None, dependencies=[]),
        ])
        run = await pm.execute("test")
        assert run.stages["noop"].status == StageStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_duration_recorded(self):
        pm = _pm()
        pm.define_pipeline("test", [
            PipelineStage(name="s", handler=_ok_handler(1), dependencies=[]),
        ])
        run = await pm.execute("test")
        assert run.stages["s"].duration >= 0
