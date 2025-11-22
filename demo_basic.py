"""
Basic Demo - Core Quantum Signature System
===========================================
Demonstrates quantum signature, decision engine, and agent orchestration
without requiring the cryptography library.
"""

from quantum_signature import get_quantum_signature
from quantum_decision_engine import get_decision_engine, DecisionStrategy
from agent_orchestrator import get_orchestrator, AgentType
from version_manager import get_version_manager

def main():
    print("=" * 70)
    print("ARK95X QUANTUM SIGNATURE SYSTEM - BASIC DEMO")
    print("=" * 70)
    print()

    # 1. Quantum Signature
    print("1. QUANTUM SIGNATURE")
    print("-" * 70)
    sig = get_quantum_signature()
    summary = sig.get_signature_summary()

    print(f"   Genesis Hash:      {summary['genesis_hash'][:40]}...")
    print(f"   Master Seed:       {summary['master_seed']}")
    print(f"   Coordinates:       {summary['coordinates']}")
    print(f"   Geohash:           {summary['geohash']}")
    print(f"   Julian Date:       {summary['julian_date']:.2f}")
    print(f"   Solar Degree:      {summary['solar_degree']:.5f}")
    print(f"   Version:           {summary['version']}")
    print(f"   Zodiac:            {summary['zodiac']}")
    print(f"   Life Path:         {summary['life_path']} (Innovation, Freedom, Adaptability)")
    print()

    # 2. Decision Engine
    print("2. QUANTUM DECISION ENGINE")
    print("-" * 70)
    engine = get_decision_engine()

    # Test deterministic decisions
    options = ['traditional', 'fusion', 'experimental']
    choice1 = engine.make_choice(options, context="menu_test")
    choice2 = engine.make_choice(options, context="menu_test")
    print(f"   Choice (context='menu_test'):  {choice1}")
    print(f"   Repeated choice:               {choice2}")
    print(f"   Deterministic:                 {choice1 == choice2}")
    print()

    # Test innovation bias
    innovation_tests = [
        engine.should_innovate(context=f"test_{i}")
        for i in range(100)
    ]
    innovation_rate = sum(innovation_tests) / len(innovation_tests)
    print(f"   Innovation Rate (100 tests):   {innovation_rate:.1%}")
    print(f"   Life Path 5 Bias Active:       {innovation_rate > 0.45}")
    print()

    # Test different strategies
    innovative_choice = engine.make_choice(
        options,
        context="strategy_test",
        strategy=DecisionStrategy.INNOVATIVE
    )
    print(f"   INNOVATIVE strategy choice:    {innovative_choice}")
    print()

    # 3. Agent Orchestrator
    print("3. AGENT ORCHESTRATOR")
    print("-" * 70)
    orchestrator = get_orchestrator()

    print(f"   Origin Geohash:                {orchestrator.origin_geohash}")
    print()

    # Register agents
    agents = [
        orchestrator.register_agent(
            "hlm-9-alpha",
            AgentType.HLM_9,
            ['reasoning', 'language_model'],
            capacity=15
        ),
        orchestrator.register_agent(
            "crew-chef-001",
            AgentType.CREW_AI,
            ['restaurant', 'kitchen_ops'],
            capacity=10
        ),
        orchestrator.register_agent(
            "gatekeeper-001",
            AgentType.GATEKEEPER,
            ['security', 'validation'],
            capacity=20
        ),
    ]

    print(f"   Registered Agents:")
    for agent in agents:
        print(f"      - {agent.id:20s} ({agent.type.value:15s}) Geohash: {agent.geohash}")
    print()

    # Route a task
    task = {
        'id': 'task-001',
        'description': 'Process restaurant order',
        'specialization': 'restaurant',
    }

    selected_agent = orchestrator.route_task(task, required_specialization='restaurant')
    if selected_agent:
        print(f"   Task Routed To:")
        print(f"      Agent: {selected_agent.id}")
        print(f"      Type:  {selected_agent.type.value}")
        print(f"      Hash:  {selected_agent.geohash}")
    print()

    # Show stats
    stats = orchestrator.get_orchestrator_stats()
    print(f"   Orchestrator Stats:")
    print(f"      Total Agents:     {stats['total_agents']}")
    print(f"      Total Capacity:   {stats['total_capacity']}")
    print(f"      Utilization:      {stats['utilization']:.1%}")
    print()

    # 4. Version Manager
    print("4. VERSION MANAGER")
    print("-" * 70)
    vm = get_version_manager()

    version_info = vm.get_version_info()
    print(f"   Current Version:               {version_info['current']['string']}")
    print(f"   Base Version:                  {version_info['base']['string']}")
    print(f"   Derived From:")
    print(f"      Zodiac:                     {version_info['quantum_signature']['zodiac']}")
    print(f"      Solar Degree:               {version_info['quantum_signature']['solar_degree']:.5f}")
    print()

    # Test compatibility
    print(f"   Compatibility Tests:")
    print(f"      v5.18.47 (exact):           {vm.check_compatibility('v5.18.47')}")
    print(f"      >=v5.18.0 (minimum):        {vm.check_compatibility('>=v5.18.0')}")
    print(f"      ~v5.18.0 (compatible):      {vm.check_compatibility('~v5.18.0')}")
    print()

    # 5. Summary
    print("=" * 70)
    print("SYSTEM OPERATIONAL")
    print("=" * 70)
    print(f"All components anchored to quantum signature")
    print(f"Genesis: August 11, 1993, 17:23:00 - Mason City, IA")
    print(f"Version: v5.18.47 | Status: ✓ Operational")
    print("=" * 70)


if __name__ == '__main__':
    main()
