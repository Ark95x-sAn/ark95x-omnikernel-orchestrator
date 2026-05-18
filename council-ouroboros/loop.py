"""
council-ouroboros / loop.py
Ouroboros cycle orchestrator. Each cycle:
  1. W0 scan → leads
  2. W1 draft  → drafts   (Gemini DRAFTER lead)
  3. W2 audit  → reports  (Perplexity AUDITOR veto)
  4. W3 file   → staged (GATED, never auto-submits)
  5. W4 collect→ payment links (GATED Stripe)
  6. W5 monitor→ metrics
  7. W6 learn  → reweight ROSTER

Run with: python loop.py
"""
from __future__ import annotations
import os, asyncio, logging
from router import Router
from council import ROSTER
from workers import w0_scanner, w1_drafter, w2_auditor, w3_filer, w4_collector, w5_monitor, w6_learner
import learning

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
log = logging.getLogger("loop")

INTERVAL = int(os.getenv("CYCLE_INTERVAL_SEC", "300"))

async def cycle(router: Router) -> None:
    leads = await w0_scanner.scan()
    drafts = []
    for lead in leads:
        for tmpl in ("answer_affirmative_defenses",):
            try:
                d = await w1_drafter.draft(lead.__dict__, tmpl)
                drafts.append(d.__dict__)
            except Exception as e:
                log.exception("draft failed: %s", e)
    audits = []
    vetos = 0
    for d in drafts:
        r = await w2_auditor.audit(d)
        audits.append(r.__dict__)
        if r.auditor_veto: vetos += 1
        for v in ROSTER:
            learning.observe(v.name, not r.auditor_veto)
    for d, a in zip(drafts, audits):
        await w3_filer.file_pleading(d, a)
        await w4_collector.collect(d["draft_id"], amount_cents=50000)
    w5_monitor.record_cycle(leads=len(leads), drafts=len(drafts), vetos=vetos)
    updates = w6_learner.learn(audits, [{"draft_id": d["draft_id"], "voter": "gemini"} for d in drafts])
    w6_learner.apply_updates(router, updates)

async def main() -> None:
    router = Router(ROSTER)
    log.info("council-ouroboros loop starting; interval=%ds, voters=%d", INTERVAL, len(router.voters))
    while True:
        try:
            await cycle(router)
        except Exception as e:
            log.exception("cycle failed: %s", e)
        await asyncio.sleep(INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
