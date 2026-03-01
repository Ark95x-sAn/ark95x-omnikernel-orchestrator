"""
local_model_manager.py - Local Model Inventory & Categorization
ARK95X Omnikernel Orchestrator - Model Integration Layer

Manages local model registry, capability matching, and task-to-model selection.
Designed for sovereign processing with Ollama-hosted models.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time


class ModelType(Enum):
    LANGUAGE = "language"
    MULTIMODAL = "multimodal"
    AUDIO = "audio"
    EMBEDDING = "embedding"
    CODE = "code"


class Performance(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


@dataclass
class ModelSpec:
    name: str
    model_type: ModelType
    capabilities: List[str]
    hardware_req: str
    performance: Performance
    use_case: str
    ollama_tag: str = ""
    context_window: int = 4096
    priority: int = 50
    loaded: bool = False
    last_used: float = 0.0
    total_requests: int = 0
    avg_latency_ms: float = 0.0


DEFAULT_MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "deepseek-r1": {
        "model_type": ModelType.LANGUAGE,
        "capabilities": ["reasoning", "analysis", "coding", "math", "planning"],
        "hardware_req": "GPU 16GB+",
        "performance": Performance.ULTRA,
        "use_case": "deep_reasoning",
        "ollama_tag": "deepseek-r1:latest",
        "context_window": 32768,
        "priority": 100,
    },
    "llama3.1-70b": {
        "model_type": ModelType.LANGUAGE,
        "capabilities": ["text_generation", "summarization", "qa", "reasoning", "coding"],
        "hardware_req": "GPU 48GB+",
        "performance": Performance.ULTRA,
        "use_case": "general_purpose",
        "ollama_tag": "llama3.1:70b",
        "context_window": 131072,
        "priority": 95,
    },
    "mixtral-8x7b": {
        "model_type": ModelType.LANGUAGE,
        "capabilities": ["text_generation", "reasoning", "coding", "analysis"],
        "hardware_req": "GPU 24GB+",
        "performance": Performance.HIGH,
        "use_case": "technical_tasks",
        "ollama_tag": "mixtral:8x7b",
        "context_window": 32768,
        "priority": 90,
    },
    "llama3.1-8b": {
        "model_type": ModelType.LANGUAGE,
        "capabilities": ["text_generation", "summarization", "qa", "chat"],
        "hardware_req": "GPU 8GB+",
        "performance": Performance.MEDIUM,
        "use_case": "general_purpose",
        "ollama_tag": "llama3.1:8b",
        "context_window": 131072,
        "priority": 80,
    },
    "mistral-7b": {
        "model_type": ModelType.LANGUAGE,
        "capabilities": ["reasoning", "coding", "analysis", "text_generation"],
        "hardware_req": "GPU 8GB+",
        "performance": Performance.HIGH,
        "use_case": "technical_tasks",
        "ollama_tag": "mistral:latest",
        "context_window": 8192,
        "priority": 75,
    },
    "phi3": {
        "model_type": ModelType.LANGUAGE,
        "capabilities": ["text_generation", "qa", "chat"],
        "hardware_req": "GPU 4GB+",
        "performance": Performance.MEDIUM,
        "use_case": "fast_inference",
        "ollama_tag": "phi3:latest",
        "context_window": 4096,
        "priority": 60,
    },
    "nomic-embed": {
        "model_type": ModelType.EMBEDDING,
        "capabilities": ["embedding", "semantic_search", "clustering"],
        "hardware_req": "GPU 4GB+",
        "performance": Performance.HIGH,
        "use_case": "vector_operations",
        "ollama_tag": "nomic-embed-text:latest",
        "context_window": 8192,
        "priority": 50,
    },
}


class LocalModelManager:
    """Manages local model inventory, scoring, and task routing."""

    def __init__(self, custom_registry: Optional[Dict[str, Dict]] = None):
        self.models: Dict[str, ModelSpec] = {}
        registry = custom_registry or DEFAULT_MODEL_REGISTRY
        for name, info in registry.items():
            self.models[name] = ModelSpec(name=name, **info)

    def register_model(self, name: str, spec: ModelSpec) -> None:
        self.models[name] = spec

    def unregister_model(self, name: str) -> bool:
        return self.models.pop(name, None) is not None

    def get_best_model_for_task(
        self, task_requirements: Dict[str, Any]
    ) -> Optional[Tuple[str, float, ModelSpec]]:
        """Select optimal local model based on task requirements."""
        task_type = task_requirements.get("type", "general")
        hardware = task_requirements.get("hardware", "gpu").lower()
        priority = task_requirements.get("priority", "normal")
        min_context = task_requirements.get("min_context_window", 0)
        required_perf = task_requirements.get("min_performance", None)

        candidates: List[Tuple[str, float, ModelSpec]] = []

        for name, spec in self.models.items():
            score = 0.0

            # Capability match
            if task_type in spec.capabilities:
                score += 3.0
            elif task_type == "general" and "text_generation" in spec.capabilities:
                score += 2.0

            # Hardware compatibility
            if hardware in spec.hardware_req.lower():
                score += 2.0

            # Performance tier
            perf_scores = {Performance.ULTRA: 4, Performance.HIGH: 3, Performance.MEDIUM: 2, Performance.LOW: 1}
            score += perf_scores.get(spec.performance, 0) * 0.5

            # Context window check
            if spec.context_window >= min_context:
                score += 1.0
            elif min_context > 0:
                continue  # Skip if context too small

            # Priority bonus
            score += spec.priority * 0.01

            # Recency bonus (recently used models are warm)
            if spec.loaded:
                score += 1.5

            # Performance filter
            if required_perf and perf_scores.get(spec.performance, 0) < perf_scores.get(Performance(required_perf), 0):
                continue

            if score > 0:
                candidates.append((name, score, spec))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0] if candidates else None

    def get_models_by_capability(self, capability: str) -> List[ModelSpec]:
        return [s for s in self.models.values() if capability in s.capabilities]

    def get_models_by_type(self, model_type: ModelType) -> List[ModelSpec]:
        return [s for s in self.models.values() if s.model_type == model_type]

    def mark_loaded(self, name: str) -> None:
        if name in self.models:
            self.models[name].loaded = True

    def mark_unloaded(self, name: str) -> None:
        if name in self.models:
            self.models[name].loaded = False

    def record_usage(self, name: str, latency_ms: float) -> None:
        if name not in self.models:
            return
        spec = self.models[name]
        spec.total_requests += 1
        spec.last_used = time.time()
        prev = spec.avg_latency_ms
        spec.avg_latency_ms = prev + (latency_ms - prev) / spec.total_requests

    def get_inventory(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for name, spec in self.models.items():
            result[name] = {
                "type": spec.model_type.value,
                "capabilities": spec.capabilities,
                "performance": spec.performance.value,
                "ollama_tag": spec.ollama_tag,
                "loaded": spec.loaded,
                "total_requests": spec.total_requests,
                "avg_latency_ms": round(spec.avg_latency_ms, 2),
                "priority": spec.priority,
            }
        return result

    def __repr__(self) -> str:
        loaded = sum(1 for s in self.models.values() if s.loaded)
        return f"LocalModelManager(total={len(self.models)}, loaded={loaded})"
