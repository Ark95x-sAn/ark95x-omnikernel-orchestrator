"""
council-ouroboros / router.py
Hybrid API + browser dispatch for LLM voters and workers.

Modes (ROUTER_MODE env):
  - api-only    : only providers with API keys are used
  - browser-only: only browser-tab voters are used (fallback)
  - hybrid      : prefer API; fall back to browser per-voter on failure
"""
from __future__ import annotations
import os, asyncio, logging, time
from dataclasses import dataclass
from typing import Callable, Awaitable, Optional

log = logging.getLogger("router")

@dataclass
class Voter:
    name: str
    role: str                # AUDITOR | DRAFTER | SCANNER | SWING | LEARNER | ...
    api_fn: Optional[Callable[[str], Awaitable[str]]] = None
    browser_fn: Optional[Callable[[str], Awaitable[str]]] = None
    weight: float = 1.0
    enabled: bool = True

class Router:
    def __init__(self, voters: list[Voter], mode: str | None = None):
        self.voters = [v for v in voters if v.enabled]
        self.mode = mode or os.getenv("ROUTER_MODE", "hybrid")
        self.timeout = int(os.getenv("COUNCIL_TIMEOUT_SEC", "45"))

    async def _call_one(self, v: Voter, prompt: str) -> tuple[str, str | None, float]:
        t0 = time.time()
        try:
            if self.mode in ("api-only", "hybrid") and v.api_fn:
                out = await asyncio.wait_for(v.api_fn(prompt), self.timeout)
                return v.name, out, time.time() - t0
            if self.mode in ("browser-only", "hybrid") and v.browser_fn:
                out = await asyncio.wait_for(v.browser_fn(prompt), self.timeout)
                return v.name, out, time.time() - t0
        except Exception as e:
            log.warning("voter %s failed primary path: %s", v.name, e)
            if self.mode == "hybrid" and v.browser_fn:
                try:
                    out = await asyncio.wait_for(v.browser_fn(prompt), self.timeout)
                    return v.name, out, time.time() - t0
                except Exception as e2:
                    log.error("voter %s browser fallback failed: %s", v.name, e2)
        return v.name, None, time.time() - t0

    async def broadcast(self, prompt: str) -> list[dict]:
        """Fan out to all voters in parallel; return list of {voter, output, latency}."""
        results = await asyncio.gather(*[self._call_one(v, prompt) for v in self.voters])
        return [
            {"voter": n, "output": o, "latency_sec": round(lat, 2), "weight": v.weight, "role": v.role}
            for (n, o, lat), v in zip(results, self.voters)
        ]

    def reweight(self, name: str, delta: float) -> None:
        for v in self.voters:
            if v.name == name:
                v.weight = max(0.0, v.weight + delta)
                log.info("reweight %s -> %.3f", name, v.weight)
                return
