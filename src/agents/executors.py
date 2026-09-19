"""
NETWORK-95 Task Executors

Real execution adapters that back the EXECUTE stage.  Each executor targets
one device/service type from the routing plan and returns a structured result.

Executor contracts:
  - `async def run(task: dict, **kwargs) -> dict`
  - Return: {"status": "completed"|"failed", "output": ..., "duration_s": float}
  - Never raise — capture exceptions and surface as {"status": "failed", "error": ...}
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

log = logging.getLogger("network95.executors")

# ── Base ──────────────────────────────────────────────────────────────────────

class BaseExecutor:
    name: str = "base"

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def _result(self, output: Any, start: float) -> Dict[str, Any]:
        return {"status": "completed", "output": output, "duration_s": round(time.time() - start, 3)}

    def _error(self, exc: Exception, start: float) -> Dict[str, Any]:
        return {"status": "failed", "error": str(exc), "duration_s": round(time.time() - start, 3)}


# ── Ollama ────────────────────────────────────────────────────────────────────

class OllamaExecutor(BaseExecutor):
    """Runs inference against a local Ollama instance (localhost:11434)."""
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self._base_url = base_url
        self._model = model

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        prompt = task.get("prompt") or task.get("name", "")
        model = task.get("model") or self._model
        payload = {"model": model, "prompt": prompt, "stream": False}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return self._result(
                    {"response": data.get("response", ""), "model": model, "eval_count": data.get("eval_count")},
                    start,
                )
        except Exception as exc:
            log.warning("[OllamaExecutor] %s — %s", task.get("name"), exc)
            return self._error(exc, start)


# ── Embedding ─────────────────────────────────────────────────────────────────

class EmbeddingExecutor(BaseExecutor):
    """Generates embeddings via Ollama's /api/embeddings endpoint."""
    name = "embedding"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self._base_url = base_url
        self._model = model

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        text = task.get("text") or task.get("prompt") or task.get("name", "")
        model = task.get("model") or self._model
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                vec = data.get("embedding", [])
                return self._result({"dims": len(vec), "model": model, "embedding_preview": vec[:4]}, start)
        except Exception as exc:
            log.warning("[EmbeddingExecutor] %s — %s", task.get("name"), exc)
            return self._error(exc, start)


# ── n8n ───────────────────────────────────────────────────────────────────────

class N8nExecutor(BaseExecutor):
    """Triggers an n8n webhook workflow."""
    name = "n8n"

    def __init__(self, webhook_base: str = "http://localhost:5678/webhook"):
        self._webhook_base = webhook_base

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        workflow_id = task.get("workflow_id", "network95-default")
        url = f"{self._webhook_base}/{workflow_id}"
        payload = {k: v for k, v in task.items() if k not in ("type", "id")}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return self._result({"workflow_id": workflow_id, "response": resp.json()}, start)
        except Exception as exc:
            log.warning("[N8nExecutor] %s — %s", task.get("name"), exc)
            return self._error(exc, start)


# ── Docker ────────────────────────────────────────────────────────────────────

class DockerExecutor(BaseExecutor):
    """Runs a docker command via asyncio subprocess."""
    name = "docker"

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        image = task.get("image", "alpine")
        cmd_args = task.get("cmd", ["echo", "hello"])
        args = ["docker", "run", "--rm", image] + (cmd_args if isinstance(cmd_args, list) else [cmd_args])
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
            if proc.returncode != 0:
                raise RuntimeError(stderr.decode().strip() or f"exit {proc.returncode}")
            return self._result({"stdout": stdout.decode().strip(), "image": image}, start)
        except Exception as exc:
            log.warning("[DockerExecutor] %s — %s", task.get("name"), exc)
            return self._error(exc, start)


# ── Local subprocess ──────────────────────────────────────────────────────────

class LocalExecutor(BaseExecutor):
    """Runs a shell command locally via asyncio subprocess."""
    name = "local"

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        shell_cmd = task.get("cmd") or task.get("name", "echo ok")
        if not isinstance(shell_cmd, str):
            shell_cmd = " ".join(shell_cmd)
        try:
            proc = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            if proc.returncode != 0:
                raise RuntimeError(stderr.decode().strip() or f"exit {proc.returncode}")
            return self._result({"stdout": stdout.decode().strip()}, start)
        except Exception as exc:
            log.warning("[LocalExecutor] %s — %s", task.get("name"), exc)
            return self._error(exc, start)


# ── Inference (generic HTTP) ──────────────────────────────────────────────────

class InferenceExecutor(BaseExecutor):
    """Generic HTTP POST to any inference endpoint."""
    name = "inference"

    def __init__(self, endpoint: str = "http://localhost:8080/infer"):
        self._endpoint = endpoint

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        payload = {k: v for k, v in task.items() if k not in ("type", "id")}
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self._endpoint, json=payload)
                resp.raise_for_status()
                return self._result(resp.json(), start)
        except Exception as exc:
            log.warning("[InferenceExecutor] %s — %s", task.get("name"), exc)
            return self._error(exc, start)


# ── Registry ──────────────────────────────────────────────────────────────────

class ExecutorRegistry:
    """Maps task type → executor instance.  Falls back to LocalExecutor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self._map: Dict[str, BaseExecutor] = {
            "ollama":    OllamaExecutor(
                base_url=cfg.get("ollama_url", "http://localhost:11434"),
                model=cfg.get("ollama_model", "mistral"),
            ),
            "embedding": EmbeddingExecutor(
                base_url=cfg.get("ollama_url", "http://localhost:11434"),
                model=cfg.get("embed_model", "nomic-embed-text"),
            ),
            "n8n":       N8nExecutor(cfg.get("n8n_webhook_base", "http://localhost:5678/webhook")),
            "docker":    DockerExecutor(),
            "local":     LocalExecutor(),
            "inference": InferenceExecutor(cfg.get("inference_endpoint", "http://localhost:8080/infer")),
        }
        self._fallback = LocalExecutor()

    def get(self, task_type: str) -> BaseExecutor:
        return self._map.get(task_type, self._fallback)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        executor = self.get(task.get("type", "local"))
        log.debug("[Registry] task=%s type=%s → %s", task.get("id", "?")[:8], task.get("type"), executor.name)
        result = await executor.run(task)
        return {"task_id": task.get("id"), "task_name": task.get("name"), **result}
