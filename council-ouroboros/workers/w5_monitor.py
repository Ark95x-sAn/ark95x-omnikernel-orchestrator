"""
council-ouroboros / workers/w5_monitor.py
W5 MONITOR — prometheus metrics + drift alerting.

Exposes /metrics on PROMETHEUS_PORT (default 9090).
Tracks: cycle_count, lead_count, draft_count, audit_veto_rate, voter_latency.
"""
from __future__ import annotations
import os, logging, time
from dataclasses import dataclass, field

log = logging.getLogger("w5_monitor")

PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

@dataclass
class Metrics:
    cycle_count: int = 0
    lead_count: int = 0
    draft_count: int = 0
    veto_count: int = 0
    voter_latency_ms: dict = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

METRICS = Metrics()

def record_cycle(leads: int, drafts: int, vetos: int) -> None:
    METRICS.cycle_count += 1
    METRICS.lead_count += leads
    METRICS.draft_count += drafts
    METRICS.veto_count += vetos
    log.info("cycle %d — leads=%d drafts=%d vetos=%d",
             METRICS.cycle_count, leads, drafts, vetos)

def record_voter(name: str, latency_ms: float) -> None:
    METRICS.voter_latency_ms[name] = latency_ms

def veto_rate() -> float:
    if METRICS.draft_count == 0: return 0.0
    return METRICS.veto_count / METRICS.draft_count

def prometheus_text() -> str:
    lines = [
        f"council_cycle_total {METRICS.cycle_count}",
        f"council_leads_total {METRICS.lead_count}",
        f"council_drafts_total {METRICS.draft_count}",
        f"council_vetos_total {METRICS.veto_count}",
        f"council_veto_rate {veto_rate():.4f}",
        f"council_uptime_seconds {time.time() - METRICS.started_at:.0f}",
    ]
    for v, ms in METRICS.voter_latency_ms.items():
        lines.append(f'council_voter_latency_ms{{voter="{v}"}} {ms:.2f}')
    return "\n".join(lines) + "\n"
