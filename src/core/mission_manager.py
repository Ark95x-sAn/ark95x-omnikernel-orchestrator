"""
NETWORK-95 Mission Manager

Implements the Mission Queue shown in the NETWORK-95 control panel:
  - Create / queue / start / complete / fail missions
  - SQLite persistence (sqlite-utils, already in requirements)
  - Dashboard-ready status snapshot matching the UI panels

Each mission maps to one run of the 7-stage NETWORK-95 pipeline.
"""
from __future__ import annotations

import time
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("network95.missions")

DB_PATH = Path("data/missions.db")


# ── Data model ────────────────────────────────────────────────────────────────

class MissionStatus(str, Enum):
    QUEUED    = "Queued"
    RUNNING   = "Running"
    COMPLETE  = "Complete"
    FAILED    = "Failed"
    CANCELLED = "Cancelled"


@dataclass
class Mission:
    mission_id: str
    objective: str
    status: MissionStatus = MissionStatus.QUEUED
    priority: int = 5               # 1=highest, 10=lowest
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Stage-level progress (matches 7-stage NETWORK-95 pipeline)
    stage: Optional[str] = None
    stages_completed: List[str] = field(default_factory=list)

    @property
    def duration_s(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return round(self.completed_at - self.started_at, 2)
        if self.started_at:
            return round(time.time() - self.started_at, 2)
        return None

    def to_row(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "objective": self.objective,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_json": json.dumps(self.result) if self.result else None,
            "error": self.error,
            "metadata_json": json.dumps(self.metadata),
            "stage": self.stage,
            "stages_json": json.dumps(self.stages_completed),
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.mission_id[:8],
            "objective": self.objective[:60],
            "status": self.status.value,
            "stage": self.stage,
            "priority": self.priority,
            "duration_s": self.duration_s,
        }


# ── MissionManager ────────────────────────────────────────────────────────────

class MissionManager:
    """
    Mission queue and persistence layer for NETWORK-95.

    Usage:
        mm = MissionManager()
        mid = mm.create("Verify RTX embeddings")
        mm.start(mid)
        mm.update_stage(mid, "execute")
        mm.complete(mid, result={"score": 768, "receipt": "RTX-20260913-001"})

        dashboard = mm.dashboard()
    """

    def __init__(self, db_path: Optional[Path] = None, persist: bool = True):
        self._missions: Dict[str, Mission] = {}
        self._db = None
        self._persist = persist
        if persist:
            self._init_db(db_path or DB_PATH)

    def _init_db(self, path: Path) -> None:
        try:
            from sqlite_utils import Database
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db = Database(path)
            if "missions" not in self._db.table_names():
                self._db["missions"].create({
                    "mission_id": str,
                    "objective": str,
                    "status": str,
                    "priority": int,
                    "created_at": float,
                    "started_at": float,
                    "completed_at": float,
                    "result_json": str,
                    "error": str,
                    "metadata_json": str,
                    "stage": str,
                    "stages_json": str,
                }, pk="mission_id", not_null={"mission_id", "objective", "status"})
                log.info("Mission DB initialised at %s", path)
        except Exception as exc:
            log.warning("Mission DB unavailable (%s), running in-memory only", exc)
            self._db = None

    def _save(self, mission: Mission) -> None:
        if self._db:
            try:
                self._db["missions"].upsert(mission.to_row(), pk="mission_id")
            except Exception as exc:
                log.warning("Mission save error: %s", exc)

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(
        self,
        objective: str,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        mid = str(uuid.uuid4())
        m = Mission(
            mission_id=mid,
            objective=objective,
            priority=priority,
            metadata=metadata or {},
        )
        self._missions[mid] = m
        self._save(m)
        log.info("QUEUED mission=%s objective=%r", mid[:8], objective[:50])
        return mid

    def start(self, mission_id: str) -> None:
        m = self._get(mission_id)
        m.status = MissionStatus.RUNNING
        m.started_at = time.time()
        m.stage = "intake"
        self._save(m)
        log.info("RUNNING mission=%s", mission_id[:8])

    def update_stage(self, mission_id: str, stage: str) -> None:
        m = self._get(mission_id)
        if m.stage and m.stage not in m.stages_completed:
            m.stages_completed.append(m.stage)
        m.stage = stage
        self._save(m)
        log.debug("STAGE mission=%s → %s", mission_id[:8], stage)

    def complete(
        self,
        mission_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        m = self._get(mission_id)
        m.status = MissionStatus.COMPLETE
        m.completed_at = time.time()
        m.result = result or {}
        if m.stage and m.stage not in m.stages_completed:
            m.stages_completed.append(m.stage)
        m.stage = "done"
        self._save(m)
        log.info(
            "COMPLETE mission=%s duration=%.1fs",
            mission_id[:8], m.duration_s or 0,
        )

    def fail(self, mission_id: str, error: str) -> None:
        m = self._get(mission_id)
        m.status = MissionStatus.FAILED
        m.completed_at = time.time()
        m.error = error
        self._save(m)
        log.error("FAILED mission=%s error=%s", mission_id[:8], error[:80])

    def cancel(self, mission_id: str) -> None:
        m = self._get(mission_id)
        m.status = MissionStatus.CANCELLED
        m.completed_at = time.time()
        self._save(m)
        log.info("CANCELLED mission=%s", mission_id[:8])

    def get(self, mission_id: str) -> Mission:
        return self._get(mission_id)

    def _get(self, mission_id: str) -> Mission:
        m = self._missions.get(mission_id)
        if not m:
            raise KeyError(f"Mission not found: {mission_id}")
        return m

    # ── Queries ───────────────────────────────────────────────────────────────

    def queue(self) -> List[Mission]:
        return sorted(
            [m for m in self._missions.values() if m.status == MissionStatus.QUEUED],
            key=lambda m: (m.priority, m.created_at),
        )

    def running(self) -> List[Mission]:
        return [m for m in self._missions.values() if m.status == MissionStatus.RUNNING]

    def recent(self, n: int = 10) -> List[Mission]:
        return sorted(
            self._missions.values(),
            key=lambda m: m.created_at,
            reverse=True,
        )[:n]

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def dashboard(self) -> Dict[str, Any]:
        """Returns the status panel matching the NETWORK-95 Mission Queue UI."""
        all_m = list(self._missions.values())
        by_status = {s.value: 0 for s in MissionStatus}
        for m in all_m:
            by_status[m.status.value] += 1

        active_missions = [
            m.summary()
            for m in sorted(all_m, key=lambda x: x.created_at, reverse=True)[:7]
        ]

        return {
            "active_missions": active_missions,
            "counts": by_status,
            "queue_depth": by_status[MissionStatus.QUEUED.value],
            "running": by_status[MissionStatus.RUNNING.value],
            "total": len(all_m),
        }
