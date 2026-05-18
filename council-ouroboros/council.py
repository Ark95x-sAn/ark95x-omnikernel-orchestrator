"""
council-ouroboros / council.py
9-voter council with role rotation, weighted vote, and AUDITOR veto.

Roster (post-rotation 2026-05-18):
  - perplexity  : AUDITOR (veto holder, tie-breaker)
  - gemini      : DRAFTER
  - openai      : SWING
  - mistral     : SWING       (Le Chat, replaces claude in 9th seat)
  - qwen        : SWING
  - ollama      : LEARNER     (local, zero-cost)
  - deepseek    : SWING       (sign-in pending; disabled until creds)
  - xai         : SWING       (sign-in pending; disabled until creds)
  - google_pse  : SCANNER_AID

Claude rotated OUT 2026-05-18 14:00 CDT. Archived in Ledger v3.
"""
from __future__ import annotations
import json, os, logging
from collections import Counter
from dataclasses import dataclass
from router import Router, Voter

log = logging.getLogger("council")

ROSTER = [
    Voter(name="perplexity", role="AUDITOR", weight=1.5, enabled=True),
    Voter(name="gemini",     role="DRAFTER", weight=1.2, enabled=True),
    Voter(name="openai",     role="SWING",   weight=1.0, enabled=True),
    Voter(name="mistral",    role="SWING",   weight=1.0, enabled=True),
    Voter(name="qwen",       role="SWING",   weight=1.0, enabled=True),
    Voter(name="ollama",     role="LEARNER", weight=0.8, enabled=True),
    Voter(name="deepseek",   role="SWING",   weight=1.0, enabled=bool(os.getenv("DEEPSEEK_API_KEY"))),
    Voter(name="xai",        role="SWING",   weight=1.0, enabled=bool(os.getenv("XAI_API_KEY"))),
    Voter(name="google_pse", role="SCANNER_AID", weight=0.5, enabled=True),
]

QUORUM    = int(os.getenv("COUNCIL_QUORUM", "5"))
TIE_BREAK = os.getenv("COUNCIL_TIE_BREAKER", "perplexity")

@dataclass
class Decision:
    winner: str
    tally: dict
    veto: bool
    quorum_met: bool
    raw: list[dict]

def _parse(o: str | None) -> dict | None:
    if not o: return None
    try:
        s = o.strip()
        if s.startswith("```"): s = s.strip("`").split("\n", 1)[-1]
        return json.loads(s[s.find("{"): s.rfind("}")+1])
    except Exception as e:
        log.warning("unparseable voter output: %s", e)
        return None

async def vote(prompt: str) -> Decision:
    router = Router(ROSTER)
    raw = await router.broadcast(prompt)
    weighted: Counter = Counter()
    veto = False
    parsed_count = 0
    for r in raw:
        p = _parse(r["output"])
        if not p: continue
        parsed_count += 1
        choice = str(p.get("vote", "")).upper().strip()[:1]
        if choice in "ABCDE":
            weighted[choice] += r["weight"] * (p.get("confidence_0_100", 50) / 100.0)
        if r["voter"] == TIE_BREAK and p.get("auditor_veto_flag_bool"):
            veto = True
    quorum_met = parsed_count >= QUORUM
    if not weighted:
        return Decision(winner="", tally={}, veto=veto, quorum_met=quorum_met, raw=raw)
    top = weighted.most_common()
    # tie-break with AUDITOR
    if len(top) > 1 and top[0][1] == top[1][1]:
        aud = next((r for r in raw if r["voter"] == TIE_BREAK), None)
        if aud:
            p = _parse(aud["output"]) or {}
            choice = str(p.get("vote", "")).upper().strip()[:1]
            if choice in dict(top):
                return Decision(winner=choice, tally=dict(top), veto=veto, quorum_met=quorum_met, raw=raw)
    return Decision(winner=top[0][0], tally=dict(top), veto=veto, quorum_met=quorum_met, raw=raw)
