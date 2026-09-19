"""ARK95X OmniNet — Social Platform API
FastAPI application exposing the full social + agent + sensing platform.
Run with: uvicorn src.api.platform:app --reload --port 8080
"""
import time
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.social.models import Post, PostType, AuraColor, DigitalIdentity
from src.social.feed_engine import FeedEngine
from src.social.identity import IdentityRegistry

try:
    from src.sensing.wifi_sensing_agent import WiFiSensingAgent
    _sensing = WiFiSensingAgent()
except Exception:
    _sensing = None

try:
    from src.telemetry.mindstate import MindStateEngine
    from src.telemetry.aura_engine import AuraEngine
    from src.telemetry.roi_engine import ROIEngine
    _mindstate = MindStateEngine()
    _aura      = AuraEngine()
    _roi       = ROIEngine()
except Exception as _te:
    _mindstate = _aura = _roi = None
    logging.getLogger("ark95x.platform").warning(f"Telemetry unavailable: {_te}")

try:
    from src.agents.network95_agent import Network95Agent
    from src.api.network95_router import router as _network95_router, set_agent as _set_n95_agent
    _network95_agent = Network95Agent()
    _set_n95_agent(_network95_agent)
except Exception as _n95_err:
    _network95_agent = None
    logging.getLogger("ark95x.platform").warning(f"NETWORK-95 unavailable: {_n95_err}")

logger = logging.getLogger("ark95x.platform")

# ── App init ───────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ARK95X OmniNet",
    description="Digital twin social platform — consciousness made operational",
    version="1.0.0",
)

if _network95_agent is not None:
    app.include_router(_network95_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_static = Path(__file__).parent.parent.parent / "static"
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

feed    = FeedEngine()
registry = IdentityRegistry()

# ── WebSocket connection manager ───────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active = [c for c in self.active if c != ws]

    async def broadcast(self, data: Dict):
        msg = json.dumps(data)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── Background pulse ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def start_background():
    feed.bootstrap()
    asyncio.create_task(_pulse_loop())
    asyncio.create_task(_sensing_loop())
    asyncio.create_task(_telemetry_loop())
    if _network95_agent is not None:
        asyncio.create_task(_network95_agent.autonomous_loop())


async def _pulse_loop():
    """Push a live feed update to all WS clients every 8 seconds."""
    while True:
        await asyncio.sleep(8)
        try:
            top = feed.get_feed(limit=1)
            await manager.broadcast({
                "event": "feed_pulse",
                "payload": top[0] if top else {},
                "ts": time.time(),
            })
        except Exception as e:
            logger.debug(f"Pulse error: {e}")


async def _telemetry_loop():
    """Advance telemetry engines every 5 seconds and broadcast mindstate."""
    while True:
        await asyncio.sleep(5)
        if not (_mindstate and _aura and _roi):
            continue
        try:
            state, vec = _mindstate.sample()
            aura_snap  = _aura.sample()
            await manager.broadcast({
                "event": "telemetry_tick",
                "payload": {
                    "mindstate":    state.value,
                    "aura_pulse":   round(aura_snap.pulse_rate_hz, 3),
                    "aura_intensity": round(aura_snap.intensity, 3),
                    "alignment":    round(aura_snap.alignment_score, 3),
                    "trauma_index": round(aura_snap.trauma_index, 3),
                    "stress":       round(vec.stress, 3),
                    "flow":         round(vec.flow, 3),
                },
                "ts": time.time(),
            })
        except Exception as e:
            logger.debug(f"Telemetry loop error: {e}")


async def _sensing_loop():
    """Run a CSI simulation cycle every 15 seconds and post to feed."""
    if not _sensing:
        return
    while True:
        await asyncio.sleep(15)
        try:
            result = await _sensing.handle_task({
                "action": "simulate", "n": 40, "motion": True
            })
            last = result.get("last_analysis")
            if last and last.get("presence") == "occupied":
                post = feed.add_sensing_post(last)
                await manager.broadcast({
                    "event": "sensing_update",
                    "payload": {
                        "post_id": post.post_id,
                        "presence": last.get("presence"),
                        "breathing_bpm": last.get("breathing_rate_bpm"),
                        "motion": last.get("motion_detected"),
                        "confidence": last.get("presence_confidence"),
                    },
                    "ts": time.time(),
                })
        except Exception as e:
            logger.debug(f"Sensing loop error: {e}")


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = _static / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text())
    return HTMLResponse("<h1>ARK95X OmniNet</h1><p>Static files not found.</p>")


@app.get("/api/feed")
async def get_feed(
    limit: int = 20,
    post_type: Optional[str] = None,
    min_score: float = 0.0,
):
    return {"posts": feed.get_feed(limit=limit, post_type=post_type, min_council_score=min_score)}


@app.get("/api/stats")
async def get_stats():
    return {
        "feed": feed.stats(),
        "online_users": len(registry.all_online()),
        "ws_connections": len(manager.active),
        "sensing_active": _sensing is not None,
    }


class PostRequest(BaseModel):
    author_id: str = "ark95x"
    content: str
    post_type: str = "thought"


@app.post("/api/post")
async def create_post(req: PostRequest):
    ident = registry.get(req.author_id) or registry.get("ark95x")
    try:
        ptype = PostType(req.post_type)
    except ValueError:
        ptype = PostType.THOUGHT

    post = Post(
        author_id=ident.user_id if ident else req.author_id,
        author_handle=ident.handle if ident else f"@{req.author_id}",
        author_aura=ident.aura_color.value if ident else AuraColor.VIOLET.value,
        content=req.content,
        post_type=ptype,
    )
    saved = feed.add_post(post)
    registry.pulse(req.author_id)

    await manager.broadcast({
        "event": "new_post",
        "payload": {
            "post_id": saved.post_id,
            "author_handle": saved.author_handle,
            "author_aura": saved.author_aura,
            "content": saved.content,
            "post_type": saved.post_type.value,
            "timestamp_rel": "just now",
            "council_score": saved.council_score,
            "reactions": saved.reactions,
            "agent_tags": saved.agent_tags,
        },
        "ts": time.time(),
    })
    return {"status": "ok", "post_id": saved.post_id, "council_score": saved.council_score}


class ReactionRequest(BaseModel):
    post_id: str
    reaction: str  # resonate | amplify | question | ignite


@app.post("/api/react")
async def react(req: ReactionRequest):
    ok = feed.react(req.post_id, req.reaction)
    if not ok:
        raise HTTPException(404, "Post not found or invalid reaction")
    await manager.broadcast({"event": "reaction", "payload": req.dict(), "ts": time.time()})
    return {"status": "ok"}


@app.get("/api/identity/{user_id}")
async def get_identity(user_id: str):
    d = registry.to_dict(user_id)
    if not d:
        raise HTTPException(404, "Identity not found")
    return d


@app.get("/api/identities")
async def get_all_identities():
    return {"identities": [registry._to_dict(i) for i in registry.get_all()]}


@app.get("/api/agents")
async def get_agents():
    agents = [
        {"id": "Architect",      "color": "#06b6d4", "status": "online", "tasks": 31, "score": 0.94},
        {"id": "Auditor",        "color": "#f59e0b", "status": "online", "tasks": 28, "score": 0.97},
        {"id": "Debugger",       "color": "#dc2626", "status": "online", "tasks": 19, "score": 0.89},
        {"id": "Optimizer",      "color": "#10b981", "status": "online", "tasks": 22, "score": 0.91},
        {"id": "Learner",        "color": "#7c3aed", "status": "online", "tasks": 14, "score": 0.93},
        {"id": "WiFiSensing",    "color": "#06b6d4", "status": "online" if _sensing else "offline", "tasks": 12, "score": 0.88},
        {"id": "SovereignEngine","color": "#f59e0b", "status": "online", "tasks": 47, "score": 0.96},
        {"id": "HybridRouter",   "color": "#94a3b8", "status": "online", "tasks": 203,"score": 0.99},
        {"id": "CouncilCore",    "color": "#7c3aed", "status": "online", "tasks": 9,  "score": 0.95},
    ]
    return {"agents": agents}


@app.get("/api/sensing/latest")
async def sensing_latest():
    if not _sensing:
        return {"status": "offline", "message": "Sensing module not loaded"}
    result = await _sensing.handle_task({"action": "simulate", "n": 50, "motion": True})
    return result.get("last_analysis") or {"status": "insufficient_data"}


@app.get("/api/council")
async def council_status():
    import random
    voters = [
        {"name": "Perplexity", "role": "AUDITOR", "weight": 1.4, "status": "online", "last_verdict": "amplify"},
        {"name": "Gemini",     "role": "DRAFTER",  "weight": 1.2, "status": "online", "last_verdict": "amplify"},
        {"name": "Ollama",     "role": "SWING",    "weight": 1.0, "status": "online", "last_verdict": "neutral"},
        {"name": "Qwen",       "role": "SWING",    "weight": 1.0, "status": "online", "last_verdict": "amplify"},
        {"name": "DeepSeek",   "role": "SWING",    "weight": 1.0, "status": "online", "last_verdict": "amplify"},
        {"name": "ChatGPT",    "role": "SWING",    "weight": 0.9, "status": "online", "last_verdict": "neutral"},
        {"name": "LeChat",     "role": "SWING",    "weight": 0.9, "status": "online", "last_verdict": "amplify"},
        {"name": "Grok",       "role": "SWING",    "weight": 0.8, "status": "online", "last_verdict": "neutral"},
        {"name": "Claude",     "role": "ROTATED",  "weight": 0.0, "status": "rotated_out", "last_verdict": "—"},
    ]
    return {
        "voters": voters,
        "quorum_threshold": 5,
        "current_quorum": 8,
        "last_cycle": round(time.time() - random.randint(30, 300)),
        "cycles_completed": 47,
    }


# ── Telemetry routes ──────────────────────────────────────────────────────────

@app.get("/api/telemetry/mindstate")
async def tel_mindstate():
    if not _mindstate:
        return {"error": "telemetry offline"}
    _mindstate.sample()
    return {
        "current":     _mindstate.get_state(),
        "history":     _mindstate.get_history(n=80),
        "transitions": _mindstate.get_transitions(),
    }


@app.get("/api/telemetry/aura")
async def tel_aura():
    if not _aura:
        return {"error": "aura offline"}
    _aura.sample()
    return {
        "snapshot":  _aura.get_snapshot(),
        "series":    _aura.get_pulse_series(n=80),
        "trauma":    _aura.get_trauma_log(),
        "alignment": _aura.get_alignment_matrix(),
    }


@app.get("/api/telemetry/roi")
async def tel_roi():
    if not _roi:
        return {"error": "roi offline"}
    return {
        "snapshot": _roi.snapshot(),
        "ledger":   _roi.get_ledger(n=28),
    }


class TraumaRequest(BaseModel):
    description: str
    severity: float = 0.5


@app.post("/api/telemetry/trauma")
async def inject_trauma(req: TraumaRequest):
    if not _aura:
        return {"error": "aura offline"}
    ev = _aura.inject_trauma(req.description, req.severity)
    await manager.broadcast({
        "event": "trauma",
        "payload": {"id": ev.event_id, "severity": ev.severity, "desc": ev.description},
        "ts": time.time(),
    })
    return {"event_id": ev.event_id, "severity": ev.severity}


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_text(json.dumps({
            "event": "connected",
            "payload": {"msg": "ARK95X OmniNet live. Digital twin sync active."},
            "ts": time.time(),
        }))
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"event": "pong", "ts": time.time()}))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)
