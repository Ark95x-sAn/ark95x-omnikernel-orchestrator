"""
performance_optimizer.py - Model Performance Optimization
ARK95X Omnikernel Orchestrator - Model Integration Layer

Hardware detection, model config optimization, batch sizing,
and real-time performance monitoring for local inference.
"""

import os
import platform
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class GPUInfo:
    name: str = "unknown"
    memory_total_gb: float = 0.0
    memory_free_gb: float = 0.0
    utilization_pct: float = 0.0


@dataclass
class HardwareSpecs:
    cpu_cores: int = 1
    ram_gb: float = 0.0
    gpus: List[GPUInfo] = field(default_factory=list)
    platform: str = ""
    has_cuda: bool = False


@dataclass
class ModelConfig:
    dtype: str = "float16"
    device_map: str = "auto"
    low_cpu_mem: bool = True
    quantization: Optional[str] = None  # '4bit', '8bit', None
    batch_size: int = 1
    max_seq_length: int = 4096
    context_window: int = 4096


@dataclass
class PerfSnapshot:
    timestamp: float
    cpu_pct: float
    ram_used_gb: float
    ram_total_gb: float
    gpu_util_pct: float
    gpu_mem_used_gb: float
    gpu_mem_total_gb: float
    model_name: str = ""
    inference_latency_ms: float = 0.0
    tokens_per_second: float = 0.0


def detect_hardware() -> HardwareSpecs:
    """Detect system hardware specifications."""
    specs = HardwareSpecs()
    specs.platform = platform.system()

    try:
        import psutil
        specs.cpu_cores = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        specs.ram_gb = round(mem.total / (1024 ** 3), 2)
    except ImportError:
        specs.cpu_cores = os.cpu_count() or 1

    # GPU detection via nvidia-smi or torch
    try:
        import torch
        if torch.cuda.is_available():
            specs.has_cuda = True
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                total_gb = round(props.total_mem / (1024 ** 3), 2)
                free_gb = round(torch.cuda.mem_get_info(i)[0] / (1024 ** 3), 2)
                specs.gpus.append(GPUInfo(
                    name=props.name,
                    memory_total_gb=total_gb,
                    memory_free_gb=free_gb,
                ))
    except ImportError:
        pass

    # Fallback: GPUtil
    if not specs.gpus:
        try:
            import GPUtil
            for gpu in GPUtil.getGPUs():
                specs.gpus.append(GPUInfo(
                    name=gpu.name,
                    memory_total_gb=round(gpu.memoryTotal / 1024, 2),
                    memory_free_gb=round(gpu.memoryFree / 1024, 2),
                    utilization_pct=gpu.load * 100,
                ))
        except ImportError:
            pass

    if not specs.gpus:
        specs.gpus.append(GPUInfo(name="CPU-only", memory_total_gb=specs.ram_gb))

    return specs


class ModelPerformanceOptimizer:
    """Optimizes model configs and monitors performance."""

    def __init__(self):
        self.hardware = detect_hardware()
        self.configs: Dict[str, ModelConfig] = {}
        self.snapshots: List[PerfSnapshot] = []
        self.max_snapshots = 1000

    def optimize_config(self, model_name: str, model_params_b: float = 7.0) -> ModelConfig:
        """Generate optimized model config based on hardware."""
        cfg = ModelConfig()
        total_gpu_mem = sum(g.memory_free_gb for g in self.hardware.gpus)
        has_gpu = self.hardware.has_cuda and total_gpu_mem > 2

        if not has_gpu:
            cfg.dtype = "float32"
            cfg.device_map = "cpu"
            cfg.quantization = "4bit" if model_params_b > 3 else None
            cfg.batch_size = 1
        elif total_gpu_mem < 8:
            cfg.dtype = "float16"
            cfg.quantization = "4bit"
            cfg.batch_size = 1
        elif total_gpu_mem < 16:
            cfg.dtype = "float16"
            cfg.quantization = "8bit" if model_params_b > 13 else None
            cfg.batch_size = 2
        elif total_gpu_mem < 32:
            cfg.dtype = "bfloat16"
            cfg.quantization = "8bit" if model_params_b > 30 else None
            cfg.batch_size = 4
        else:
            cfg.dtype = "bfloat16"
            cfg.quantization = None
            cfg.batch_size = 8

        # Context window based on memory
        if total_gpu_mem > 24:
            cfg.context_window = 32768
            cfg.max_seq_length = 32768
        elif total_gpu_mem > 12:
            cfg.context_window = 8192
            cfg.max_seq_length = 8192
        else:
            cfg.context_window = 4096
            cfg.max_seq_length = 4096

        self.configs[model_name] = cfg
        return cfg

    def get_batch_recommendation(self, model_name: str, seq_length: int) -> int:
        """Recommend batch size for given sequence length."""
        total_gpu = sum(g.memory_free_gb for g in self.hardware.gpus)
        if total_gpu <= 0:
            return 1

        mem_per_sample_gb = seq_length * 0.00001  # rough estimate
        max_batch = max(1, int(total_gpu / max(mem_per_sample_gb, 0.1)))
        return min(max_batch, 32)

    def take_snapshot(self, model_name: str = "") -> PerfSnapshot:
        """Capture current performance snapshot."""
        cpu_pct = 0.0
        ram_used = 0.0
        ram_total = self.hardware.ram_gb

        try:
            import psutil
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            ram_used = round(mem.used / (1024 ** 3), 2)
            ram_total = round(mem.total / (1024 ** 3), 2)
        except ImportError:
            pass

        gpu_util = 0.0
        gpu_mem_used = 0.0
        gpu_mem_total = 0.0

        try:
            import torch
            if torch.cuda.is_available():
                gpu_mem_used = round(torch.cuda.memory_allocated() / (1024 ** 3), 2)
                gpu_mem_total = sum(g.memory_total_gb for g in self.hardware.gpus)
        except ImportError:
            pass

        snap = PerfSnapshot(
            timestamp=time.time(),
            cpu_pct=cpu_pct,
            ram_used_gb=ram_used,
            ram_total_gb=ram_total,
            gpu_util_pct=gpu_util,
            gpu_mem_used_gb=gpu_mem_used,
            gpu_mem_total_gb=gpu_mem_total,
            model_name=model_name,
        )

        self.snapshots.append(snap)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        return snap

    def get_ollama_config(self, model_name: str) -> Dict[str, Any]:
        """Generate Ollama-specific runtime config."""
        cfg = self.configs.get(model_name) or self.optimize_config(model_name)
        total_gpu = sum(g.memory_free_gb for g in self.hardware.gpus)

        ollama_opts: Dict[str, Any] = {
            "num_ctx": cfg.context_window,
            "num_batch": min(512, cfg.context_window),
            "num_thread": max(1, self.hardware.cpu_cores // 2),
        }

        if total_gpu > 8:
            ollama_opts["num_gpu"] = 99  # offload all layers to GPU
        elif total_gpu > 4:
            ollama_opts["num_gpu"] = 20  # partial offload
        else:
            ollama_opts["num_gpu"] = 0  # CPU only

        return ollama_opts

    def get_summary(self) -> Dict[str, Any]:
        """Get optimizer summary."""
        return {
            "hardware": {
                "platform": self.hardware.platform,
                "cpu_cores": self.hardware.cpu_cores,
                "ram_gb": self.hardware.ram_gb,
                "has_cuda": self.hardware.has_cuda,
                "gpus": [
                    {"name": g.name, "total_gb": g.memory_total_gb, "free_gb": g.memory_free_gb}
                    for g in self.hardware.gpus
                ],
            },
            "configs": {k: vars(v) for k, v in self.configs.items()},
            "snapshots_count": len(self.snapshots),
        }
