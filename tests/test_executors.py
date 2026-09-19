"""Tests for the NETWORK-95 executor layer."""
import asyncio
import pytest

from src.agents.executors import (
    LocalExecutor, DockerExecutor, OllamaExecutor, EmbeddingExecutor,
    N8nExecutor, InferenceExecutor, ExecutorRegistry,
)


class TestLocalExecutor:

    @pytest.mark.asyncio
    async def test_runs_echo(self):
        ex = LocalExecutor()
        result = await ex.run({"name": "echo test", "cmd": "echo hello"})
        assert result["status"] == "completed"
        assert result["output"]["stdout"] == "hello"
        assert result["duration_s"] >= 0

    @pytest.mark.asyncio
    async def test_failed_command_returns_failed_status(self):
        ex = LocalExecutor()
        result = await ex.run({"name": "bad", "cmd": "false"})
        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_duration_present(self):
        ex = LocalExecutor()
        result = await ex.run({"name": "x", "cmd": "echo x"})
        assert isinstance(result["duration_s"], float)


class TestDockerExecutor:

    @pytest.mark.asyncio
    async def test_docker_missing_graceful_error(self):
        # In CI without Docker this should still return a "failed" dict, not raise.
        ex = DockerExecutor()
        result = await ex.run({"name": "docker test", "image": "alpine", "cmd": ["echo", "hi"]})
        assert result["status"] in ("completed", "failed")
        assert "duration_s" in result


class TestOllamaExecutor:

    @pytest.mark.asyncio
    async def test_connection_refused_returns_failed(self):
        ex = OllamaExecutor(base_url="http://localhost:19999")
        result = await ex.run({"name": "test", "prompt": "hello"})
        assert result["status"] == "failed"
        assert "error" in result


class TestEmbeddingExecutor:

    @pytest.mark.asyncio
    async def test_connection_refused_returns_failed(self):
        ex = EmbeddingExecutor(base_url="http://localhost:19999")
        result = await ex.run({"name": "embed", "text": "hello world"})
        assert result["status"] == "failed"


class TestN8nExecutor:

    @pytest.mark.asyncio
    async def test_connection_refused_returns_failed(self):
        ex = N8nExecutor(webhook_base="http://localhost:19999/webhook")
        result = await ex.run({"name": "workflow", "workflow_id": "test"})
        assert result["status"] == "failed"


class TestInferenceExecutor:

    @pytest.mark.asyncio
    async def test_connection_refused_returns_failed(self):
        ex = InferenceExecutor(endpoint="http://localhost:19999/infer")
        result = await ex.run({"name": "infer", "prompt": "hello"})
        assert result["status"] == "failed"


class TestExecutorRegistry:

    def test_get_known_types(self):
        reg = ExecutorRegistry()
        for task_type in ("ollama", "embedding", "n8n", "docker", "local", "inference"):
            ex = reg.get(task_type)
            assert ex is not None
            assert ex.name == task_type

    def test_get_unknown_falls_back_to_local(self):
        reg = ExecutorRegistry()
        ex = reg.get("totally_unknown_type_xyz")
        assert ex.name == "local"

    @pytest.mark.asyncio
    async def test_execute_wraps_result_with_task_id(self):
        reg = ExecutorRegistry()
        result = await reg.execute({"id": "t001", "name": "echo hi", "type": "local", "cmd": "echo hi"})
        assert result["task_id"] == "t001"
        assert result["task_name"] == "echo hi"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        reg = ExecutorRegistry()
        tasks = [
            {"id": f"t{i:03d}", "name": f"echo {i}", "type": "local", "cmd": f"echo {i}"}
            for i in range(5)
        ]
        results = await asyncio.gather(*[reg.execute(t) for t in tasks])
        assert all(r["status"] == "completed" for r in results)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_execute_never_raises(self):
        reg = ExecutorRegistry()
        # Even a broken executor should not propagate an exception
        result = await reg.execute({"id": "bad", "name": "bad cmd", "type": "local", "cmd": "exit 1"})
        assert result["status"] == "failed"
