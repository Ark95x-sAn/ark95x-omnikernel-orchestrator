"""ARK95X Pipeline Manager
DAG-based task pipeline with parallel execution,
dependency resolution, and streaming data flow.
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ark95x.pipeline")


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    name: str
    handler: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    status: StageStatus = StageStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    retries: int = 0
    max_retries: int = 2
    timeout: float = 300.0


@dataclass
class PipelineRun:
    run_id: str
    pipeline_name: str
    stages: Dict[str, PipelineStage] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "pending"


class PipelineManager:
    """DAG pipeline executor with parallel stage resolution."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.pipelines: Dict[str, List[PipelineStage]] = {}
        self.runs: Dict[str, PipelineRun] = {}
        self.max_parallel = self.config.get("max_parallel", 10)
        self._semaphore = asyncio.Semaphore(self.max_parallel)

    def define_pipeline(self, name: str, stages: List[PipelineStage]) -> None:
        self.pipelines[name] = stages
        logger.info(f"Pipeline defined: {name} ({len(stages)} stages)")

    def _resolve_order(self, stages: List[PipelineStage]) -> List[List[str]]:
        graph: Dict[str, Set[str]] = {}
        for s in stages:
            graph[s.name] = set(s.dependencies)
        levels = []
        resolved: Set[str] = set()
        while graph:
            ready = [n for n, deps in graph.items() if deps <= resolved]
            if not ready:
                remaining = list(graph.keys())
                logger.error(f"Circular dependency: {remaining}")
                raise ValueError(f"Circular dependency in {remaining}")
            levels.append(ready)
            resolved.update(ready)
            for n in ready:
                del graph[n]
        return levels

    async def execute(self, pipeline_name: str, context: Optional[Dict] = None) -> PipelineRun:
        stages_def = self.pipelines.get(pipeline_name)
        if not stages_def:
            raise KeyError(f"Pipeline not found: {pipeline_name}")

        run_id = f"{pipeline_name}_{int(time.time())}"
        stage_map = {s.name: PipelineStage(
            name=s.name, handler=s.handler,
            dependencies=list(s.dependencies),
            max_retries=s.max_retries, timeout=s.timeout
        ) for s in stages_def}

        run = PipelineRun(
            run_id=run_id, pipeline_name=pipeline_name,
            stages=stage_map, start_time=time.time(), status="running"
        )
        self.runs[run_id] = run
        ctx = context or {}
        ctx["__results__"] = {}

        try:
            levels = self._resolve_order(list(stage_map.values()))
            for level in levels:
                tasks = []
                for stage_name in level:
                    stage = stage_map[stage_name]
                    deps_ok = all(
                        stage_map[d].status == StageStatus.COMPLETED
                        for d in stage.dependencies
                    )
                    if not deps_ok:
                        stage.status = StageStatus.SKIPPED
                        continue
                    tasks.append(self._run_stage(stage, ctx))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            failed = [s for s in stage_map.values() if s.status == StageStatus.FAILED]
            run.status = "failed" if failed else "completed"
        except Exception as e:
            run.status = "error"
            logger.error(f"Pipeline {run_id} error: {e}")
        finally:
            run.end_time = time.time()

        logger.info(f"Pipeline {run_id} {run.status} in {run.end_time - run.start_time:.2f}s")
        return run

    async def _run_stage(self, stage: PipelineStage, ctx: Dict) -> None:
        async with self._semaphore:
            stage.status = StageStatus.RUNNING
            start = time.time()
            for attempt in range(stage.max_retries + 1):
                try:
                    if stage.handler:
                        result = await asyncio.wait_for(
                            stage.handler(ctx), timeout=stage.timeout
                        )
                        stage.result = result
                        ctx["__results__"][stage.name] = result
                    stage.status = StageStatus.COMPLETED
                    stage.duration = time.time() - start
                    return
                except asyncio.TimeoutError:
                    stage.error = f"Timeout after {stage.timeout}s"
                    stage.retries = attempt + 1
                except Exception as e:
                    stage.error = str(e)
                    stage.retries = attempt + 1
                    if attempt < stage.max_retries:
                        await asyncio.sleep(2 ** attempt)
            stage.status = StageStatus.FAILED
            stage.duration = time.time() - start
            logger.error(f"Stage {stage.name} failed: {stage.error}")

    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        run = self.runs.get(run_id)
        if not run:
            return {}
        return {
            "run_id": run.run_id,
            "status": run.status,
            "duration": run.end_time - run.start_time if run.end_time else 0,
            "stages": {
                k: {"status": v.status.value, "duration": v.duration}
                for k, v in run.stages.items()
            },
        }
