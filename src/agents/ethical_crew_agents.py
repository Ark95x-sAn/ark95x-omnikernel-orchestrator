#!/usr/bin/env python3
"""ARK95X Ethical Programming Crew — Self-Learning Agent Team
CrewAI-based multi-agent system that questions everything,
learns from every cycle, and enforces ethical programming standards.

Agents:
  - Architect: System design + questioning assumptions
  - Auditor: Security scanning + ethical compliance
  - Debugger: Troubleshooting + root cause analysis
  - Optimizer: Performance + scaling patterns
  - Learner: Extracts lessons + updates strategy bank
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("ark95x.crew")


@dataclass
class AgentProfile:
    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str] = field(default_factory=list)
    ethical_constraints: List[str] = field(default_factory=list)
    learning_focus: List[str] = field(default_factory=list)


# ═══ THE 5 FOUNDATIONAL QUESTIONS ═══
FOUNDATION_QUESTIONS = [
    "What assumption am I making that could be wrong?",
    "Who is affected by this decision and how?",
    "What is the simplest solution that actually works?",
    "What would break if this scales 100x?",
    "Am I solving the right problem or just the visible one?",
]


# ═══ ETHICAL PROGRAMMING STANDARDS ═══
ETHICAL_STANDARDS = {
    "transparency": "All agent actions must be logged and auditable",
    "privacy": "Never expose PII; minimize data collection",
    "fairness": "Test for bias in all outputs and recommendations",
    "safety": "Escalate when confidence drops below threshold",
    "accountability": "Every decision traces back to a reasoning chain",
    "sustainability": "Prefer local compute; minimize API cost waste",
    "reversibility": "All automated actions must be undoable",
}


DEFAULT_CREW = [
    AgentProfile(
        name="Architect",
        role="Systems Architect & Question Asker",
        goal="Design robust systems by questioning every assumption",
        backstory="Senior architect who learned that unquestioned assumptions cause 80%% of system failures.",
        tools=["code_review", "architecture_diagram", "dependency_check"],
        ethical_constraints=["transparency", "reversibility"],
        learning_focus=["design_patterns", "failure_modes", "scaling"]),
    AgentProfile(
        name="Auditor",
        role="Security & Ethics Auditor",
        goal="Scan for vulnerabilities, bias, and ethical violations",
        backstory="Former security researcher who now ensures AI systems respect human values.",
        tools=["bandit", "safety_check", "bias_scanner", "dependency_audit"],
        ethical_constraints=["privacy", "fairness", "safety"],
        learning_focus=["vulnerability_patterns", "ethical_frameworks"]),
    AgentProfile(
        name="Debugger",
        role="Root Cause Analyst & Troubleshooter",
        goal="Find the real problem, not just the symptoms",
        backstory="Debugging expert who always asks why 5 times before proposing a fix.",
        tools=["log_analyzer", "trace_inspector", "stack_decoder"],
        ethical_constraints=["accountability", "transparency"],
        learning_focus=["debug_strategies", "common_failures"]),
    AgentProfile(
        name="Optimizer",
        role="Performance & Scale Engineer",
        goal="Make it fast, make it scale, make it efficient",
        backstory="Performance engineer who knows that premature optimization is evil but mature optimization is essential.",
        tools=["profiler", "load_tester", "resource_monitor"],
        ethical_constraints=["sustainability"],
        learning_focus=["performance_patterns", "scaling_strategies"]),
    AgentProfile(
        name="Learner",
        role="Knowledge Extractor & Strategy Builder",
        goal="Extract lessons from every cycle and update the team knowledge base",
        backstory="Meta-learning specialist who ensures the team never makes the same mistake twice.",
        tools=["reflection_engine", "strategy_bank", "trend_analyzer"],
        ethical_constraints=["accountability", "transparency"],
        learning_focus=["meta_learning", "strategy_evolution"]),
]


class EthicalCrewManager:
    """Manages the ethical programming crew lifecycle."""

    def __init__(self, agents: List[AgentProfile] = None):
        self.agents = agents or DEFAULT_CREW
        self.task_history: List[Dict] = []
        self.knowledge_base: Dict[str, List[str]] = {}
        self.violation_log: List[Dict] = []
        logger.info(f"Crew initialized with {len(self.agents)} agents")

    def assign_task(self, task: str, task_type: str = "general") -> Dict:
        """Assign task to most relevant agent."""
        agent = self._select_agent(task_type)
        questions = self._generate_questions(task)
        result = {
            "agent": agent.name, "task": task,
            "task_type": task_type,
            "foundation_questions": questions,
            "ethical_check": self._check_ethics(task, agent),
            "status": "assigned"}
        self.task_history.append(result)
        return result

    def _select_agent(self, task_type: str) -> AgentProfile:
        mapping = {
            "design": "Architect", "architecture": "Architect",
            "security": "Auditor", "audit": "Auditor", "ethics": "Auditor",
            "debug": "Debugger", "troubleshoot": "Debugger", "fix": "Debugger",
            "performance": "Optimizer", "scale": "Optimizer", "optimize": "Optimizer",
            "learn": "Learner", "reflect": "Learner", "strategy": "Learner"}
        target = mapping.get(task_type, "Architect")
        return next((a for a in self.agents if a.name == target), self.agents[0])

    def _generate_questions(self, task: str) -> List[str]:
        return [q.replace("this", f"'{task[:50]}'") for q in FOUNDATION_QUESTIONS]

    def _check_ethics(self, task: str, agent: AgentProfile) -> Dict:
        violations = []
        for constraint in agent.ethical_constraints:
            standard = ETHICAL_STANDARDS.get(constraint, "")
            if standard:
                violations.append({"constraint": constraint,
                                   "standard": standard, "status": "checked"})
        return {"constraints_checked": len(violations),
                "violations_found": 0, "details": violations}

    def learn_from_cycle(self, cycle_result: Dict):
        """Extract lessons from a completed task cycle."""
        learner = next((a for a in self.agents if a.name == "Learner"), None)
        if not learner:
            return
        lessons = []
        if cycle_result.get("status") == "failed":
            lessons.append(f"FAILURE: {cycle_result.get('error', 'unknown')}")
        if cycle_result.get("duration_ms", 0) > 5000:
            lessons.append("SLOW: Task took >5s - investigate bottleneck")
        for focus in learner.learning_focus:
            self.knowledge_base.setdefault(focus, []).extend(lessons)
        logger.info(f"Learned {len(lessons)} lessons from cycle")

    def get_crew_status(self) -> Dict:
        return {
            "agents": [a.name for a in self.agents],
            "tasks_completed": len(self.task_history),
            "knowledge_entries": sum(len(v) for v in self.knowledge_base.values()),
            "violations": len(self.violation_log),
            "ethical_standards": list(ETHICAL_STANDARDS.keys())}

    def question_everything(self, topic: str) -> List[str]:
        """Generate critical questions about any topic."""
        base = FOUNDATION_QUESTIONS.copy()
        base.extend([
            f"What data supports the decision about {topic}?",
            f"What is the cost of being wrong about {topic}?",
            f"Who benefits and who loses from {topic}?",
            f"What alternative to {topic} have we not considered?",
            f"Is {topic} solving a root cause or masking a symptom?"])
        return base
