"""
hybrid_router.py - Hybrid Local/Cloud Model Router
ARK95X Omnikernel Orchestrator - Model Integration Layer

Routes requests between local Ollama models and cloud APIs.
Privacy-first with cost optimization and offline fallback.
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class RoutingStrategy(Enum):
    LOCAL_FIRST = "local_first"
    CLOUD_FIRST = "cloud_first"
    COST_OPTIMIZED = "cost_optimized"
    PRIVACY_REQUIRED = "privacy_required"
    PERFORMANCE_FIRST = "performance_first"


@dataclass
class RoutingResult:
    success: bool
    provider: str  # 'local' or 'cloud'
    model: str
    response: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    error: str = ""
    cached: bool = False


@dataclass
class ModelEndpoint:
    name: str
    provider: str  # 'ollama', 'openai', 'anthropic', 'perplexity'
    endpoint: str
    api_key: str = ""
    model_id: str = ""
    cost_per_1k_tokens: float = 0.0
    max_tokens: int = 4096
    is_local: bool = False
    is_available: bool = True
    avg_latency_ms: float = 0.0
    total_requests: int = 0
    error_count: int = 0


class HybridModelRouter:
    """Routes inference between local and cloud models."""

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.ollama_host = ollama_host.rstrip("/")
        self.endpoints: Dict[str, ModelEndpoint] = {}
        self.response_cache: Dict[str, RoutingResult] = {}
        self.cache_ttl = 300  # 5 min TTL
        self.default_strategy = RoutingStrategy.LOCAL_FIRST
        self._init_local_endpoints()

    def _init_local_endpoints(self) -> None:
        """Register default Ollama local endpoints."""
        local_models = [
            ("deepseek-r1", "deepseek-r1:latest"),
            ("llama3.1-70b", "llama3.1:70b"),
            ("mixtral-8x7b", "mixtral:8x7b"),
            ("llama3.1-8b", "llama3.1:8b"),
            ("mistral-7b", "mistral:latest"),
            ("phi3", "phi3:latest"),
            ("nomic-embed", "nomic-embed-text:latest"),
        ]
        for name, model_id in local_models:
            self.endpoints[name] = ModelEndpoint(
                name=name,
                provider="ollama",
                endpoint=f"{self.ollama_host}/api/generate",
                model_id=model_id,
                cost_per_1k_tokens=0.0,
                is_local=True,
            )

    def register_cloud_endpoint(
        self, name: str, provider: str, api_key: str,
        model_id: str, cost_per_1k: float, endpoint: str = ""
    ) -> None:
        """Register a cloud model endpoint."""
        default_endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "anthropic": "https://api.anthropic.com/v1/messages",
            "perplexity": "https://api.perplexity.ai/chat/completions",
        }
        self.endpoints[name] = ModelEndpoint(
            name=name,
            provider=provider,
            endpoint=endpoint or default_endpoints.get(provider, ""),
            api_key=api_key,
            model_id=model_id,
            cost_per_1k_tokens=cost_per_1k,
            is_local=False,
        )

    def should_use_local(self, requirements: Dict[str, Any]) -> bool:
        """Determine if local processing is preferred."""
        privacy = requirements.get("privacy_required", False)
        offline = requirements.get("offline_capable", False)
        budget = requirements.get("budget", 1.0)
        strategy = requirements.get("strategy", self.default_strategy)

        if isinstance(strategy, str):
            strategy = RoutingStrategy(strategy)

        if strategy == RoutingStrategy.PRIVACY_REQUIRED:
            return True
        if strategy == RoutingStrategy.CLOUD_FIRST:
            return False
        if privacy or offline:
            return True
        if strategy == RoutingStrategy.COST_OPTIMIZED and budget < 0.05:
            return True
        return strategy == RoutingStrategy.LOCAL_FIRST

    def select_endpoint(self, requirements: Dict[str, Any]) -> Optional[ModelEndpoint]:
        """Select best endpoint based on requirements."""
        use_local = self.should_use_local(requirements)
        task_type = requirements.get("task_type", "general")

        candidates = [
            ep for ep in self.endpoints.values()
            if ep.is_available and ep.is_local == use_local
        ]

        if not candidates:
            # Fallback: try opposite locality
            candidates = [
                ep for ep in self.endpoints.values() if ep.is_available
            ]

        if not candidates:
            return None

        # Sort: prefer lower cost, then lower latency
        candidates.sort(
            key=lambda e: (e.cost_per_1k_tokens, e.avg_latency_ms)
        )
        return candidates[0]

    async def route_request(
        self, prompt: str, requirements: Dict[str, Any]
    ) -> RoutingResult:
        """Route request to optimal model."""
        # Check cache
        cache_key = self._cache_key(prompt, requirements)
        cached = self.response_cache.get(cache_key)
        if cached and not requirements.get("no_cache", False):
            cached.cached = True
            return cached

        endpoint = self.select_endpoint(requirements)
        if not endpoint:
            return RoutingResult(
                success=False, provider="none", model="none",
                error="No available endpoints"
            )

        if endpoint.is_local:
            result = await self._execute_local(endpoint, prompt, requirements)
        else:
            result = await self._execute_cloud(endpoint, prompt, requirements)

        # Update metrics
        endpoint.total_requests += 1
        if result.success:
            prev = endpoint.avg_latency_ms
            n = endpoint.total_requests
            endpoint.avg_latency_ms = prev + (result.latency_ms - prev) / n
        else:
            endpoint.error_count += 1

        # Cache successful results
        if result.success:
            self.response_cache[cache_key] = result

        return result

    async def _execute_local(
        self, endpoint: ModelEndpoint, prompt: str, req: Dict[str, Any]
    ) -> RoutingResult:
        """Execute via Ollama local API."""
        start = time.time()
        try:
            import aiohttp
            payload = {
                "model": endpoint.model_id,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": req.get("temperature", 0.7),
                    "num_predict": req.get("max_tokens", 500),
                },
            }
            if req.get("system_prompt"):
                payload["system"] = req["system_prompt"]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint.endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status != 200:
                        return RoutingResult(
                            success=False, provider="local",
                            model=endpoint.model_id,
                            error=f"Ollama returned {resp.status}",
                        )
                    data = await resp.json()

            latency = (time.time() - start) * 1000
            return RoutingResult(
                success=True,
                provider="local",
                model=endpoint.model_id,
                response=data.get("response", ""),
                tokens_used=data.get("eval_count", 0),
                cost=0.0,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RoutingResult(
                success=False, provider="local",
                model=endpoint.model_id,
                error=str(e), latency_ms=latency,
            )

    async def _execute_cloud(
        self, endpoint: ModelEndpoint, prompt: str, req: Dict[str, Any]
    ) -> RoutingResult:
        """Execute via cloud API."""
        start = time.time()
        try:
            import aiohttp
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {endpoint.api_key}",
            }
            payload = {
                "model": endpoint.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": req.get("max_tokens", 500),
                "temperature": req.get("temperature", 0.7),
            }
            if req.get("system_prompt"):
                payload["messages"].insert(
                    0, {"role": "system", "content": req["system_prompt"]}
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint.endpoint, json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        return RoutingResult(
                            success=False, provider="cloud",
                            model=endpoint.model_id,
                            error=f"Cloud API returned {resp.status}",
                        )
                    data = await resp.json()

            latency = (time.time() - start) * 1000
            response_text = ""
            tokens = 0
            if "choices" in data:
                response_text = data["choices"][0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)

            cost = (tokens / 1000) * endpoint.cost_per_1k_tokens
            return RoutingResult(
                success=True,
                provider="cloud",
                model=endpoint.model_id,
                response=response_text,
                tokens_used=tokens,
                cost=cost,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return RoutingResult(
                success=False, provider="cloud",
                model=endpoint.model_id,
                error=str(e), latency_ms=latency,
            )

    def _cache_key(self, prompt: str, req: Dict[str, Any]) -> str:
        import hashlib
        raw = f"{prompt}:{json.dumps(req, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get_status(self) -> Dict[str, Any]:
        local = [e for e in self.endpoints.values() if e.is_local]
        cloud = [e for e in self.endpoints.values() if not e.is_local]
        return {
            "local_endpoints": len(local),
            "cloud_endpoints": len(cloud),
            "cache_size": len(self.response_cache),
            "default_strategy": self.default_strategy.value,
            "endpoints": {
                name: {
                    "provider": ep.provider,
                    "is_local": ep.is_local,
                    "available": ep.is_available,
                    "requests": ep.total_requests,
                    "errors": ep.error_count,
                    "avg_latency_ms": round(ep.avg_latency_ms, 2),
                }
                for name, ep in self.endpoints.items()
            },
        }
