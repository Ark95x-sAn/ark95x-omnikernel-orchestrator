"""Tests for src/core/pipeline_learn.py and PipelineManager integration."""
import asyncio
import pytest
from src.core.pipeline_learn import PipelineLearner, StageProfile, MIN_SAMPLES, TIMEOUT_SAFETY
from src.core.pipeline_manager import PipelineManager, PipelineStage, StageStatus


# ── StageProfile unit tests ───────────────────────────────────────────────────

class TestStageProfile:
    def _filled(self, n=MIN_SAMPLES):
        p = StageProfile(name="s")
        for i in range(n):
            p.durations.append(float(i + 1))
            p.outcomes.append(1.0)
            p.retries.append(0.0)
        return p

    def test_mean_duration(self):
        p = self._filled(5)
        assert p.mean_duration() == pytest.approx(3.0)

    def test_p95_duration(self):
        p = StageProfile(name="s")
        for v in [1.0, 2.0, 3.0, 4.0, 100.0]:
            p.durations.append(v)
        assert p.p95_duration() > 4.0

    def test_success_rate_all_pass(self):
        p = self._filled()
        assert p.success_rate() == pytest.approx(1.0)

    def test_success_rate_mixed(self):
        p = StageProfile(name="s")
        for v in [1.0, 1.0, 0.0, 1.0, 0.0]:
            p.outcomes.append(v)
        assert p.success_rate() == pytest.approx(0.6)

    def test_recommended_timeout_requires_min_samples(self):
        p = StageProfile(name="s")
        for _ in range(MIN_SAMPLES - 1):
            p.durations.append(1.0)
        assert p.recommended_timeout() is None

    def test_recommended_timeout_value(self):
        p = self._filled(MIN_SAMPLES)
        rt = p.recommended_timeout()
        assert rt is not None
        assert rt == pytest.approx(p.p95_duration() * TIMEOUT_SAFETY, rel=0.01)

    def test_zscore_duration_no_std(self):
        p = StageProfile(name="s")
        for _ in range(MIN_SAMPLES):
            p.durations.append(5.0)
        assert p.zscore_duration(5.0) == 0.0

    def test_snapshot_keys(self):
        p = self._filled()
        snap = p.snapshot()
        for key in ("name", "samples", "mean_duration_s", "p95_duration_s",
                    "success_rate", "recommended_timeout_s"):
            assert key in snap


# ── PipelineLearner unit tests ────────────────────────────────────────────────

class TestPipelineLearner:
    def test_observe_creates_profile(self):
        l = PipelineLearner()
        l.observe("ingest", 1.0, True)
        assert l.stage("ingest") is not None

    def test_no_alert_for_low_sample_count(self):
        l = PipelineLearner()
        for _ in range(MIN_SAMPLES - 1):
            l.observe("ingest", 1.0, True)
        assert l.recent_alerts() == []

    def test_failure_alert_triggered(self):
        l = PipelineLearner()
        # establish high pass-rate baseline
        for _ in range(40):
            l.observe("stage_x", 1.0, True)
        # sudden run of failures should trigger drift alert
        for _ in range(10):
            l.observe("stage_x", 1.0, False)
        alerts = [a for a in l.recent_alerts() if a["kind"] == "failure_rate_drift"]
        assert len(alerts) > 0

    def test_duration_spike_alert(self):
        l = PipelineLearner()
        for _ in range(20):
            l.observe("stage_y", 1.0, True)
        l.observe("stage_y", 999.0, True)  # enormous spike
        alerts = [a for a in l.recent_alerts() if a["kind"] == "duration_spike"]
        assert len(alerts) > 0

    def test_recommendations_timeout(self):
        l = PipelineLearner()
        for _ in range(MIN_SAMPLES):
            l.observe("etl", 2.0, True)
        recs = l.recommendations()
        timeout_recs = [r for r in recs if r["type"] == "timeout"]
        assert len(timeout_recs) == 1
        assert timeout_recs[0]["stage"] == "etl"
        assert timeout_recs[0]["recommended_timeout_s"] > 0

    def test_recommendations_reliability(self):
        l = PipelineLearner()
        for _ in range(MIN_SAMPLES):
            l.observe("flaky", 1.0, False)
        recs = l.recommendations()
        rel_recs = [r for r in recs if r["type"] == "reliability"]
        assert len(rel_recs) == 1

    def test_bottlenecks_ordering(self):
        l = PipelineLearner()
        for _ in range(MIN_SAMPLES):
            l.observe("fast", 0.1, True)
            l.observe("slow", 10.0, True)
        bots = l.bottlenecks()
        assert bots[0]["name"] == "slow"
        assert bots[1]["name"] == "fast"

    def test_summary_structure(self):
        l = PipelineLearner()
        s = l.summary()
        assert "tracked_stages" in s
        assert "total_alerts" in s
        assert "bottlenecks" in s
        assert "recommendations" in s


# ── PipelineManager integration tests ────────────────────────────────────────

class TestPipelineManagerIntegration:
    @pytest.mark.asyncio
    async def test_learner_receives_observations(self):
        learner = PipelineLearner()
        mgr = PipelineManager(learner=learner)

        async def ok_handler(ctx):
            return "ok"

        mgr.define_pipeline("test_pipe", [
            PipelineStage(name="step_a", handler=ok_handler),
            PipelineStage(name="step_b", handler=ok_handler, dependencies=["step_a"]),
        ])

        await mgr.execute("test_pipe")

        assert learner.stage("step_a") is not None
        assert learner.stage("step_b") is not None
        assert learner.stage("step_a").success_rate() == 1.0

    @pytest.mark.asyncio
    async def test_learner_records_failure(self):
        learner = PipelineLearner()
        mgr = PipelineManager(learner=learner)

        async def bad_handler(ctx):
            raise RuntimeError("boom")

        mgr.define_pipeline("fail_pipe", [
            PipelineStage(name="breaker", handler=bad_handler, max_retries=0),
        ])

        run = await mgr.execute("fail_pipe")
        assert run.status == "failed"

        profile = learner.stage("breaker")
        assert profile is not None
        assert profile.success_rate() == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_manager_without_learner_still_works(self):
        mgr = PipelineManager()  # no learner — must not crash

        async def handler(ctx):
            return 42

        mgr.define_pipeline("bare", [PipelineStage(name="s", handler=handler)])
        run = await mgr.execute("bare")
        assert run.status == "completed"
