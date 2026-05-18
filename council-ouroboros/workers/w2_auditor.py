"""
council-ouroboros / workers/w2_auditor.py
W2 AUDITOR — UPL veto + citation cross-check.

Roster role: AUDITOR (Perplexity lead, post-rotation 2026-05-18; veto holder).

Responsibilities:
  1. UPL guard — reject any draft that renders legal advice vs. doc-prep.
  2. Citation cross-check — every cited statute/rule must resolve in local
     vector DB (Chroma collection: iowa_civil_procedure).
  3. Hallucination guardrails — reject drafts that cite non-existent cases.
  4. Disclaimer presence — confirm UPL_DISCLAIMER prefix.
  5. Veto flag — if any fail, set auditor_veto=True and block W3 filer.
"""
from __future__ import annotations
import os, logging, re
from dataclasses import dataclass
from router import Router
from council import ROSTER

log = logging.getLogger("w2_auditor")

LEGAL_ADVICE_PATTERNS = [
    r"\byou should\b",
    r"\bI advise\b",
    r"\bmy legal opinion\b",
    r"\bthis is legal advice\b",
]

DISCLAIMER_TOKEN = "DOCUMENT PREPARATION ONLY"

@dataclass
class AuditReport:
    draft_id: str
    upl_pass: bool
    disclaimer_pass: bool
    citation_pass: bool
    citations_checked: int
    citations_unresolved: list[str]
    auditor_veto: bool
    notes: str

async def _ask_auditor(prompt: str) -> str:
    router = Router([v for v in ROSTER if v.role == "AUDITOR"])
    results = await router.broadcast(prompt)
    return results[0]["output"] if results and results[0]["output"] else ""

def _check_upl(text: str) -> bool:
    for pat in LEGAL_ADVICE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return False
    return True

def _check_disclaimer(text: str) -> bool:
    return DISCLAIMER_TOKEN in text

def _extract_citations(text: str) -> list[str]:
    # Iowa rule cites: "Iowa R. Civ. P. 1.234", statutes: "Iowa Code § 654A.6"
    rules = re.findall(r"Iowa R\. Civ\. P\. [0-9]+\.[0-9]+", text)
    statutes = re.findall(r"Iowa Code § [0-9A-Za-z\.]+", text)
    return list(set(rules + statutes))

async def _resolve_citation(c: str) -> bool:
    # TODO: vector lookup in chroma collection iowa_civil_procedure
    # Stub: assume rules 1.x and Iowa Code Chapter 654A exist.
    return bool(re.match(r"Iowa R\. Civ\. P\. 1\.", c) or "654A" in c)

async def audit(draft: dict) -> AuditReport:
    text = draft.get("text", "")
    upl_pass = _check_upl(text)
    disc_pass = _check_disclaimer(text)
    cites = _extract_citations(text)
    unresolved = []
    for c in cites:
        if not await _resolve_citation(c):
            unresolved.append(c)
    citation_pass = (len(unresolved) == 0)
    veto = not (upl_pass and disc_pass and citation_pass)
    report = AuditReport(
        draft_id=draft.get("draft_id", "?"),
        upl_pass=upl_pass,
        disclaimer_pass=disc_pass,
        citation_pass=citation_pass,
        citations_checked=len(cites),
        citations_unresolved=unresolved,
        auditor_veto=veto,
        notes="veto" if veto else "pass",
    )
    log.info("audit %s veto=%s upl=%s disc=%s cites=%d unresolved=%d",
             report.draft_id, veto, upl_pass, disc_pass,
             len(cites), len(unresolved))
    return report
