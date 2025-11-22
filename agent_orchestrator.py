"""
Agent Orchestration Router
===========================
Distributed agent routing system using geohash-based spatial indexing.

Routes CrewAI agents, clones, and decision requests based on:
- Geohash proximity to quantum signature origin
- Workload distribution
- Agent specialization matching
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import hashlib

from quantum_signature import get_quantum_signature
from quantum_decision_engine import get_decision_engine


class AgentType(Enum):
    """Types of agents in the orchestrator."""
    CREW_AI = "crew_ai"  # CrewAI intelligent agents
    CLONE = "clone"  # System clones for parallel processing
    GATEKEEPER = "gatekeeper"  # Request validation and routing
    DECISION_ROUTER = "decision_router"  # Decision routing logic
    HLM_9 = "hlm_9"  # High-Level Model agents


class AgentStatus(Enum):
    """Agent operational status."""
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"


@dataclass
class Agent:
    """Agent representation in the orchestrator."""
    id: str
    type: AgentType
    status: AgentStatus
    specializations: List[str]
    capacity: int  # Max concurrent tasks
    current_load: int  # Current task count
    geohash: str  # Agent's spatial hash (for distributed routing)
    metadata: Dict[str, Any]

    def can_accept_task(self) -> bool:
        """Check if agent can accept new task."""
        return (
            self.status not in [AgentStatus.OFFLINE, AgentStatus.OVERLOADED]
            and self.current_load < self.capacity
        )

    def get_load_factor(self) -> float:
        """Get current load as percentage of capacity."""
        if self.capacity == 0:
            return 1.0
        return self.current_load / self.capacity


class AgentOrchestrator:
    """
    Main orchestration system for agent distribution and routing.

    Uses quantum signature geohash as the spatial anchor point for
    distributed agent placement and routing decisions.
    """

    def __init__(self):
        """Initialize orchestrator with quantum signature."""
        self.signature = get_quantum_signature()
        self.decision_engine = get_decision_engine()

        # Central geohash from quantum signature
        self.origin_geohash = self.signature.get_geohash(precision=8)

        # Agent registry
        self.agents: Dict[str, Agent] = {}

        # Task queue
        self.task_queue: List[Dict[str, Any]] = []

    def register_agent(
        self,
        agent_id: str,
        agent_type: AgentType,
        specializations: List[str],
        capacity: int = 10,
        geohash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Agent:
        """
        Register a new agent in the orchestrator.

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent
            specializations: List of agent capabilities
            capacity: Maximum concurrent tasks
            geohash: Optional geohash (auto-generated if not provided)
            metadata: Additional agent metadata

        Returns:
            Registered Agent instance
        """
        # Auto-generate geohash if not provided
        if geohash is None:
            # Use agent_id to derive a geohash variant from origin
            geohash = self._derive_agent_geohash(agent_id)

        agent = Agent(
            id=agent_id,
            type=agent_type,
            status=AgentStatus.IDLE,
            specializations=specializations,
            capacity=capacity,
            current_load=0,
            geohash=geohash,
            metadata=metadata or {}
        )

        self.agents[agent_id] = agent
        return agent

    def route_task(
        self,
        task: Dict[str, Any],
        required_specialization: Optional[str] = None,
        preferred_agent_type: Optional[AgentType] = None
    ) -> Optional[Agent]:
        """
        Route task to best available agent.

        Routing considers:
        1. Agent specialization match
        2. Current load
        3. Geohash proximity to origin
        4. Agent type preference

        Args:
            task: Task dictionary with requirements
            required_specialization: Required agent capability
            preferred_agent_type: Preferred type of agent

        Returns:
            Selected Agent or None if no suitable agent
        """
        # Filter available agents
        available = [
            agent for agent in self.agents.values()
            if agent.can_accept_task()
        ]

        if not available:
            return None

        # Filter by specialization if required
        if required_specialization:
            available = [
                agent for agent in available
                if required_specialization in agent.specializations
            ]

        if not available:
            return None

        # Filter by preferred type
        if preferred_agent_type:
            preferred = [a for a in available if a.type == preferred_agent_type]
            if preferred:
                available = preferred

        # Score agents based on multiple factors
        scored_agents = []
        for agent in available:
            score = self._calculate_agent_score(agent, task)
            scored_agents.append((agent, score))

        # Sort by score (higher is better)
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # Use quantum decision engine for final selection
        # This adds innovation/adaptability to routing
        top_candidates = scored_agents[:min(3, len(scored_agents))]

        if len(top_candidates) == 1:
            return top_candidates[0][0]

        # Weight by scores for quantum choice
        agents_list = [a for a, _ in top_candidates]
        weights = [score for _, score in top_candidates]

        selected = self.decision_engine.make_choice(
            agents_list,
            context=f"task_routing_{task.get('id', 'unknown')}",
            weights=weights
        )

        return selected

    def assign_task(self, agent: Agent, task: Dict[str, Any]) -> bool:
        """
        Assign task to agent.

        Args:
            agent: Target agent
            task: Task to assign

        Returns:
            True if successfully assigned
        """
        if not agent.can_accept_task():
            return False

        agent.current_load += 1

        # Update status based on load
        load_factor = agent.get_load_factor()
        if load_factor >= 1.0:
            agent.status = AgentStatus.OVERLOADED
        elif load_factor >= 0.7:
            agent.status = AgentStatus.BUSY
        else:
            agent.status = AgentStatus.IDLE

        return True

    def release_task(self, agent: Agent) -> None:
        """
        Release a task from agent, freeing capacity.

        Args:
            agent: Agent to release task from
        """
        if agent.current_load > 0:
            agent.current_load -= 1

        # Update status
        load_factor = agent.get_load_factor()
        if load_factor >= 1.0:
            agent.status = AgentStatus.OVERLOADED
        elif load_factor >= 0.7:
            agent.status = AgentStatus.BUSY
        else:
            agent.status = AgentStatus.IDLE

    def _derive_agent_geohash(self, agent_id: str) -> str:
        """
        Derive geohash for agent based on origin and agent ID.

        Creates spatial distribution around quantum signature origin.

        Args:
            agent_id: Agent identifier

        Returns:
            Derived geohash string
        """
        # Hash agent_id to get offset values
        hash_bytes = hashlib.sha256(agent_id.encode()).digest()

        # Extract offset values from hash (small perturbations)
        lat_offset = (int.from_bytes(hash_bytes[:4], 'big') % 1000) / 100000.0 - 0.005
        lon_offset = (int.from_bytes(hash_bytes[4:8], 'big') % 1000) / 100000.0 - 0.005

        # Apply offset to origin coordinates
        origin_lat, origin_lon = self.signature.get_coordinates()
        agent_lat = origin_lat + lat_offset
        agent_lon = origin_lon + lon_offset

        # Generate geohash for agent position
        return self.signature._encode_geohash(agent_lat, agent_lon, precision=8)

    def _calculate_agent_score(self, agent: Agent, task: Dict[str, Any]) -> float:
        """
        Calculate routing score for agent-task pairing.

        Args:
            agent: Candidate agent
            task: Task to be assigned

        Returns:
            Score (0-100, higher is better)
        """
        factors = {}

        # Load factor (prefer less loaded agents)
        factors['availability'] = 1.0 - agent.get_load_factor()

        # Specialization match
        task_specialization = task.get('specialization')
        if task_specialization:
            if task_specialization in agent.specializations:
                factors['specialization'] = 1.0
            else:
                factors['specialization'] = 0.3
        else:
            factors['specialization'] = 0.5

        # Geohash proximity to origin (closer = better)
        proximity = self._calculate_geohash_proximity(agent.geohash, self.origin_geohash)
        factors['proximity'] = proximity

        # Agent type bonus
        factors['type_bonus'] = 0.8  # Baseline

        # Use decision engine to calculate final score with quantum perturbation
        score = self.decision_engine.evaluate_score(factors, min_score=0, max_score=100)

        return score

    def _calculate_geohash_proximity(self, geohash1: str, geohash2: str) -> float:
        """
        Calculate proximity score between two geohashes.

        Args:
            geohash1: First geohash
            geohash2: Second geohash

        Returns:
            Proximity score (0-1, higher = closer)
        """
        # Count matching prefix characters
        matches = 0
        for c1, c2 in zip(geohash1, geohash2):
            if c1 == c2:
                matches += 1
            else:
                break

        # Normalize by length
        max_len = min(len(geohash1), len(geohash2))
        if max_len == 0:
            return 0.0

        return matches / max_len

    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics.

        Returns:
            Dict with orchestrator metrics
        """
        total_agents = len(self.agents)
        if total_agents == 0:
            return {
                'total_agents': 0,
                'origin_geohash': self.origin_geohash,
            }

        status_counts = {}
        type_counts = {}
        total_capacity = 0
        total_load = 0

        for agent in self.agents.values():
            status_counts[agent.status.value] = status_counts.get(agent.status.value, 0) + 1
            type_counts[agent.type.value] = type_counts.get(agent.type.value, 0) + 1
            total_capacity += agent.capacity
            total_load += agent.current_load

        return {
            'total_agents': total_agents,
            'origin_geohash': self.origin_geohash,
            'status_distribution': status_counts,
            'type_distribution': type_counts,
            'total_capacity': total_capacity,
            'total_load': total_load,
            'utilization': total_load / total_capacity if total_capacity > 0 else 0,
        }


# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> AgentOrchestrator:
    """
    Get or create singleton orchestrator instance.

    Returns:
        AgentOrchestrator: Global orchestrator
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator()
    return _orchestrator_instance
