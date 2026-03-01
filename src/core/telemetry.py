"""ARK95X Telemetry Module
Real-time metrics collection, aggregation, and
performance monitoring with time-series storage.
"""
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger("ark95x.telemetry")


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class MetricSeries:
    name: str
    metric_type: MetricType
    points: deque = field(default_factory=lambda: deque(maxlen=10000))
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def latest(self) -> Optional[float]:
        return self.points[-1].value if self.points else None

    @property
    def avg(self) -> float:
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    @property
    def min_val(self) -> float:
        return min((p.value for p in self.points), default=0.0)

    @property
    def max_val(self) -> float:
        return max((p.value for p in self.points), default=0.0)


class TelemetryCollector:
    """Centralized metrics collection and aggregation."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.series: Dict[str, MetricSeries] = {}
        self.alerts: List[Dict[str, Any]] = []
        self._thresholds: Dict[str, Dict] = {}
        self._retention = self.config.get("retention_points", 10000)

    def _get_or_create(self, name: str, metric_type: MetricType) -> MetricSeries:
        if name not in self.series:
            self.series[name] = MetricSeries(
                name=name, metric_type=metric_type,
                points=deque(maxlen=self._retention)
            )
        return self.series[name]

    def increment(self, name: str, value: float = 1.0, **labels):
        s = self._get_or_create(name, MetricType.COUNTER)
        current = s.latest or 0.0
        point = MetricPoint(name=name, value=current + value, labels=labels, metric_type=MetricType.COUNTER)
        s.points.append(point)
        self._check_threshold(name, point.value)

    def gauge(self, name: str, value: float, **labels):
        s = self._get_or_create(name, MetricType.GAUGE)
        point = MetricPoint(name=name, value=value, labels=labels, metric_type=MetricType.GAUGE)
        s.points.append(point)
        self._check_threshold(name, value)

    def timer(self, name: str, duration: float, **labels):
        s = self._get_or_create(name, MetricType.TIMER)
        point = MetricPoint(name=name, value=duration, labels=labels, metric_type=MetricType.TIMER)
        s.points.append(point)
        self._check_threshold(name, duration)

    def histogram(self, name: str, value: float, **labels):
        s = self._get_or_create(name, MetricType.HISTOGRAM)
        point = MetricPoint(name=name, value=value, labels=labels, metric_type=MetricType.HISTOGRAM)
        s.points.append(point)

    def set_threshold(self, name: str, warn: Optional[float] = None, critical: Optional[float] = None):
        self._thresholds[name] = {"warn": warn, "critical": critical}

    def _check_threshold(self, name: str, value: float):
        t = self._thresholds.get(name)
        if not t:
            return
        if t.get("critical") and value >= t["critical"]:
            alert = {"metric": name, "value": value, "level": "critical", "time": time.time()}
            self.alerts.append(alert)
            logger.critical(f"ALERT [{name}]: {value} >= {t['critical']}")
        elif t.get("warn") and value >= t["warn"]:
            alert = {"metric": name, "value": value, "level": "warning", "time": time.time()}
            self.alerts.append(alert)
            logger.warning(f"WARN [{name}]: {value} >= {t['warn']}")

    def get_snapshot(self, window_seconds: float = 60.0) -> Dict[str, Any]:
        cutoff = time.time() - window_seconds
        snapshot = {}
        for name, s in self.series.items():
            recent = [p for p in s.points if p.timestamp >= cutoff]
            if recent:
                values = [p.value for p in recent]
                snapshot[name] = {
                    "type": s.metric_type.value,
                    "count": len(recent),
                    "latest": values[-1],
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
        return snapshot

    def get_dashboard(self) -> Dict[str, Any]:
        return {
            "total_series": len(self.series),
            "total_points": sum(len(s.points) for s in self.series.values()),
            "active_alerts": len([a for a in self.alerts if time.time() - a["time"] < 300]),
            "metrics": {
                name: {"latest": s.latest, "avg": s.avg, "type": s.metric_type.value}
                for name, s in self.series.items()
            },
        }
