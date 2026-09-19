"""
Lesson Learner — closed-loop feedback from mission history into decomposition

Reads `data/lessons/network95.jsonl` (written by Network95Agent.persist_and_learn)
and surfaces:
  - type_weights(objective)  — suggests best task type for a keyword
  - suggest_priority(objective) — suggests priority adjustment based on past speed
  - recent_failures()        — list of recently failed task types to avoid or retry
  - summary()                — stats for logging / status endpoint

This is the "L" in LEARN that feeds back into DECOMPOSE.
"""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("network95.lesson_learner")

_LESSONS_PATH = Path("data/lessons/network95.jsonl")
_MAX_LESSONS = 500


class LessonLearner:
    """
    Lightweight in-process lesson store.  Load once, refresh on demand.

    The JSONL file each lesson looks like:
      {
        "mission_id": "...",
        "objective": "...",
        "pipeline_summary": {"stages": [...], "bottlenecks": [...], ...},
        "sub_tasks": [{"type": "embedding", "status": "completed", ...}],
        "timestamp": 1234567890.0
      }
    """

    def __init__(self, path: Optional[Path] = None):
        self._path = path or _LESSONS_PATH
        # type → {total, succeeded, total_duration_s}
        self._type_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"total": 0, "succeeded": 0, "duration": 0.0})
        # keyword → most successful type
        self._keyword_type: Dict[str, str] = {}
        self._lessons_loaded = 0
        self._load()

    # ── Load / refresh ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        lines = self._path.read_text().splitlines()
        # Only keep the most recent MAX_LESSONS entries
        for line in lines[-_MAX_LESSONS:]:
            try:
                lesson = json.loads(line)
                self._ingest(lesson)
                self._lessons_loaded += 1
            except Exception:
                pass
        self._rebuild_keyword_map()
        log.debug("LessonLearner loaded %d lessons from %s", self._lessons_loaded, self._path)

    def refresh(self) -> None:
        """Re-read the JSONL file to pick up lessons from this and previous sessions."""
        self._type_stats = defaultdict(lambda: {"total": 0, "succeeded": 0, "duration": 0.0})
        self._lessons_loaded = 0
        self._load()

    def _ingest(self, lesson: Dict[str, Any]) -> None:
        sub_tasks = lesson.get("sub_tasks", [])
        for task in sub_tasks:
            t = task.get("type", "local")
            succeeded = task.get("status") == "completed"
            duration = task.get("duration_s") or task.get("estimated_s") or 0.0
            self._type_stats[t]["total"] += 1
            self._type_stats[t]["succeeded"] += int(succeeded)
            self._type_stats[t]["duration"] += float(duration)

    def _rebuild_keyword_map(self) -> None:
        """Map common objective keywords → the executor type with the best success rate."""
        self._keyword_type = {}
        for t, stats in self._type_stats.items():
            if stats["total"] < 3:
                continue
            rate = stats["succeeded"] / stats["total"]
            if rate < 0.5:
                continue
            # Associate this type with its own name as a keyword (simple bootstrap)
            self._keyword_type[t] = t

    # ── Public API ─────────────────────────────────────────────────────────────

    def type_weights(self, objective: str) -> Dict[str, float]:
        """
        Returns {task_type: confidence_weight} for task types that have a positive
        history relevant to this objective's keywords.  Weights ∈ (0, 1].
        """
        obj_lower = objective.lower()
        weights: Dict[str, float] = {}
        for t, stats in self._type_stats.items():
            if stats["total"] < 2:
                continue
            rate = stats["succeeded"] / stats["total"]
            if rate < 0.4:
                continue
            # If objective text mentions the type name or a known keyword
            if t in obj_lower or any(kw in obj_lower for kw in _TYPE_KEYWORDS.get(t, [])):
                weights[t] = round(rate, 3)
        return weights

    def suggest_priority_delta(self, objective: str) -> int:
        """
        Returns −2..+2 adjustment to default priority based on lesson history.
        Negative = bump up (more urgent), Positive = deprioritise.
        Objectives that have historically fast completions get priority boost.
        """
        weights = self.type_weights(objective)
        if not weights:
            return 0
        best_type = max(weights, key=weights.__getitem__)
        stats = self._type_stats[best_type]
        if stats["total"] == 0:
            return 0
        avg_duration = stats["duration"] / stats["total"]
        if avg_duration < 3.0:
            return -1  # historically fast → bump up
        if avg_duration > 30.0:
            return +1  # historically slow → deprioritise slightly
        return 0

    def recent_failures(self, limit: int = 5) -> List[str]:
        """Returns task types that have recently failed (success rate < 40%)."""
        failures = [
            t for t, s in self._type_stats.items()
            if s["total"] >= 2 and (s["succeeded"] / s["total"]) < 0.4
        ]
        return failures[:limit]

    def summary(self) -> Dict[str, Any]:
        total_tasks = sum(s["total"] for s in self._type_stats.values())
        total_ok = sum(s["succeeded"] for s in self._type_stats.values())
        return {
            "lessons_loaded": self._lessons_loaded,
            "type_stats": {
                t: {
                    "total": int(s["total"]),
                    "success_rate": round(s["succeeded"] / s["total"], 3) if s["total"] else 0.0,
                    "avg_duration_s": round(s["duration"] / s["total"], 2) if s["total"] else 0.0,
                }
                for t, s in self._type_stats.items()
            },
            "overall_success_rate": round(total_ok / total_tasks, 3) if total_tasks else 0.0,
            "recent_failures": self.recent_failures(),
        }


# ── Keyword → executor type map ───────────────────────────────────────────────

_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "ollama":    ["model", "llm", "language", "generate", "chat", "ollama"],
    "embedding": ["embed", "vector", "semantic", "similarity", "rag", "encode"],
    "n8n":       ["workflow", "automation", "n8n", "webhook", "trigger", "scan", "research"],
    "docker":    ["container", "docker", "build", "image", "compile", "deploy"],
    "inference": ["infer", "classify", "predict", "score", "ml", "ai"],
    "local":     ["local", "script", "run", "execute", "shell", "command"],
}
