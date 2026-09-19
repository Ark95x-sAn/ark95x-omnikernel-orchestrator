"""
NETWORK-95 Mission HTTP + WebSocket Router

Mounts at /api/v1/missions — provides:
  POST   /                    Create + optionally auto-run a new mission
  GET    /                    List missions (queue / running / recent)
  GET    /{mission_id}        Get single mission details
  POST   /{mission_id}/run    Trigger execution of a queued mission
  GET    /status              Agent + learner status snapshot
  WS     /live               Real-time mission events pushed to clients
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

log = logging.getLogger("network95.router")

router = APIRouter(prefix="/api/v1/missions", tags=["network95"])

# Injected at startup by platform.py
_agent = None  # type: Optional[Any]  # Network95Agent


def set_agent(agent) -> None:
    global _agent
    _agent = agent


def _require_agent():
    if _agent is None:
        raise HTTPException(503, "NETWORK-95 agent not initialised")
    return _agent


# ── WebSocket broadcast ───────────────────────────────────────────────────────

class _WSManager:
    def __init__(self):
        self._clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        self._clients = [c for c in self._clients if c is not ws]

    async def broadcast(self, event: str, payload: Dict):
        msg = json.dumps({"event": event, "payload": payload})
        dead = []
        for ws in self._clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_ws = _WSManager()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateMissionRequest(BaseModel):
    objective: str
    priority: int = 5
    auto_run: bool = False
    context: Dict[str, Any] = {}


class MissionResponse(BaseModel):
    mission_id: str
    objective: str
    status: str
    stage: Optional[str] = None
    priority: int
    duration_s: Optional[float] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_mission(req: CreateMissionRequest):
    agent = _require_agent()
    mid = agent.create_mission(req.objective, priority=req.priority)
    m = agent.mission_manager.get(mid)

    await _ws.broadcast("mission_created", {"mission_id": mid, "objective": req.objective})

    if req.auto_run:
        asyncio.create_task(_run_and_broadcast(agent, mid, req.context))
        return {"mission_id": mid, "status": m.status.value, "auto_run": True}

    return {"mission_id": mid, "status": m.status.value, "auto_run": False}


@router.get("")
async def list_missions(view: str = "recent", limit: int = 20):
    agent = _require_agent()
    mm = agent.mission_manager

    if view == "queue":
        missions = mm.queue()[:limit]
    elif view == "running":
        missions = mm.running()[:limit]
    else:
        missions = mm.recent(limit)

    return {"view": view, "missions": [m.summary() for m in missions]}


@router.get("/status")
async def agent_status():
    agent = _require_agent()
    return agent.status()


@router.get("/{mission_id}")
async def get_mission(mission_id: str):
    agent = _require_agent()
    try:
        m = agent.mission_manager.get(mission_id)
    except KeyError:
        raise HTTPException(404, f"Mission {mission_id} not found")
    return {
        "mission_id": m.mission_id,
        "objective": m.objective,
        "status": m.status.value,
        "stage": m.stage,
        "stages_completed": m.stages_completed,
        "priority": m.priority,
        "duration_s": m.duration_s,
        "result": m.result,
        "error": m.error,
    }


@router.post("/{mission_id}/run")
async def run_mission(mission_id: str, context: Dict[str, Any] = {}):
    agent = _require_agent()
    try:
        m = agent.mission_manager.get(mission_id)
    except KeyError:
        raise HTTPException(404, f"Mission {mission_id} not found")

    from src.core.mission_manager import MissionStatus
    if m.status not in (MissionStatus.QUEUED,):
        raise HTTPException(409, f"Mission is {m.status.value}, cannot run")

    asyncio.create_task(_run_and_broadcast(agent, mission_id, context))
    return {"mission_id": mission_id, "status": "running_async"}


@router.websocket("/live")
async def mission_live(ws: WebSocket):
    await _ws.connect(ws)
    try:
        while True:
            await ws.receive_text()   # keep alive; ignore client messages
    except WebSocketDisconnect:
        _ws.disconnect(ws)


# ── Background task ──────────────────────────────────────────────────────────

async def _run_and_broadcast(agent, mission_id: str, context: Dict):
    await _ws.broadcast("mission_started", {"mission_id": mission_id})
    try:
        result = await agent.run_mission(mission_id, context=context)
        m = agent.mission_manager.get(mission_id)
        await _ws.broadcast("mission_complete", {
            "mission_id": mission_id,
            "status": m.status.value,
            "delta": result.get("notify", {}).get("delta", {}),
        })
    except Exception as exc:
        log.error("Mission %s failed in background: %s", mission_id[:8], exc)
        await _ws.broadcast("mission_error", {"mission_id": mission_id, "error": str(exc)})
