"""Tests for the NEXUS sensing bridge and LessonLearner."""
import json
import pytest
import tempfile
from pathlib import Path

from src.sensing.nexus_intake import NexusIntake, SensorDomain
from src.sensing.nexus_bridge import ingest_sensing_result
from src.agents.lesson_learner import LessonLearner


# ── NexusBridge ───────────────────────────────────────────────────────────────

class TestNexusBridge:

    def _sensing_result(self, presence="occupied", motion=True, bpm=14.5, rssi=-55.0, confidence=0.85):
        return {
            "last_analysis": {
                "presence": presence,
                "motion_detected": motion,
                "breathing_rate_bpm": bpm,
                "rssi": rssi,
                "variance": 0.003,
                "presence_confidence": confidence,
            }
        }

    def test_ingest_occupied_populates_four_domains(self):
        intake = NexusIntake()
        n = ingest_sensing_result(intake, self._sensing_result())
        assert n == 4

    def test_ingest_no_last_analysis_returns_zero(self):
        intake = NexusIntake()
        n = ingest_sensing_result(intake, {})
        assert n == 0

    def test_rf_wireless_captured(self):
        intake = NexusIntake()
        ingest_sensing_result(intake, self._sensing_result())
        batch = intake.synchronize(window_s=1.0)
        domains = [r.domain for r in batch.readings]
        assert SensorDomain.RF_WIRELESS in domains

    def test_presence_proximity_captured(self):
        intake = NexusIntake()
        ingest_sensing_result(intake, self._sensing_result())
        batch = intake.synchronize(window_s=1.0)
        domains = [r.domain for r in batch.readings]
        assert SensorDomain.PRESENCE_PROXIMITY in domains

    def test_human_biometrics_captured_when_bpm_positive(self):
        intake = NexusIntake()
        ingest_sensing_result(intake, self._sensing_result(bpm=16.0))
        batch = intake.synchronize(window_s=1.0)
        domains = [r.domain for r in batch.readings]
        assert SensorDomain.HUMAN_BIOMETRICS in domains

    def test_human_biometrics_skipped_when_bpm_zero(self):
        intake = NexusIntake()
        n = ingest_sensing_result(intake, self._sensing_result(bpm=0.0))
        assert n == 3  # RF + MOTION + PRESENCE, no BIOMETRICS

    def test_motion_inertial_captured(self):
        intake = NexusIntake()
        ingest_sensing_result(intake, self._sensing_result(motion=False))
        batch = intake.synchronize(window_s=1.0)
        domains = [r.domain for r in batch.readings]
        assert SensorDomain.MOTION_INERTIAL in domains

    def test_readings_feed_into_fusion(self):
        from src.sensing.fusion_engine import FusionEngine
        intake = NexusIntake()
        ingest_sensing_result(intake, self._sensing_result())
        batch = intake.synchronize(window_s=1.0)
        fe = FusionEngine()
        action = fe.run(batch)
        assert action.priority in ("critical", "high", "normal", "low")


# ── LessonLearner ─────────────────────────────────────────────────────────────

def _write_lessons(path: Path, lessons):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for l in lessons:
            f.write(json.dumps(l) + "\n")


class TestLessonLearner:

    def _make_lesson(self, objective, tasks):
        return {"mission_id": "abc", "objective": objective, "sub_tasks": tasks, "timestamp": 1.0}

    def test_empty_file_returns_zero_lessons(self):
        with tempfile.TemporaryDirectory() as d:
            ll = LessonLearner(path=Path(d) / "nonexistent.jsonl")
            assert ll.summary()["lessons_loaded"] == 0

    def test_loads_lessons_from_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lessons.jsonl"
            lessons = [
                self._make_lesson("embed test", [
                    {"id": "t1", "type": "embedding", "status": "completed", "duration_s": 3.0},
                ]),
            ]
            _write_lessons(p, lessons)
            ll = LessonLearner(path=p)
            assert ll.summary()["lessons_loaded"] == 1

    def test_type_weights_reflect_success_rate(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lessons.jsonl"
            lessons = [
                self._make_lesson("run embedding", [
                    {"id": f"t{i}", "type": "embedding", "status": "completed", "duration_s": 2.0}
                ])
                for i in range(5)
            ]
            _write_lessons(p, lessons)
            ll = LessonLearner(path=p)
            weights = ll.type_weights("run embedding test")
            assert "embedding" in weights
            assert weights["embedding"] > 0.9

    def test_recent_failures_returns_low_success_types(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lessons.jsonl"
            lessons = [
                self._make_lesson("docker build", [
                    {"id": f"t{i}", "type": "docker", "status": "failed", "duration_s": 0.5}
                ])
                for i in range(4)
            ]
            _write_lessons(p, lessons)
            ll = LessonLearner(path=p)
            failures = ll.recent_failures()
            assert "docker" in failures

    def test_suggest_priority_delta_fast_tasks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lessons.jsonl"
            lessons = [
                self._make_lesson("local script", [
                    {"id": f"t{i}", "type": "local", "status": "completed", "duration_s": 1.0}
                ])
                for i in range(5)
            ]
            _write_lessons(p, lessons)
            ll = LessonLearner(path=p)
            delta = ll.suggest_priority_delta("run local script")
            assert delta <= 0  # fast tasks get a priority boost (negative delta)

    def test_refresh_picks_up_new_data(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lessons.jsonl"
            ll = LessonLearner(path=p)
            assert ll.summary()["lessons_loaded"] == 0
            _write_lessons(p, [
                self._make_lesson("test", [{"id": "t1", "type": "local", "status": "completed", "duration_s": 1.0}])
            ])
            ll.refresh()
            assert ll.summary()["lessons_loaded"] == 1

    def test_summary_structure(self):
        with tempfile.TemporaryDirectory() as d:
            ll = LessonLearner(path=Path(d) / "x.jsonl")
            s = ll.summary()
            for key in ("lessons_loaded", "type_stats", "overall_success_rate", "recent_failures"):
                assert key in s
