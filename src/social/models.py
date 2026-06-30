"""ARK95X OmniNet — Social Platform Data Models"""
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class AuraColor(Enum):
    VIOLET   = "#7c3aed"
    GOLD     = "#f59e0b"
    CYAN     = "#06b6d4"
    CRIMSON  = "#dc2626"
    EMERALD  = "#10b981"
    SILVER   = "#94a3b8"


class PostType(Enum):
    THOUGHT     = "thought"
    INSIGHT     = "insight"       # AI-agent generated
    SENSING     = "sensing"       # from wifi sensing module
    COUNCIL     = "council"       # council decision
    MEMORY      = "memory"        # recalled from vector store
    MISSION     = "mission"       # crew mission log


class ReactionType(Enum):
    RESONATE   = "resonate"       # equivalent of like
    AMPLIFY    = "amplify"        # boost signal
    QUESTION   = "question"       # challenge / audit
    IGNITE     = "ignite"         # spark action


@dataclass
class DigitalIdentity:
    user_id: str
    handle: str
    display_name: str
    aura_color: AuraColor = AuraColor.VIOLET
    aura_intensity: float = 0.7       # 0.0 – 1.0
    consciousness_level: int = 1      # 1–9 (maps to council voter tiers)
    memory_vectors: int = 0           # embeddings stored in Qdrant
    missions_completed: int = 0
    crew: str = "purple_team"
    bio: str = ""
    signature_hash: str = ""          # digital flame / codex signature
    joined_ts: float = field(default_factory=time.time)
    online: bool = False
    twin_active: bool = False         # digital twin inference mode active

    def aura_css(self) -> str:
        color = self.aura_color.value
        intensity = int(self.aura_intensity * 100)
        return f"0 0 {intensity}px {color}, 0 0 {intensity*2}px {color}40"


@dataclass
class Post:
    post_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    author_id: str = ""
    author_handle: str = ""
    author_aura: str = AuraColor.VIOLET.value
    content: str = ""
    post_type: PostType = PostType.THOUGHT
    timestamp: float = field(default_factory=time.time)
    council_score: float = 0.0        # 0.0 – 1.0 voted by council
    reactions: Dict[str, int] = field(default_factory=lambda: {r.value: 0 for r in ReactionType})
    agent_tags: List[str] = field(default_factory=list)  # which agents processed this
    memory_depth: int = 0             # how deep in the consciousness stack
    thread_id: Optional[str] = None
    replies: List["Post"] = field(default_factory=list)
    sensing_data: Optional[Dict] = None  # attached CSI sensing snapshot
    pinned: bool = False


@dataclass
class CrewMission:
    mission_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    crew: str = "purple_team"
    agents_assigned: List[str] = field(default_factory=list)
    status: str = "active"           # active | complete | archived
    progress: float = 0.0            # 0.0 – 1.0
    created_ts: float = field(default_factory=time.time)
    output: Optional[str] = None


@dataclass
class CouncilVote:
    post_id: str
    voter: str
    weight: float
    verdict: str     # "amplify" | "archive" | "neutral"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SensingSnapshot:
    timestamp: float
    presence: str
    presence_confidence: float
    motion_detected: bool
    motion_intensity: float
    breathing_rate_bpm: Optional[float]
    location_hint: str = "unknown"    # room-level hint
