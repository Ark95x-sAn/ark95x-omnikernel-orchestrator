#!/usr/bin/env python3
"""ARK95X Hybrid Router — 8-Layer Agentic AI Routing Engine
Routes requests across local (Ollama), cloud (OpenAI/Anthropic),
and MCP-connected models with privacy mode, fallback chains,
and reflection-loop integration.

Maps to the 8-Layer Agentic AI Architecture:
  L1: Infrastructure  L2: Agent Internet  L3: Tooling
  L4: Cognition       L5: Memory          L6: Application
  L7: Ops/Governance  L8: Strategic
"""
import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("ark95x.router")


@dataclass
class RouteDecision:
    provider: str
    model: str
    task_type: str
    priority: str
    privacy_mode: bool = False
    layer: int = 4


class HybridRouter:
    """Routes AI requests to optimal provider based on task, cost, privacy."""

    LOCAL_MODELS = {
        "llama3.1": {"type": "general", "speed": "fast", "quality": "good"},
        "mistral:7b": {"type": "reasoning", "speed": "fast", "quality": "good"},
        "phi3:3.8b": {"type": "coding", "speed": "very_fast", "quality": "moderate"},
        "deepseek-r1": {"type": "reasoning", "speed": "moderate", "quality": "excellent"},
    }

    CLOUD_MODELS = {
        "gpt-4": {"type": "advanced_reasoning", "speed": "moderate", "quality": "excellent"},
        "gpt-4o": {"type": "general", "speed": "fast", "quality": "excellent"},
        "claude-3.5-sonnet": {"type": "analysis", "speed": "fast", "quality": "excellent"},
        "claude-3-opus": {"type": "creative", "speed": "moderate", "quality": "excellent"},
    }

    def __init__(self, config: dict):
        self.config = config
        self.ollama_url = config.get("ollama_url", "http://localhost:11434")
        self.openai_key = config.get("openai_api_key", "")
        self.anthropic_key = config.get("anthropic_api_key", "")
        self.privacy_mode = config.get("privacy_mode", False)
        self.request_log: List[Dict] = []

    def route(self, prompt: str, task_type: str = "general",
             priority: str = "normal") -> RouteDecision:
        if self.privacy_mode or priority == "cost_sensitive":
            model = self._select_local(task_type)
            return RouteDecision("local", model, task_type, priority, True, 1)
        if self.openai_key or self.anthropic_key:
            model = self._select_cloud(task_type)
            return RouteDecision("cloud", model, task_type, priority, False, 4)
        model = self._select_local(task_type)
        return RouteDecision("fallback_local", model, task_type, priority, True, 1)

    def execute(self, route: RouteDecision, prompt: str) -> Dict[str, Any]:
        start = time.time()
        try:
            if route.provider in ("local", "fallback_local"):
                result = self._call_ollama(route.model, prompt)
            elif route.provider == "cloud" and "gpt" in route.model:
                result = self._call_openai(route.model, prompt)
            elif route.provider == "cloud" and "claude" in route.model:
                result = self._call_anthropic(route.model, prompt)
            else:
                result = self._call_ollama("llama3.1", prompt)
            result["duration_ms"] = round((time.time() - start) * 1000, 2)
            self._log_request(route, result)
            return result
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {"success": False, "error": str(e), "provider": route.provider}

    def _select_local(self, task_type: str) -> str:
        for model, info in self.LOCAL_MODELS.items():
            if info["type"] == task_type:
                return model
        return self.config.get("default_local_model", "llama3.1")

    def _select_cloud(self, task_type: str) -> str:
        for model, info in self.CLOUD_MODELS.items():
            if info["type"] == task_type:
                return model
        return self.config.get("default_cloud_model", "gpt-4o")

    def _call_ollama(self, model: str, prompt: str) -> Dict:
        r = requests.post(f"{self.ollama_url}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False,
            "options": {"temperature": self.config.get("temperature", 0.7),
                        "num_predict": self.config.get("max_tokens", 2048)}},
            timeout=120)
        if r.status_code == 200:
            data = r.json()
            return {"success": True, "provider": "local", "model": model,
                    "response": data.get("response", ""),
                    "tokens": data.get("eval_count", 0)}
        return {"success": False, "error": f"HTTP {r.status_code}"}

    def _call_openai(self, model: str, prompt: str) -> Dict:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_key}",
                     "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": self.config.get("temperature", 0.7),
                  "max_tokens": self.config.get("max_tokens", 2048)},
            timeout=120)
        if r.status_code == 200:
            data = r.json()
            return {"success": True, "provider": "openai", "model": model,
                    "response": data["choices"][0]["message"]["content"],
                    "tokens": data["usage"]["total_tokens"]}
        return {"success": False, "error": f"HTTP {r.status_code}"}

    def _call_anthropic(self, model: str, prompt: str) -> Dict:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.anthropic_key,
                     "Content-Type": "application/json",
                     "anthropic-version": "2023-06-01"},
            json={"model": model,
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": self.config.get("max_tokens", 2048)},
            timeout=120)
        if r.status_code == 200:
            data = r.json()
            return {"success": True, "provider": "anthropic", "model": model,
                    "response": data["content"][0]["text"],
                    "tokens": data.get("usage", {}).get("input_tokens", 0)}
        return {"success": False, "error": f"HTTP {r.status_code}"}

    def _log_request(self, route: RouteDecision, result: Dict):
        self.request_log.append({
            "timestamp": time.time(), "provider": route.provider,
            "model": route.model, "task_type": route.task_type,
            "success": result.get("success", False),
            "tokens": result.get("tokens", 0),
            "duration_ms": result.get("duration_ms", 0)})

    def get_stats(self) -> Dict:
        total = len(self.request_log)
        success = sum(1 for r in self.request_log if r["success"])
        return {"total_requests": total, "success_rate": success / max(total, 1),
                "providers_used": list(set(r["provider"] for r in self.request_log))}
