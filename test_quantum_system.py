"""
Comprehensive Test Suite for Quantum Signature System
======================================================
Tests all components of the ARK95X Omnikernel Orchestrator.
"""

import pytest
from datetime import datetime

from quantum_signature import get_quantum_signature, QuantumSignature
from quantum_decision_engine import get_decision_engine, DecisionStrategy
from agent_orchestrator import get_orchestrator, AgentType, AgentStatus
from quantum_crypto import get_quantum_crypto
from version_manager import get_version_manager, ReleaseChannel, Version
from omnikernel import get_omnikernel, SystemStatus


class TestQuantumSignature:
    """Test quantum signature core functionality."""

    def test_genesis_hash(self):
        """Test genesis hash generation."""
        sig = get_quantum_signature()
        assert sig.genesis_hash is not None
        assert len(sig.genesis_hash) == 64  # SHA256 hex

    def test_temporal_anchor(self):
        """Test temporal anchor."""
        sig = get_quantum_signature()
        assert sig.get_master_seed() == 745102980

    def test_spatial_coordinates(self):
        """Test spatial coordinates."""
        sig = get_quantum_signature()
        lat, lon = sig.get_coordinates()
        assert lat == pytest.approx(41.1936, rel=1e-4)
        assert lon == pytest.approx(-93.2008, rel=1e-4)

    def test_solar_degree(self):
        """Test solar degree."""
        sig = get_quantum_signature()
        assert sig.get_solar_degree() == pytest.approx(18.78333, rel=1e-5)

    def test_life_path(self):
        """Test life path calculation."""
        sig = get_quantum_signature()
        assert sig.get_life_path() == 5

    def test_geohash_generation(self):
        """Test geohash generation."""
        sig = get_quantum_signature()
        geohash = sig.get_geohash(precision=8)
        assert len(geohash) == 8
        assert all(c in "0123456789bcdefghjkmnpqrstuvwxyz" for c in geohash)

    def test_julian_date(self):
        """Test Julian date calculation."""
        sig = get_quantum_signature()
        julian = sig.get_julian_date()
        assert julian > 2449000  # Reasonable Julian date for 1993

    def test_version_identifier(self):
        """Test version identifier from solar degree."""
        sig = get_quantum_signature()
        version = sig.get_version_identifier()
        assert version == "v5.18.78"  # Leo=5, 18°, 78 from decimal

    def test_key_derivation(self):
        """Test key derivation."""
        sig = get_quantum_signature()
        key1 = sig.derive_key("test_purpose")
        key2 = sig.derive_key("test_purpose")
        key3 = sig.derive_key("different_purpose")

        # Same purpose = same key
        assert key1 == key2
        # Different purpose = different key
        assert key1 != key3


class TestQuantumDecisionEngine:
    """Test quantum decision engine."""

    def test_deterministic_choice(self):
        """Test that choices are deterministic with same context."""
        engine = get_decision_engine()
        options = ['a', 'b', 'c', 'd', 'e']

        choice1 = engine.make_choice(options, context="test_context")
        choice2 = engine.make_choice(options, context="test_context")

        assert choice1 == choice2  # Deterministic

    def test_different_contexts(self):
        """Test that different contexts can yield different results."""
        engine = get_decision_engine()
        options = ['a', 'b', 'c', 'd', 'e']

        choices = set()
        for i in range(10):
            choice = engine.make_choice(options, context=f"context_{i}")
            choices.add(choice)

        # Should have some variety across different contexts
        assert len(choices) > 1

    def test_weighted_decision(self):
        """Test weighted decision making."""
        engine = get_decision_engine()
        outcomes = {
            'option_a': 0.8,
            'option_b': 0.1,
            'option_c': 0.1,
        }

        # Make many decisions
        results = {}
        for i in range(100):
            choice = engine.make_weighted_decision(outcomes, context=f"weighted_{i}")
            results[choice] = results.get(choice, 0) + 1

        # Option A should be chosen most often (but not 100% due to randomness)
        assert results.get('option_a', 0) > results.get('option_b', 0)

    def test_innovation_bias(self):
        """Test Life Path 5 innovation bias."""
        engine = get_decision_engine()

        # Test many innovation decisions
        innovate_count = sum(
            1 for i in range(100)
            if engine.should_innovate(threshold=0.5, context=f"innovation_test_{i}")
        )

        # With Life Path 5 bias, should have higher innovation rate
        assert innovate_count > 40  # More than 40% innovation

    def test_score_evaluation(self):
        """Test score evaluation with quantum perturbation."""
        engine = get_decision_engine()
        factors = {
            'quality': 0.8,
            'speed': 0.6,
            'cost': 0.7,
        }

        score = engine.evaluate_score(factors, min_score=0, max_score=100)

        # Score should be reasonable
        assert 0 <= score <= 100
        assert 60 <= score <= 80  # Around average of factors


class TestAgentOrchestrator:
    """Test agent orchestration system."""

    def test_agent_registration(self):
        """Test agent registration."""
        orchestrator = get_orchestrator()

        agent = orchestrator.register_agent(
            agent_id="test_agent_001",
            agent_type=AgentType.CREW_AI,
            specializations=['test'],
            capacity=10
        )

        assert agent.id == "test_agent_001"
        assert agent.type == AgentType.CREW_AI
        assert agent.status == AgentStatus.IDLE
        assert agent.current_load == 0

    def test_task_routing(self):
        """Test task routing to agents."""
        orchestrator = get_orchestrator()

        # Register test agent
        orchestrator.register_agent(
            agent_id="test_router_001",
            agent_type=AgentType.CREW_AI,
            specializations=['routing_test'],
            capacity=5
        )

        # Route task
        task = {
            'id': 'test_task_001',
            'description': 'Test task',
        }

        agent = orchestrator.route_task(task, required_specialization='routing_test')

        assert agent is not None
        assert agent.id == "test_router_001"

    def test_task_assignment(self):
        """Test task assignment and load tracking."""
        orchestrator = get_orchestrator()

        agent = orchestrator.register_agent(
            agent_id="test_load_001",
            agent_type=AgentType.CLONE,
            specializations=['load_test'],
            capacity=3
        )

        task = {'id': 'task_1'}

        # Assign task
        success = orchestrator.assign_task(agent, task)
        assert success
        assert agent.current_load == 1

        # Release task
        orchestrator.release_task(agent)
        assert agent.current_load == 0

    def test_geohash_proximity(self):
        """Test geohash proximity calculation."""
        orchestrator = get_orchestrator()

        # Same geohash = perfect proximity
        proximity = orchestrator._calculate_geohash_proximity("9zpgbn8v", "9zpgbn8v")
        assert proximity == 1.0

        # Completely different = low proximity
        proximity = orchestrator._calculate_geohash_proximity("9zpgbn8v", "abc12345")
        assert proximity < 0.5


class TestQuantumCrypto:
    """Test quantum cryptography system."""

    def test_key_derivation(self):
        """Test key derivation from Julian date."""
        crypto = get_quantum_crypto()

        key1 = crypto.derive_key("test_purpose")
        key2 = crypto.derive_key("test_purpose")
        key3 = crypto.derive_key("other_purpose")

        # Same purpose = same key
        assert key1 == key2
        # Different purpose = different key
        assert key1 != key3

    def test_encryption_decryption(self):
        """Test encryption and decryption."""
        crypto = get_quantum_crypto()

        plaintext = "Secret restaurant recipe"
        purpose = "recipe_vault"

        # Encrypt
        encrypted = crypto.encrypt_string(plaintext, purpose)
        assert encrypted != plaintext

        # Decrypt
        decrypted = crypto.decrypt_string(encrypted, purpose)
        assert decrypted == plaintext

    def test_wrong_purpose_fails(self):
        """Test that wrong purpose fails decryption."""
        crypto = get_quantum_crypto()

        plaintext = "Secret data"
        encrypted = crypto.encrypt_string(plaintext, "purpose_a")

        # Try to decrypt with wrong purpose
        with pytest.raises(Exception):
            crypto.decrypt_string(encrypted, "purpose_b")

    def test_secure_token_generation(self):
        """Test secure token generation."""
        crypto = get_quantum_crypto()

        token1 = crypto.generate_secure_token(length=32)
        token2 = crypto.generate_secure_token(length=32)

        # Should be different
        assert token1 != token2
        # Should be correct length (hex encoded)
        assert len(token1) == 64  # 32 bytes = 64 hex chars

    def test_signature_verification(self):
        """Test message signing and verification."""
        crypto = get_quantum_crypto()

        message = b"Important message"
        signature = crypto.create_signature(message)

        # Verify correct signature
        assert crypto.verify_signature(message, signature)

        # Wrong message fails
        assert not crypto.verify_signature(b"Wrong message", signature)


class TestVersionManager:
    """Test version management system."""

    def test_base_version(self):
        """Test base version derivation from solar degree."""
        vm = get_version_manager()

        base = vm.base_version
        assert base.major == 5  # Leo
        assert base.minor == 18  # Degree
        assert base.patch == 47  # Minutes

    def test_version_string(self):
        """Test version string formatting."""
        vm = get_version_manager()
        version_str = vm.get_version_string()

        assert version_str.startswith("v5.18.47")

    def test_version_bump(self):
        """Test version bumping."""
        vm = get_version_manager()

        current = vm.get_current_version()
        initial_patch = current.patch

        # Bump patch
        new_version = vm.create_release(version_bump="patch")

        assert new_version.patch == initial_patch + 1

    def test_version_comparison(self):
        """Test version comparison."""
        v1 = Version(major=5, minor=18, patch=47)
        v2 = Version(major=5, minor=18, patch=48)
        v3 = Version(major=5, minor=19, patch=0)

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3

    def test_compatibility_check(self):
        """Test version compatibility checking."""
        vm = get_version_manager()

        # Exact match
        assert vm.check_compatibility("v5.18.47")

        # Greater than
        assert vm.check_compatibility(">=v5.18.0")

        # Compatible minor
        assert vm.check_compatibility("~v5.18.0")


class TestOmnikernel:
    """Test main omnikernel orchestrator."""

    def test_initialization(self):
        """Test omnikernel initialization."""
        omni = get_omnikernel()

        assert omni.status in [SystemStatus.READY, SystemStatus.RUNNING]
        assert omni.signature is not None
        assert omni.decision_engine is not None

    def test_agent_initialization(self):
        """Test agent initialization through omnikernel."""
        omni = get_omnikernel()

        configs = [
            {
                'id': 'omni_test_001',
                'type': 'crew_ai',
                'specializations': ['test'],
                'capacity': 5,
            }
        ]

        agents = omni.initialize_agents(configs)

        assert len(agents) == 1
        assert agents[0].id == 'omni_test_001'

    def test_task_processing(self):
        """Test task processing through omnikernel."""
        omni = get_omnikernel()

        # Initialize agent
        omni.initialize_agents([{
            'id': 'omni_processor_001',
            'type': 'crew_ai',
            'specializations': ['processing'],
            'capacity': 10,
        }])

        # Process task
        task = {
            'id': 'omni_task_001',
            'description': 'Test processing',
            'specialization': 'processing',
            'approach_options': ['standard', 'fast'],
        }

        result = omni.process_task(task)

        assert result['success']
        assert 'agent' in result
        assert 'approach' in result

    def test_encryption_decryption(self):
        """Test encryption through omnikernel."""
        omni = get_omnikernel()

        data = "Sensitive restaurant data"
        purpose = "restaurant_ops"

        encrypted = omni.encrypt_data(data, purpose)
        decrypted = omni.decrypt_data(encrypted, purpose)

        assert decrypted == data

    def test_system_status(self):
        """Test system status reporting."""
        omni = get_omnikernel()

        status = omni.get_system_status()

        assert 'status' in status
        assert 'version' in status
        assert 'quantum_signature' in status
        assert 'decision_engine' in status

    def test_health_check(self):
        """Test health check endpoint."""
        omni = get_omnikernel()

        health = omni.get_health_check()

        assert 'status' in health
        assert 'version' in health
        assert 'uptime' in health

    def test_innovation_decision(self):
        """Test innovation decision through omnikernel."""
        omni = get_omnikernel()

        # Make multiple innovation decisions
        decisions = [omni.should_innovate(f"context_{i}") for i in range(20)]

        # Should have some True values due to Life Path 5 bias
        assert any(decisions)


def test_singleton_consistency():
    """Test that singletons return same instance."""
    sig1 = get_quantum_signature()
    sig2 = get_quantum_signature()
    assert sig1 is sig2

    engine1 = get_decision_engine()
    engine2 = get_decision_engine()
    assert engine1 is engine2

    orch1 = get_orchestrator()
    orch2 = get_orchestrator()
    assert orch1 is orch2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=.', '--cov-report=term-missing'])
