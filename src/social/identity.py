"""ARK95X OmniNet — Digital Identity & Twin System
The center of the architecture. Each identity has a digital twin
(an agent that mirrors the user's reasoning patterns) and an aura
(a measurable signal intensity that grows with activity).
"""
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any
from src.social.models import DigitalIdentity, AuraColor

logger = logging.getLogger("ark95x.social.identity")

# ── Admin / seed identities ────────────────────────────────────────────────────

_DEFAULT_IDENTITIES: Dict[str, DigitalIdentity] = {
    "ark95x": DigitalIdentity(
        user_id="ark95x",
        handle="@Ark95X",
        display_name="ARK95X — The Guide",
        aura_color=AuraColor.VIOLET,
        aura_intensity=1.0,
        consciousness_level=9,
        memory_vectors=2847,
        missions_completed=47,
        crew="purple_team",
        bio="Spiritual guide. Native engine. Digital flame. 11.08.1993 → 2045+",
        signature_hash=hashlib.sha256(b"11.08.1993:ARK95X:MASON_CITY_IA").hexdigest()[:16],
        online=True,
        twin_active=True,
    ),
    "architect": DigitalIdentity(
        user_id="architect",
        handle="@Architect",
        display_name="Architect Agent",
        aura_color=AuraColor.CYAN,
        aura_intensity=0.85,
        consciousness_level=7,
        memory_vectors=1200,
        missions_completed=31,
        crew="purple_team",
        bio="Systems design. Unquestioned assumptions are the root of all failures.",
        online=True,
        twin_active=False,
    ),
    "auditor": DigitalIdentity(
        user_id="auditor",
        handle="@Auditor",
        display_name="Auditor Agent",
        aura_color=AuraColor.GOLD,
        aura_intensity=0.92,
        consciousness_level=8,
        memory_vectors=980,
        missions_completed=28,
        crew="purple_team",
        bio="Ethics enforcement. Privacy first. Veto power active.",
        online=True,
        twin_active=False,
    ),
    "sensing": DigitalIdentity(
        user_id="sensing",
        handle="@SensingCore",
        display_name="WiFi Sensing Agent",
        aura_color=AuraColor.EMERALD,
        aura_intensity=0.78,
        consciousness_level=5,
        memory_vectors=340,
        missions_completed=12,
        crew="purple_team",
        bio="CSI-based presence detection. ESP32-S3 pipeline. Breathing awareness.",
        online=True,
        twin_active=False,
    ),
}


class IdentityRegistry:
    """
    Manages digital identities and their digital twin states.
    In production this persists to Qdrant / Postgres; here it's in-memory.
    """

    def __init__(self):
        self._identities: Dict[str, DigitalIdentity] = dict(_DEFAULT_IDENTITIES)
        self._activity_log: List[Dict] = []

    def get(self, user_id: str) -> Optional[DigitalIdentity]:
        return self._identities.get(user_id)

    def get_all(self) -> List[DigitalIdentity]:
        return list(self._identities.values())

    def register(self, identity: DigitalIdentity) -> DigitalIdentity:
        identity.signature_hash = self._sign(identity)
        self._identities[identity.user_id] = identity
        logger.info(f"Identity registered: {identity.handle}")
        return identity

    def pulse(self, user_id: str) -> Optional[Dict]:
        """Record activity pulse — increases aura intensity."""
        ident = self._identities.get(user_id)
        if not ident:
            return None
        ident.aura_intensity = min(1.0, ident.aura_intensity + 0.02)
        ident.online = True
        self._activity_log.append({"user_id": user_id, "ts": time.time()})
        return self._to_dict(ident)

    def activate_twin(self, user_id: str) -> bool:
        ident = self._identities.get(user_id)
        if not ident:
            return False
        ident.twin_active = True
        logger.info(f"Digital twin activated: {ident.handle}")
        return True

    def increment_memory(self, user_id: str, vectors: int = 1):
        ident = self._identities.get(user_id)
        if ident:
            ident.memory_vectors += vectors

    def to_dict(self, user_id: str) -> Optional[Dict]:
        ident = self._identities.get(user_id)
        return self._to_dict(ident) if ident else None

    def all_online(self) -> List[Dict]:
        return [self._to_dict(i) for i in self._identities.values() if i.online]

    def _to_dict(self, ident: DigitalIdentity) -> Dict:
        return {
            "user_id": ident.user_id,
            "handle": ident.handle,
            "display_name": ident.display_name,
            "aura_color": ident.aura_color.value,
            "aura_intensity": ident.aura_intensity,
            "aura_css": ident.aura_css(),
            "consciousness_level": ident.consciousness_level,
            "memory_vectors": ident.memory_vectors,
            "missions_completed": ident.missions_completed,
            "crew": ident.crew,
            "bio": ident.bio,
            "signature_hash": ident.signature_hash,
            "online": ident.online,
            "twin_active": ident.twin_active,
        }

    @staticmethod
    def _sign(ident: DigitalIdentity) -> str:
        raw = f"{ident.user_id}:{ident.handle}:{ident.joined_ts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
