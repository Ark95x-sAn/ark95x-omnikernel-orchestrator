"""Tests for the full NETWORK-95 + NEXUS-1 stack."""
import asyncio
import pytest
import time

from src.sensing.nexus_intake import NexusIntake, SensorDomain, SensorReading, SynchronizedBatch
from src.sensing.fusion_engine import (
    FusionEngine, EvidenceStream, DecodedState, VerificationResult, ActionRecommendation,
)
from src.core.mission_manager import MissionManager, MissionStatus
from src.agents.network95_agent import Network95Agent, _decompose_objective, _select_device


# ═══════════════════════════════════════════════════════════════════
# NexusIntake — CAPTURE + SYNCHRONIZE
# ═══════════════════════════════════════════════════════════════════

class TestNexusIntake:

    def test_capture_returns_reading(self):
        intake = NexusIntake()
        r = intake.capture(SensorDomain.ENVIRONMENTAL, raw={"temp_c": 22.0}, confidence=0.9)
        assert isinstance(r, SensorReading)
        assert r.domain == SensorDomain.ENVIRONMENTAL
        assert r.quality_score > 0

    def test_capture_all_24_domains(self):
        intake = NexusIntake()
        for domain in SensorDomain:
            r = intake.capture(domain, raw={"value": 1.0}, confidence=0.8)
            assert r.domain == domain

    def test_capture_drops_zero_confidence(self):
        intake = NexusIntake()
        r = intake.capture(SensorDomain.HUMAN_BIOMETRICS, raw={"hr": 70}, confidence=0.0)
        assert r.quality_score == 0.0
        assert intake.stats()["total_dropped"] == 1

    def test_capture_empty_raw_penalises_quality(self):
        intake = NexusIntake()
        r = intake.capture(SensorDomain.RADAR, raw={}, confidence=1.0)
        assert r.quality_score < 1.0

    def test_sequence_increments(self):
        intake = NexusIntake()
        r1 = intake.capture(SensorDomain.LIDAR, raw={"dist_m": 3.0})
        r2 = intake.capture(SensorDomain.LIDAR, raw={"dist_m": 3.1})
        assert r2.seq == r1.seq + 1

    def test_synchronize_returns_batch(self):
        intake = NexusIntake()
        intake.capture(SensorDomain.ENVIRONMENTAL, raw={"temp_c": 20})
        intake.capture(SensorDomain.MACHINE_DEVICE_STATE, raw={"cpu_pct": 45})
        batch = intake.synchronize(window_s=1.0)
        assert isinstance(batch, SynchronizedBatch)
        assert len(batch.readings) >= 2

    def test_synchronize_excludes_old_readings(self):
        intake = NexusIntake()
        # Manually inject a reading with an old timestamp
        r = intake.capture(SensorDomain.AUDIO_ACOUSTICS, raw={"db": 60})
        r.timestamp = time.time() - 10   # 10 seconds old
        batch = intake.synchronize(window_s=0.1)
        # The old reading should not be in the batch
        audio_readings = [x for x in batch.readings if x.domain == SensorDomain.AUDIO_ACOUSTICS]
        assert len(audio_readings) == 0

    def test_completeness_fraction(self):
        intake = NexusIntake()
        intake.capture(SensorDomain.RF_WIRELESS, raw={"rssi": -60})
        batch = intake.synchronize()
        assert 0 < batch.completeness <= 1.0

    def test_active_domains_listing(self):
        intake = NexusIntake()
        intake.capture(SensorDomain.SONAR_ACOUSTIC, raw={"dist_m": 1.0})
        assert SensorDomain.SONAR_ACOUSTIC.value in intake.active_domains()

    def test_stats_structure(self):
        intake = NexusIntake()
        s = intake.stats()
        for key in ("total_captured", "total_dropped", "active_domains", "batches_issued"):
            assert key in s


# ═══════════════════════════════════════════════════════════════════
# FusionEngine — FUSE → DECODE → VERIFY → ACT
# ═══════════════════════════════════════════════════════════════════

class TestFusionEngine:

    def _batch(self, readings=None):
        intake = NexusIntake()
        if readings:
            for domain, raw in readings:
                intake.capture(domain, raw=raw, confidence=0.9)
        else:
            intake.capture(SensorDomain.ENVIRONMENTAL, raw={"temp_c": 22, "co2_ppm": 900})
            intake.capture(SensorDomain.MACHINE_DEVICE_STATE, raw={"cpu_pct": 50, "gpu_temp": 70})
        return intake.synchronize(window_s=1.0)

    def test_fuse_returns_evidence_stream(self):
        fe = FusionEngine()
        batch = self._batch()
        stream = fe.fuse(batch)
        assert isinstance(stream, EvidenceStream)
        assert 0 <= stream.fused_confidence <= 1.0
        assert stream.evidence_hash

    def test_fuse_empty_batch(self):
        fe = FusionEngine()
        intake = NexusIntake()
        batch = intake.synchronize()
        stream = fe.fuse(batch)
        assert stream.fused_confidence == 0.0

    def test_decode_returns_state(self):
        fe = FusionEngine()
        stream = fe.fuse(self._batch())
        decoded = fe.decode(stream)
        assert isinstance(decoded, DecodedState)
        assert isinstance(decoded.state_labels, list)
        assert isinstance(decoded.narrative, str)

    def test_decode_high_cpu_label(self):
        fe = FusionEngine()
        batch = self._batch([(SensorDomain.MACHINE_DEVICE_STATE, {"cpu_pct": 95})])
        stream = fe.fuse(batch)
        decoded = fe.decode(stream)
        assert "cpu_critical" in decoded.state_labels

    def test_decode_motion_label(self):
        fe = FusionEngine()
        batch = self._batch([(SensorDomain.MOTION_INERTIAL, {"ax": 5.0, "ay": 3.0, "az": 1.0})])
        stream = fe.fuse(batch)
        decoded = fe.decode(stream)
        assert "motion_detected" in decoded.state_labels

    def test_verify_passes_with_good_data(self):
        fe = FusionEngine()
        stream = fe.fuse(self._batch())
        decoded = fe.decode(stream)
        result = fe.verify(decoded, stream)
        assert isinstance(result, VerificationResult)
        assert 0 <= result.score <= 1.0

    def test_verify_fails_low_confidence(self):
        fe = FusionEngine(criteria={"min_evidence_confidence": 0.99})
        intake = NexusIntake()
        intake.capture(SensorDomain.SENSOR_HEALTH_META, raw={"snr": 0.1}, confidence=0.1)
        batch = intake.synchronize(window_s=1.0)
        stream = fe.fuse(batch)
        decoded = fe.decode(stream)
        result = fe.verify(decoded, stream)
        assert not result.passed

    def test_act_returns_recommendation(self):
        fe = FusionEngine()
        batch = self._batch()
        stream = fe.fuse(batch)
        decoded = fe.decode(stream)
        verified = fe.verify(decoded, stream)
        action = fe.act(verified, decoded)
        assert isinstance(action, ActionRecommendation)
        assert action.priority in ("critical", "high", "normal", "low")
        assert action.action_type in ("alert", "log", "trigger_pipeline", "no_action")

    def test_act_critical_on_fall_event(self):
        fe = FusionEngine()
        batch = self._batch([(SensorDomain.MOTION_INERTIAL, {"fall_detected": 1})])
        stream = fe.fuse(batch)
        decoded = fe.decode(stream)
        verified = fe.verify(decoded, stream)
        action = fe.act(verified, decoded)
        assert action.priority == "critical"

    def test_run_one_shot(self):
        fe = FusionEngine()
        action = fe.run(self._batch())
        assert isinstance(action, ActionRecommendation)


# ═══════════════════════════════════════════════════════════════════
# MissionManager
# ═══════════════════════════════════════════════════════════════════

class TestMissionManager:

    def test_create_and_get(self):
        mm = MissionManager(persist=False)
        mid = mm.create("Test objective")
        m = mm.get(mid)
        assert m.objective == "Test objective"
        assert m.status == MissionStatus.QUEUED

    def test_start_mission(self):
        mm = MissionManager(persist=False)
        mid = mm.create("obj")
        mm.start(mid)
        m = mm.get(mid)
        assert m.status == MissionStatus.RUNNING
        assert m.started_at is not None
        assert m.stage == "intake"

    def test_update_stage_tracks_progress(self):
        mm = MissionManager(persist=False)
        mid = mm.create("obj")
        mm.start(mid)
        mm.update_stage(mid, "decompose")
        m = mm.get(mid)
        assert m.stage == "decompose"
        assert "intake" in m.stages_completed

    def test_complete_mission(self):
        mm = MissionManager(persist=False)
        mid = mm.create("obj")
        mm.start(mid)
        mm.complete(mid, result={"score": 42})
        m = mm.get(mid)
        assert m.status == MissionStatus.COMPLETE
        assert m.result["score"] == 42
        assert m.completed_at is not None

    def test_fail_mission(self):
        mm = MissionManager(persist=False)
        mid = mm.create("obj")
        mm.start(mid)
        mm.fail(mid, error="boom")
        m = mm.get(mid)
        assert m.status == MissionStatus.FAILED
        assert m.error == "boom"

    def test_queue_ordering_by_priority(self):
        mm = MissionManager(persist=False)
        mm.create("low",  priority=8)
        mm.create("high", priority=1)
        mm.create("mid",  priority=5)
        queue = mm.queue()
        assert queue[0].objective == "high"
        assert queue[-1].objective == "low"

    def test_running_list(self):
        mm = MissionManager(persist=False)
        mid1 = mm.create("a")
        mid2 = mm.create("b")
        mm.start(mid1)
        assert len(mm.running()) == 1
        mm.start(mid2)
        assert len(mm.running()) == 2

    def test_dashboard_structure(self):
        mm = MissionManager(persist=False)
        mm.create("x")
        d = mm.dashboard()
        for key in ("active_missions", "counts", "queue_depth", "running", "total"):
            assert key in d

    def test_missing_mission_raises(self):
        mm = MissionManager(persist=False)
        with pytest.raises(KeyError):
            mm.get("nonexistent")

    def test_duration_computed(self):
        mm = MissionManager(persist=False)
        mid = mm.create("dur")
        mm.start(mid)
        mm.complete(mid)
        m = mm.get(mid)
        assert m.duration_s is not None
        assert m.duration_s >= 0


# ═══════════════════════════════════════════════════════════════════
# Network95Agent — integration
# ═══════════════════════════════════════════════════════════════════

class TestNetwork95Agent:

    @pytest.fixture
    def agent(self):
        return Network95Agent(config={"persist_missions": False})

    def test_create_mission(self, agent):
        mid = agent.create_mission("Test mission")
        assert mid
        m = agent.mission_manager.get(mid)
        assert m.status == MissionStatus.QUEUED

    @pytest.mark.asyncio
    async def test_run_mission_completes(self, agent):
        mid = agent.create_mission("Run embedding test")
        result = await agent.run_mission(mid)
        assert "notify" in result
        assert result["notify"]["delta"]["status"] in ("VERIFIED", "FAILED")

    @pytest.mark.asyncio
    async def test_mission_status_after_run(self, agent):
        mid = agent.create_mission("Scan research articles")
        await agent.run_mission(mid)
        m = agent.mission_manager.get(mid)
        assert m.status in (MissionStatus.COMPLETE, MissionStatus.FAILED)

    @pytest.mark.asyncio
    async def test_learner_populated_after_run(self, agent):
        mid = agent.create_mission("Build docker image")
        await agent.run_mission(mid)
        # All 7 stages should be tracked by the learner
        assert agent.learner.summary()["tracked_stages"] == 7

    @pytest.mark.asyncio
    async def test_run_with_sensor_context(self, agent):
        mid = agent.create_mission("Verify presence detection")
        ctx = {
            "sensor_readings": [
                {
                    "domain": "presence_proximity",
                    "raw": {"occupancy": 1},
                    "metadata": {"source": "proximity_sensor"},
                    "confidence": 0.95,
                }
            ]
        }
        result = await agent.run_mission(mid, context=ctx)
        assert "execute" in result
        # The sensor label "occupied" should surface in the action
        labels = result["execute"].get("sensor_action", {}).get("labels", [])
        assert "occupied" in labels

    @pytest.mark.asyncio
    async def test_run_next_queued(self, agent):
        agent.create_mission("queued mission 1")
        result = await agent.run_next_queued()
        assert result is not None
        assert "notify" in result

    @pytest.mark.asyncio
    async def test_run_next_queued_empty(self, agent):
        result = await agent.run_next_queued()
        assert result is None

    def test_status_structure(self, agent):
        s = agent.status()
        assert s["system"] == "NETWORK-95"
        for key in ("mission_dashboard", "intake", "pipeline_learner", "devices"):
            assert key in s

    def test_device_routing(self):
        assert _select_device("embedding") == "gpu_node"
        assert _select_device("n8n") == "control_node"
        assert _select_device("voice") == "edge_device"
        assert _select_device("unknown_type") == "local"

    def test_decompose_embedding(self):
        tasks = _decompose_objective("Run embedding test for RTX")
        types = [t["type"] for t in tasks]
        assert "embedding" in types or "ollama" in types

    def test_decompose_research(self):
        tasks = _decompose_objective("Research AI papers and summarise")
        types = [t["type"] for t in tasks]
        assert "n8n" in types or "inference" in types

    def test_decompose_always_validates(self):
        tasks = _decompose_objective("Do something random")
        assert tasks[-1]["name"].lower().startswith("validate")
