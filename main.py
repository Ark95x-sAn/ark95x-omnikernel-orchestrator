#!/usr/bin/env python3
"""ARK95X OmniKernel Orchestrator - Main Entry Point
Full-scale self-learning sovereign AI system with ethical crew agents,
hybrid routing, MCP integration, and autonomous reflection.
"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# ── Core imports ──────────────────────────────────────────────────────────────
try:
    from src.core.sovereign_reflection_engine import SovereignReflectionEngine
except ImportError:
    SovereignReflectionEngine = None

try:
    from src.core.hybrid_router import HybridRouter
except ImportError:
    HybridRouter = None

try:
    from src.agents.ethical_crew_agents import EthicalCrewAgents
except ImportError:
    EthicalCrewAgents = None

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ark95x.log", mode="a"),
    ],
)
log = logging.getLogger("ARK95X")

BANNER = r"""
   ___    ____  _  ______  ____  _  __
  / _ |  / __ \| |/ / __ \/ __/ | |/ /
 / __ | / /_/ /   </_  __/_\ \  |   / 
/_/ |_|/_/ \__/_/|_| /_/ /___/ /_/|_| 
 OmniKernel Orchestrator  v2.0-sovereign
"""


class ARK95XOrchestrator:
    """Master orchestrator wiring all subsystems together."""

    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.reflection_engine = None
        self.hybrid_router = None
        self.crew_agents = None
        self.session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.memory: list = []
        log.info(f"ARK95X Orchestrator initialized | session={self.session_id}")

    def _load_config(self) -> dict:
        path = Path(self.config_path)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {
            "autonomy_level": 3,
            "preferred_model": "ollama/llama3",
            "fallback_models": ["openai/gpt-4o", "perplexity/sonar"],
            "ethical_mode": True,
            "self_learning": True,
            "mcp_enabled": True,
            "log_level": "INFO",
        }

    async def boot(self):
        """Boot all subsystems in order."""
        log.info("=== ARK95X BOOT SEQUENCE INITIATED ===")

        # 1. Hybrid Router
        if HybridRouter:
            self.hybrid_router = HybridRouter(
                preferred_model=self.config.get("preferred_model", "ollama/llama3"),
                fallback_models=self.config.get("fallback_models", []),
            )
            log.info("[BOOT] HybridRouter online")
        else:
            log.warning("[BOOT] HybridRouter not available")

        # 2. Sovereign Reflection Engine
        if SovereignReflectionEngine:
            self.reflection_engine = SovereignReflectionEngine(
                autonomy_level=self.config.get("autonomy_level", 3),
                router=self.hybrid_router,
            )
            log.info("[BOOT] SovereignReflectionEngine online")
        else:
            log.warning("[BOOT] SovereignReflectionEngine not available")

        # 3. Ethical Crew Agents
        if EthicalCrewAgents:
            self.crew_agents = EthicalCrewAgents(
                router=self.hybrid_router,
                ethical_mode=self.config.get("ethical_mode", True),
            )
            log.info("[BOOT] EthicalCrewAgents online")
        else:
            log.warning("[BOOT] EthicalCrewAgents not available")

        log.info("=== BOOT SEQUENCE COMPLETE ===")

    async def reflect(self, prompt: str) -> str:
        """Run sovereign reflection cycle on a prompt."""
        if self.reflection_engine:
            result = await self.reflection_engine.reflect(prompt)
        elif self.hybrid_router:
            result = await self.hybrid_router.route(prompt)
        else:
            result = f"[STUB] No engine available. Prompt received: {prompt}"
        self.memory.append({"ts": datetime.utcnow().isoformat(), "prompt": prompt, "result": result})
        return result

    async def run_crew_task(self, task: str) -> str:
        """Delegate a task to the ethical crew."""
        if self.crew_agents:
            return await self.crew_agents.execute(task)
        return f"[STUB] Crew not available. Task: {task}"

    async def self_improve(self):
        """Trigger autonomous self-improvement cycle."""
        if not self.config.get("self_learning", True):
            log.info("Self-learning disabled in config.")
            return
        log.info("[SELF-IMPROVE] Starting autonomous improvement cycle...")
        prompt = (
            "Review the ARK95X system memory and recent tasks. "
            "Identify patterns, gaps, and improvements. "
            "Output a prioritized improvement plan."
        )
        result = await self.reflect(prompt)
        log.info(f"[SELF-IMPROVE] Result: {result[:200]}...")
        return result

    async def interactive_loop(self):
        """Simple interactive REPL for direct orchestrator control."""
        print(BANNER)
        print(f"Session: {self.session_id}")
        print("Commands: reflect <prompt> | crew <task> | improve | status | quit\n")
        while True:
            try:
                line = input("ARK95X> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nShutting down ARK95X...")
                break
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                print("Goodbye.")
                break
            elif line.lower() == "status":
                self._print_status()
            elif line.lower() == "improve":
                result = await self.self_improve()
                print(f"\nImprovement Plan:\n{result}\n")
            elif line.lower().startswith("reflect "):
                prompt = line[8:]
                result = await self.reflect(prompt)
                print(f"\nReflection:\n{result}\n")
            elif line.lower().startswith("crew "):
                task = line[5:]
                result = await self.run_crew_task(task)
                print(f"\nCrew Result:\n{result}\n")
            else:
                print("Unknown command. Try: reflect <prompt> | crew <task> | improve | status | quit")

    def _print_status(self):
        print(f"""
=== ARK95X STATUS ===
Session     : {self.session_id}
Autonomy    : {self.config.get('autonomy_level', 'N/A')}
Router      : {'ONLINE' if self.hybrid_router else 'OFFLINE'}
Reflection  : {'ONLINE' if self.reflection_engine else 'OFFLINE'}
Crew        : {'ONLINE' if self.crew_agents else 'OFFLINE'}
Self-Learn  : {self.config.get('self_learning', False)}
Ethical Mode: {self.config.get('ethical_mode', False)}
Memory Items: {len(self.memory)}
====================""")


async def main():
    orchestrator = ARK95XOrchestrator()
    await orchestrator.boot()
    await orchestrator.interactive_loop()


if __name__ == "__main__":
    asyncio.run(main())
            
