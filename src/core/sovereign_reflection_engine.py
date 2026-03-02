#!/usr/bin/env python3
"""ARK95X Sovereign Self-Reflection Engine — Autonomy Level 4
Fully Autonomous Self-Improving Agent Loop with Strategic Execution Framework.
The system asks itself 10 diagnostic questions after every task cycle,
scores its own performance, logs insights to memory, and rewrites its own
prompt strategies for the next iteration — all without human input.
Compatible with CrewAI, LangChain, Ollama (local), OpenAI, Anthropic.
"""
import json
import time
import sqlite3
import hashlib
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from enum import Enum

logger = logging.getLogger("ark95x.reflection")


class ExecutionHealth(Enum):
    """Strategic execution health based on 7-factor audit."""
    CRITICAL = "critical"
    AT_RISK = "at_risk"
    HEALTHY = "healthy"
    EXCEPTIONAL = "exceptional"


class AutonomyLevel(Enum):
    OPERATOR = 1
    COLLABORATOR = 2
    CONSULTANT = 3
    APPROVER = 4
    OBSERVER = 5


# ═══ CORE: The 10 Self-Reflection Questions ═══
STRATEGIC_EXECUTION_FRAMEWORK = [
    {"clarity": {"check": "Can I state the goal in one sentence?",
     "validation": ["One measurable outcome", "One clear finish line",
                    "One definition of done"], "weight": 1.5}},
    {"urgency": {"check": "Why does this matter NOW?",
     "three_questions": ["Why does this matter now?",
                         "What breaks if we lose?", "Who does this help?"],
     "weight": 1.4}},
    {"planning": {"check": "What are 2-3 lead measures per priority?",
     "validation": ["Define 2-3 lead measures",
                    "Clarify good for this week",
                    "Tie measures to meetings"], "weight": 1.3}},
    {"agility": {"check": "What will actually get in the way?",
     "stress_test": ["What will actually get in the way?",
                     "What must stop for this to start?",
                     "Where will this break under pressure?"],
     "weight": 1.2}},
    {"ownership": {"check": "Who shaped this plan besides me?",
     "validation": ["Involve others in defining how",
                    "Let teams shape lead measures",
                    "Connect strategy to personal wins"], "weight": 1.4}},
    {"time": {"check": "Is this on the calendar with non-negotiable rhythms?",
     "protection": ["Schedule weekly lead-measure reviews",
                    "Make execution visible daily",
                    "Protect time for critical actions"], "weight": 1.3}},
    {"accountability": {"check": "Is there a public scoreboard?",
     "mechanisms": ["Public scoreboard updated weekly",
                    "Weekly commitment cycle",
                    "Kill bad bets fast with abort criteria"],
     "weight": 1.5}},
    {"tool_selection": {"check": "Did I use the right tools?",
     "weight": 1.2}},
    {"evolution": {"check": "What would a smarter version do differently?",
     "weight": 1.2}},
    {"autonomy_check": {"check": "Should I escalate, delegate, or continue?",
     "weight": 1.0}},
]


@dataclass
class StrategyEntry:
    strategy_id: str
    source_cycle: str
    directive: str
    category: str
    applied_count: int = 0
    success_delta: float = 0.0
    created_at: str = ""
    active: bool = True


@dataclass
class ReflectionCycle:
    cycle_id: str
    agent_id: str
    task_summary: str
    scores: Dict[str, float] = field(default_factory=dict)
    reasoning: Dict[str, str] = field(default_factory=dict)
    weighted_average: float = 0.0
    prompt_patch: str = ""
    autonomy_decision: str = "CONTINUE"
    strategies_applied: List[str] = field(default_factory=list)
    execution_health: str = "healthy"
    timestamp: str = ""


@dataclass
class StrategicAuditResult:
    factors_passing: int = 0
    total_factors: int = 7
    health: ExecutionHealth = ExecutionHealth.HEALTHY
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ReflectionMemory:
    """SQLite persistence layer for reflection cycles and strategies."""

    def __init__(self, db_path: str = "ark95x_reflection.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS reflection_cycles (
                cycle_id TEXT PRIMARY KEY, agent_id TEXT,
                task_summary TEXT, scores TEXT, reasoning TEXT,
                weighted_average REAL, prompt_patch TEXT,
                autonomy_decision TEXT, execution_health TEXT,
                strategies_applied TEXT, timestamp TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS strategies (
                strategy_id TEXT PRIMARY KEY, source_cycle TEXT,
                directive TEXT, category TEXT, applied_count INTEGER,
                success_delta REAL, created_at TEXT, active INTEGER)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS performance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT, weighted_average REAL,
                execution_health TEXT, timestamp TEXT)""")

    def save_cycle(self, cycle: ReflectionCycle):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reflection_cycles VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (cycle.cycle_id, cycle.agent_id, cycle.task_summary,
                 json.dumps(cycle.scores), json.dumps(cycle.reasoning),
                 cycle.weighted_average, cycle.prompt_patch,
                 cycle.autonomy_decision, cycle.execution_health,
                 json.dumps(cycle.strategies_applied), cycle.timestamp))
            conn.execute(
                "INSERT INTO performance_log (agent_id, weighted_average, execution_health, timestamp) VALUES (?,?,?,?)",
                (cycle.agent_id, cycle.weighted_average, cycle.execution_health, cycle.timestamp))

    def save_strategy(self, strategy: StrategyEntry):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO strategies VALUES (?,?,?,?,?,?,?,?)",
                (strategy.strategy_id, strategy.source_cycle,
                 strategy.directive, strategy.category,
                 strategy.applied_count, strategy.success_delta,
                 strategy.created_at, int(strategy.active)))

    def get_active_strategies(self, limit: int = 5) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM strategies WHERE active=1 ORDER BY success_delta DESC LIMIT ?",
                (limit,)).fetchall()
        return [{"strategy_id": r[0], "directive": r[2], "category": r[3],
                 "applied_count": r[4], "success_delta": r[5]} for r in rows]

    def get_performance_trend(self, agent_id: str, n: int = 10) -> List[float]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT weighted_average FROM performance_log WHERE agent_id=? ORDER BY id DESC LIMIT ?",
                (agent_id, n)).fetchall()
        return [r[0] for r in reversed(rows)]


class SovereignReflectionEngine:
    """The core self-reflection and self-improvement engine."""

    def __init__(self, agent_id: str = "ARK95X-PRIME",
                 llm_call: Callable = None,
                 autonomy_level: int = 4,
                 score_threshold: float = 6.0,
                 db_path: str = "ark95x_reflection.db"):
        self.agent_id = agent_id
        self.llm_call = llm_call
        self.autonomy_level = AutonomyLevel(min(autonomy_level, 4))
        self.score_threshold = score_threshold
        self.memory = ReflectionMemory(db_path)
        self.cycle_count = 0
        logger.info(f"Reflection engine initialized: {agent_id} at L{autonomy_level}")

    def reflect(self, task_summary: str, task_output: str) -> ReflectionCycle:
        """Run a full 10-question self-reflection cycle."""
        self.cycle_count += 1
        cycle_id = f"{self.agent_id}_{int(time.time())}_{self.cycle_count}"
        now = datetime.now(timezone.utc).isoformat()

        strategies = self.memory.get_active_strategies()
        strategy_context = "\n".join(
            [f"- [{s['category']}] {s['directive']}" for s in strategies]
        ) if strategies else "No active strategies yet."

        prompt = self._build_reflection_prompt(
            task_summary, task_output, strategy_context)

        if self.llm_call:
            try:
                raw = self.llm_call(prompt)
                result = self._parse_reflection(raw)
            except Exception as e:
                logger.warning(f"LLM reflection failed: {e}")
                result = self._baseline_scores()
        else:
            result = self._baseline_scores()

        scores = result.get("scores", {})
        reasoning = result.get("reasoning", {})
        weighted_avg = self._compute_weighted_average(scores)
        autonomy_decision = self._decide_autonomy(weighted_avg)
        prompt_patch = self._generate_prompt_patch(scores, reasoning)
        health = self._assess_execution_health(scores)

        cycle = ReflectionCycle(
            cycle_id=cycle_id, agent_id=self.agent_id,
            task_summary=task_summary, scores=scores,
            reasoning=reasoning, weighted_average=weighted_avg,
            prompt_patch=prompt_patch,
            autonomy_decision=autonomy_decision,
            strategies_applied=[s["strategy_id"] for s in strategies],
            execution_health=health.value, timestamp=now)

        self.memory.save_cycle(cycle)
        self._extract_strategies(cycle, scores, reasoning)

        logger.info(
            f"Reflection {cycle_id}: avg={weighted_avg:.1f} "
            f"health={health.value} decision={autonomy_decision}")
        return cycle

    def _build_reflection_prompt(self, summary, output, strategies):
        questions = "\n".join([
            f"{i+1}. {list(q.keys())[0].upper()}: {list(q.values())[0]['check']}"
            for i, q in enumerate(STRATEGIC_EXECUTION_FRAMEWORK)])
        return f"""You are a self-evaluating AI agent. Score yourself 0-10 on each question.
Return JSON: {{"scores": {{"q1": N, ...}}, "reasoning": {{"q1": "...", ...}}}}

TASK: {summary}
OUTPUT: {output[:500]}
ACTIVE STRATEGIES:\n{strategies}

QUESTIONS:\n{questions}

Respond ONLY with valid JSON."""

    def _parse_reflection(self, raw: str) -> Dict:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            return self._baseline_scores()

    def _baseline_scores(self) -> Dict:
        return {"scores": {f"q{i+1}": 5.0 for i in range(10)},
                "reasoning": {f"q{i+1}": "Baseline - no LLM connected" for i in range(10)}}

    def _compute_weighted_average(self, scores: Dict) -> float:
        weights = [list(q.values())[0].get("weight", 1.0)
                   for q in STRATEGIC_EXECUTION_FRAMEWORK]
        total_w, total_s = 0.0, 0.0
        for i, (key, score) in enumerate(scores.items()):
            w = weights[i] if i < len(weights) else 1.0
            total_w += w
            total_s += float(score) * w
        return round(total_s / total_w, 2) if total_w > 0 else 5.0

    def _decide_autonomy(self, weighted_avg: float) -> str:
        if weighted_avg < 4.0:
            return "ESCALATE"
        elif weighted_avg < 6.0:
            return "CONTINUE_CAUTION"
        return "CONTINUE"

    def _assess_execution_health(self, scores: Dict) -> ExecutionHealth:
        passing = sum(1 for s in scores.values() if float(s) >= 6.0)
        if passing <= 3:
            return ExecutionHealth.CRITICAL
        elif passing <= 5:
            return ExecutionHealth.AT_RISK
        elif passing <= 7:
            return ExecutionHealth.HEALTHY
        return ExecutionHealth.EXCEPTIONAL

    def _generate_prompt_patch(self, scores: Dict, reasoning: Dict) -> str:
        patches = []
        categories = [list(q.keys())[0] for q in STRATEGIC_EXECUTION_FRAMEWORK]
        for i, (key, score) in enumerate(scores.items()):
            if float(score) < self.score_threshold:
                cat = categories[i] if i < len(categories) else "unknown"
                reason = reasoning.get(key, "")
                patches.append(
                    f"[{cat.upper()}] Score: {score}/10 -> Fix: {reason[:100]}")
        return "\n".join(patches) if patches else "NO_PATCH_NEEDED"

    def _extract_strategies(self, cycle, scores, reasoning):
        for i, (key, score) in enumerate(scores.items()):
            if float(score) >= 7.0:
                cats = [list(q.keys())[0] for q in STRATEGIC_EXECUTION_FRAMEWORK]
                cat = cats[i] if i < len(cats) else "general"
                sid = hashlib.md5(
                    f"{cycle.cycle_id}_{key}".encode()).hexdigest()[:12]
                strategy = StrategyEntry(
                    strategy_id=sid, source_cycle=cycle.cycle_id,
                    directive=reasoning.get(key, "High performance noted"),
                    category=cat,
                    created_at=cycle.timestamp)
                self.memory.save_strategy(strategy)

    def generate_strategic_audit(self, scores: Dict) -> StrategicAuditResult:
        """Run the 7-factor strategic execution audit."""
        audit = StrategicAuditResult()
        factors = ["clarity", "urgency", "planning", "agility",
                   "ownership", "time", "accountability"]
        for i, factor in enumerate(factors):
            key = f"q{i+1}"
            score = float(scores.get(key, 0))
            if score >= 6.0:
                audit.factors_passing += 1
                audit.findings.append(f"{factor}: PASS ({score}/10)")
            else:
                audit.findings.append(f"{factor}: FAIL ({score}/10)")
                audit.recommendations.append(
                    f"Improve {factor} - current score {score}/10")
        if audit.factors_passing <= 3:
            audit.health = ExecutionHealth.CRITICAL
        elif audit.factors_passing <= 5:
            audit.health = ExecutionHealth.AT_RISK
        elif audit.factors_passing < 7:
            audit.health = ExecutionHealth.HEALTHY
        else:
            audit.health = ExecutionHealth.EXCEPTIONAL
        return audit

    def get_performance_trend(self, n: int = 10) -> List[float]:
        return self.memory.get_performance_trend(self.agent_id, n)


def crewai_post_task_hook(output, llm_call=None, agent_id="ARK95X-CREW"):
    """Drop-in hook for CrewAI task callbacks."""
    engine = SovereignReflectionEngine(
        agent_id=agent_id, llm_call=llm_call)
    return engine.reflect(
        task_summary=str(output)[:200],
        task_output=str(output))


def ollama_call(prompt: str, model: str = "llama3.1") -> str:
    """Default Ollama local LLM call."""
    import requests
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": model, "prompt": prompt, "stream": False})
    return r.json()["response"]


if __name__ == "__main__":
    engine = SovereignReflectionEngine(
        agent_id="ARK95X-TEST", llm_call=None, autonomy_level=4)
    cycle = engine.reflect(
        task_summary="Test task: verify reflection engine",
        task_output="Engine initialized and running baseline scores")
    print(f"Cycle: {cycle.cycle_id}")
    print(f"Weighted Avg: {cycle.weighted_average}")
    print(f"Health: {cycle.execution_health}")
    print(f"Decision: {cycle.autonomy_decision}")
    audit = engine.generate_strategic_audit(cycle.scores)
    print(f"Audit: {audit.factors_passing}/{audit.total_factors} passing")
    print(f"Audit Health: {audit.health.value}")
