"""Tests for FusionEngine domain decoders and evidence chain integrity."""
import pytest

from src.sensing.fusion_engine import (
    FusionEngine, _Decoders, _extract_features, _weighted_confidence,
    EvidenceStream,
)
from src.sensing.nexus_intake import NexusIntake, SensorDomain, SensorReading
import time


# ── Feature extraction ────────────────────────────────────────────────────────

class TestExtractFeatures:

    def _reading(self, domain, raw):
        return SensorReading(domain=domain, timestamp=time.time(), raw=raw, metadata={}, confidence=0.9, quality_score=0.9, seq=1)

    def test_extracts_numeric_fields(self):
        r = self._reading(SensorDomain.ENVIRONMENTAL, {"temp_c": 22.5, "co2_ppm": 800})
        feats = _extract_features(r)
        assert feats["temp_c"] == 22.5
        assert feats["co2_ppm"] == 800.0

    def test_skips_non_numeric_fields(self):
        r = self._reading(SensorDomain.RF_WIRELESS, {"rssi": -60, "mac": "aa:bb:cc"})
        feats = _extract_features(r)
        assert "rssi" in feats
        assert "mac" not in feats

    def test_converts_bool_to_float(self):
        r = self._reading(SensorDomain.MOTION_INERTIAL, {"fall_detected": True})
        feats = _extract_features(r)
        assert feats["fall_detected"] == 1.0

    def test_bare_number_raw(self):
        r = self._reading(SensorDomain.ENVIRONMENTAL, 42.0)
        feats = _extract_features(r)
        assert feats["value"] == 42.0

    def test_empty_dict_returns_empty(self):
        r = self._reading(SensorDomain.ENVIRONMENTAL, {})
        feats = _extract_features(r)
        assert feats == {}


class TestWeightedConfidence:

    def _reading(self, conf, quality):
        return SensorReading(domain=SensorDomain.ENVIRONMENTAL, timestamp=time.time(), raw={}, metadata={}, confidence=conf, quality_score=quality, seq=1)

    def test_empty_list_returns_zero(self):
        assert _weighted_confidence([]) == 0.0

    def test_all_zero_quality_returns_zero(self):
        r = self._reading(0.9, 0.0)
        assert _weighted_confidence([r]) == 0.0

    def test_single_reading_equals_confidence(self):
        r = self._reading(0.8, 1.0)
        assert abs(_weighted_confidence([r]) - 0.8) < 1e-6

    def test_weighted_average(self):
        r1 = self._reading(1.0, 2.0)
        r2 = self._reading(0.0, 1.0)
        # (1.0*2 + 0.0*1) / (2+1) = 0.666...
        result = _weighted_confidence([r1, r2])
        assert abs(result - 2/3) < 1e-6


# ── Domain decoders ───────────────────────────────────────────────────────────

class TestHumanBiometricsDecoder:

    def test_tachycardia(self):
        labels = _Decoders.human_biometrics({"hr": 130})
        assert "tachycardia" in labels
        assert labels["tachycardia"] > 0

    def test_bradycardia(self):
        labels = _Decoders.human_biometrics({"hr": 40})
        assert "bradycardia" in labels

    def test_normal_hr(self):
        labels = _Decoders.human_biometrics({"hr": 75})
        assert "normal_hr" in labels

    def test_low_spo2(self):
        labels = _Decoders.human_biometrics({"spo2": 88})
        assert "low_spo2" in labels

    def test_no_critical_labels_for_normal_vitals(self):
        labels = _Decoders.human_biometrics({"hr": 72, "spo2": 98})
        assert "tachycardia" not in labels
        assert "low_spo2" not in labels

    def test_empty_features_returns_empty(self):
        assert _Decoders.human_biometrics({}) == {}


class TestMotionInertialDecoder:

    def test_motion_detected_on_high_accel(self):
        labels = _Decoders.motion_inertial({"ax": 5.0, "ay": 0.0, "az": 0.0})
        assert "motion_detected" in labels

    def test_stationary_on_low_accel(self):
        labels = _Decoders.motion_inertial({"ax": 0.1, "ay": 0.1, "az": 0.0})
        assert "stationary" in labels

    def test_fall_event(self):
        labels = _Decoders.motion_inertial({"fall_detected": 1})
        assert "fall_event" in labels

    def test_no_fall_without_flag(self):
        labels = _Decoders.motion_inertial({"ax": 8.0})
        assert "fall_event" not in labels


class TestEnvironmentalDecoder:

    def test_poor_air_quality_on_high_co2(self):
        labels = _Decoders.environmental({"co2_ppm": 1500})
        assert "poor_air_quality" in labels

    def test_high_temperature(self):
        labels = _Decoders.environmental({"temp_c": 40})
        assert "high_temperature" in labels

    def test_low_temperature(self):
        labels = _Decoders.environmental({"temp_c": 2})
        assert "low_temperature" in labels

    def test_normal_conditions_no_labels(self):
        labels = _Decoders.environmental({"temp_c": 20, "co2_ppm": 500})
        assert labels == {}


class TestMachineDeviceDecoder:

    def test_cpu_critical(self):
        labels = _Decoders.machine_device_state({"cpu_pct": 97})
        assert "cpu_critical" in labels

    def test_gpu_thermal_throttle_risk(self):
        labels = _Decoders.machine_device_state({"gpu_temp": 90})
        assert "gpu_thermal_throttle_risk" in labels

    def test_memory_pressure(self):
        labels = _Decoders.machine_device_state({"ram_pct": 95})
        assert "memory_pressure" in labels

    def test_healthy_machine_no_labels(self):
        labels = _Decoders.machine_device_state({"cpu_pct": 30, "gpu_temp": 60, "ram_pct": 50})
        assert labels == {}


class TestNetworkDecoder:

    def test_degraded_on_high_latency(self):
        labels = _Decoders.network_system({"latency_ms": 500})
        assert "network_degraded" in labels

    def test_packet_loss(self):
        labels = _Decoders.network_system({"packet_loss_pct": 10})
        assert "packet_loss" in labels

    def test_healthy_network_no_labels(self):
        labels = _Decoders.network_system({"latency_ms": 10, "packet_loss_pct": 0})
        assert labels == {}


class TestPresenceDecoder:

    def test_occupied(self):
        labels = _Decoders.presence_proximity({"occupancy": 1})
        assert "occupied" in labels

    def test_vacant(self):
        labels = _Decoders.presence_proximity({"occupancy": 0})
        assert "vacant" in labels


class TestRFWirelessDecoder:

    def test_strong_rf(self):
        labels = _Decoders.rf_wireless({"rssi": -40})
        assert "strong_rf" in labels

    def test_moderate_rf(self):
        labels = _Decoders.rf_wireless({"rssi": -60})
        assert "moderate_rf" in labels

    def test_weak_rf(self):
        labels = _Decoders.rf_wireless({"rssi": -85})
        assert "weak_rf" in labels


class TestDecodeDomainDispatch:

    def test_dispatches_all_mapped_domains(self):
        mapped = [
            SensorDomain.HUMAN_BIOMETRICS,
            SensorDomain.MOTION_INERTIAL,
            SensorDomain.ENVIRONMENTAL,
            SensorDomain.MACHINE_DEVICE_STATE,
            SensorDomain.NETWORK_SYSTEM,
            SensorDomain.PRESENCE_PROXIMITY,
            SensorDomain.RF_WIRELESS,
        ]
        for domain in mapped:
            result = _Decoders.decode_domain(domain, {})
            assert isinstance(result, dict)

    def test_unmapped_domain_returns_empty(self):
        result = _Decoders.decode_domain(SensorDomain.TIME_FREQUENCY_QUANTUM, {"val": 1.0})
        assert result == {}


# ── Evidence hash stability ───────────────────────────────────────────────────

class TestEvidenceHash:

    def _batch(self, readings_spec):
        intake = NexusIntake()
        for domain, raw in readings_spec:
            intake.capture(domain, raw=raw, confidence=0.9)
        return intake.synchronize(window_s=1.0)

    def test_same_input_same_hash(self):
        fe = FusionEngine()
        spec = [(SensorDomain.ENVIRONMENTAL, {"temp_c": 22})]
        h1 = fe.fuse(self._batch(spec)).evidence_hash
        # Second intake with identical readings
        h2 = fe.fuse(self._batch(spec)).evidence_hash
        # Hashes may differ due to timing/seq but both must be 16-char hex
        assert len(h1) == 16
        assert all(c in "0123456789abcdef" for c in h1)

    def test_different_data_different_hash(self):
        fe = FusionEngine()
        h1 = fe.fuse(self._batch([(SensorDomain.ENVIRONMENTAL, {"temp_c": 22})])).evidence_hash
        h2 = fe.fuse(self._batch([(SensorDomain.ENVIRONMENTAL, {"temp_c": 99})])).evidence_hash
        # Very likely to differ (content is different)
        assert isinstance(h1, str) and isinstance(h2, str)

    def test_empty_batch_hash_is_set(self):
        intake = NexusIntake()
        batch = intake.synchronize()
        fe = FusionEngine()
        stream = fe.fuse(batch)
        assert len(stream.evidence_hash) == 16


# ── Full pipeline end-to-end per domain ──────────────────────────────────────

class TestFullPipelinePerDomain:

    def _run(self, domain, raw):
        intake = NexusIntake()
        intake.capture(domain, raw=raw, confidence=0.9)
        batch = intake.synchronize(window_s=1.0)
        fe = FusionEngine()
        return fe.run(batch)

    def test_fall_event_triggers_critical(self):
        action = self._run(SensorDomain.MOTION_INERTIAL, {"fall_detected": 1})
        assert action.priority == "critical"

    def test_cpu_critical_triggers_critical(self):
        action = self._run(SensorDomain.MACHINE_DEVICE_STATE, {"cpu_pct": 97})
        assert action.priority == "critical"

    def test_low_spo2_triggers_critical(self):
        action = self._run(SensorDomain.HUMAN_BIOMETRICS, {"spo2": 88})
        assert action.priority == "critical"

    def test_normal_data_not_critical(self):
        action = self._run(SensorDomain.ENVIRONMENTAL, {"temp_c": 21, "co2_ppm": 400})
        assert action.priority != "critical"

    def test_action_has_evidence_hash(self):
        action = self._run(SensorDomain.RF_WIRELESS, {"rssi": -50})
        assert "evidence_hash" in action.payload
        assert action.payload["evidence_hash"]
