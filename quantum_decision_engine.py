"""
Quantum Decision Engine
========================
Deterministic decision-making system seeded by temporal anchor.
Uses birth timestamp for reproducible yet seemingly random choices.

Integrates Life Path 5 characteristics: Innovation, Freedom, Adaptability
"""

import random
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import hashlib

from quantum_signature import get_quantum_signature


class DecisionStrategy(Enum):
    """Decision-making strategies aligned with Life Path 5 traits."""
    INNOVATIVE = "innovative"  # Favor novel approaches
    ADAPTIVE = "adaptive"  # Context-sensitive choices
    FREE_FORM = "free_form"  # Maximum exploration
    BALANCED = "balanced"  # Equilibrium across factors


class QuantumDecisionEngine:
    """
    Decision engine using quantum signature for deterministic randomness.

    All decisions are seeded by the temporal anchor (745102980),
    ensuring reproducibility while maintaining unpredictability.
    """

    def __init__(self):
        """Initialize decision engine with quantum signature."""
        self.signature = get_quantum_signature()
        self.master_seed = self.signature.get_master_seed()
        self.life_path = self.signature.get_life_path()

        # Initialize base RNG with master seed
        self.rng = random.Random(self.master_seed)

        # Decision history for learning
        self.decision_history: List[Dict[str, Any]] = []

    def make_choice(
        self,
        options: List[Any],
        context: Optional[str] = None,
        strategy: DecisionStrategy = DecisionStrategy.BALANCED,
        weights: Optional[List[float]] = None
    ) -> Any:
        """
        Make a quantum-seeded choice from available options.

        Args:
            options: List of choices to select from
            context: Optional context string to influence seed
            strategy: Decision strategy to employ
            weights: Optional weights for each option

        Returns:
            Selected option
        """
        if not options:
            raise ValueError("Cannot choose from empty options list")

        # Create context-specific seed
        seed = self._derive_context_seed(context)
        rng = random.Random(seed)

        # Apply strategy-specific logic
        if strategy == DecisionStrategy.INNOVATIVE:
            # Favor less-traveled paths (inverse frequency weighting)
            choice = self._innovative_choice(options, rng, weights)
        elif strategy == DecisionStrategy.ADAPTIVE:
            # Use decision history to adapt
            choice = self._adaptive_choice(options, rng, weights)
        elif strategy == DecisionStrategy.FREE_FORM:
            # Pure randomness (still deterministic via seed)
            choice = rng.choices(options, weights=weights)[0]
        else:  # BALANCED
            choice = rng.choices(options, weights=weights)[0]

        # Record decision
        self.decision_history.append({
            'choice': choice,
            'options': options.copy(),
            'context': context,
            'strategy': strategy.value,
            'seed': seed,
        })

        return choice

    def make_weighted_decision(
        self,
        outcomes: Dict[str, float],
        context: Optional[str] = None
    ) -> str:
        """
        Make decision from weighted outcome dictionary.

        Args:
            outcomes: Dict mapping outcome names to weights
            context: Optional context for seeding

        Returns:
            Selected outcome key
        """
        options = list(outcomes.keys())
        weights = list(outcomes.values())
        return self.make_choice(options, context=context, weights=weights)

    def evaluate_score(
        self,
        factors: Dict[str, float],
        min_score: float = 0.0,
        max_score: float = 100.0
    ) -> float:
        """
        Evaluate a quantum-influenced score from multiple factors.

        Args:
            factors: Dict of factor names to values (0-1 normalized)
            min_score: Minimum score value
            max_score: Maximum score value

        Returns:
            Calculated score with quantum perturbation
        """
        if not factors:
            return (min_score + max_score) / 2

        # Base score from weighted average
        base_score = sum(factors.values()) / len(factors)

        # Add life-path influenced perturbation
        perturbation_seed = self.master_seed + hash(str(sorted(factors.items())))
        perturbation_rng = random.Random(perturbation_seed)

        # Life Path 5: +/- 5% variance for dynamism
        perturbation = perturbation_rng.uniform(-0.05, 0.05)

        final_score = base_score * (1 + perturbation)
        final_score = max(min_score, min(max_score, final_score * (max_score - min_score) + min_score))

        return final_score

    def should_innovate(self, threshold: float = 0.5, context: Optional[str] = None) -> bool:
        """
        Decide whether to take innovative path vs conventional.

        Life Path 5 bias: Higher baseline innovation rate.

        Args:
            threshold: Innovation threshold (0-1)
            context: Optional context for decision

        Returns:
            True if should innovate
        """
        # Life Path 5: +15% innovation bias
        adjusted_threshold = threshold * 0.85

        seed = self._derive_context_seed(context)
        rng = random.Random(seed)

        return rng.random() > adjusted_threshold

    def get_exploration_rate(self, base_rate: float = 0.2) -> float:
        """
        Calculate exploration rate for exploration/exploitation balance.

        Args:
            base_rate: Base exploration rate

        Returns:
            Adjusted exploration rate
        """
        # Life Path 5: Favor exploration (+50% boost)
        return min(1.0, base_rate * 1.5)

    def _derive_context_seed(self, context: Optional[str]) -> int:
        """
        Derive seed from master seed and context.

        Args:
            context: Context string

        Returns:
            Derived integer seed
        """
        if context is None:
            return self.master_seed

        # Hash context and combine with master seed
        context_hash = hashlib.sha256(context.encode()).hexdigest()
        context_int = int(context_hash[:16], 16)

        return self.master_seed ^ context_int

    def _innovative_choice(
        self,
        options: List[Any],
        rng: random.Random,
        weights: Optional[List[float]]
    ) -> Any:
        """
        Make innovative choice favoring novel options.

        Args:
            options: Available options
            rng: Random number generator
            weights: Optional weights

        Returns:
            Selected option
        """
        # Count option frequencies in history
        frequencies = {}
        for decision in self.decision_history:
            choice = decision['choice']
            frequencies[str(choice)] = frequencies.get(str(choice), 0) + 1

        # Create inverse frequency weights
        inverse_weights = []
        for opt in options:
            freq = frequencies.get(str(opt), 0)
            # Less used = higher weight
            inverse_weights.append(1.0 / (freq + 1))

        # Combine with provided weights if available
        if weights:
            combined = [iw * w for iw, w in zip(inverse_weights, weights)]
        else:
            combined = inverse_weights

        return rng.choices(options, weights=combined)[0]

    def _adaptive_choice(
        self,
        options: List[Any],
        rng: random.Random,
        weights: Optional[List[float]]
    ) -> Any:
        """
        Make adaptive choice based on decision history patterns.

        Args:
            options: Available options
            rng: Random number generator
            weights: Optional weights

        Returns:
            Selected option
        """
        # If no history, fall back to standard choice
        if len(self.decision_history) < 3:
            return rng.choices(options, weights=weights)[0]

        # Analyze recent decision success patterns
        # For now, use a simple recency-weighted approach
        recent_choices = [d['choice'] for d in self.decision_history[-5:]]

        # Weight recent choices slightly higher
        adaptive_weights = []
        for opt in options:
            if str(opt) in [str(rc) for rc in recent_choices]:
                adaptive_weights.append(1.2)  # Slight boost for recent
            else:
                adaptive_weights.append(1.0)

        # Combine with provided weights
        if weights:
            combined = [aw * w for aw, w in zip(adaptive_weights, weights)]
        else:
            combined = adaptive_weights

        return rng.choices(options, weights=combined)[0]

    def get_decision_stats(self) -> Dict[str, Any]:
        """
        Get statistics about decision history.

        Returns:
            Dict with decision statistics
        """
        if not self.decision_history:
            return {
                'total_decisions': 0,
                'strategy_distribution': {},
                'innovation_rate': 0.0,
            }

        strategies = {}
        for decision in self.decision_history:
            strat = decision['strategy']
            strategies[strat] = strategies.get(strat, 0) + 1

        innovative_decisions = sum(
            1 for d in self.decision_history
            if d['strategy'] == DecisionStrategy.INNOVATIVE.value
        )

        return {
            'total_decisions': len(self.decision_history),
            'strategy_distribution': strategies,
            'innovation_rate': innovative_decisions / len(self.decision_history),
            'life_path': self.life_path,
        }


# Singleton instance
_decision_engine_instance = None

def get_decision_engine() -> QuantumDecisionEngine:
    """
    Get or create singleton decision engine instance.

    Returns:
        QuantumDecisionEngine: Global decision engine
    """
    global _decision_engine_instance
    if _decision_engine_instance is None:
        _decision_engine_instance = QuantumDecisionEngine()
    return _decision_engine_instance
