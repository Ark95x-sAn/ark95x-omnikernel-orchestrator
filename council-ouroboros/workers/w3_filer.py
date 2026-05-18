"""
council-ouroboros / workers/w3_filer.py
W3 FILER — GATED court-filing submission.

GATING: requires GATED_FILING_SUBMIT=true AND human ack via Twilio SMS.
Never auto-files. Default behavior = stage + alert + wait.
"""
from __future__ import annotations
import os, logging, json, datetime as dt
from dataclasses import dataclass

log = logging.getLogger("w3_filer")

GATED = os.getenv("GATED_FILING_SUBMIT", "false").lower() == "true"
ALERT_SMS = os.getenv("ALERT_SMS_NUMBER", "")

@dataclass
class FilingResult:
    draft_id: str
    submitted: bool
    staged_path: str
    reason: str
    timestamp: str

async def _send_alert(msg: str) -> None:
    # Twilio outbound — only if creds present
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    tok = os.getenv("TWILIO_AUTH_TOKEN")
    if not (sid and tok and ALERT_SMS):
        log.info("alert (no-twilio): %s", msg)
        return
    # TODO: real twilio.rest.Client(sid, tok).messages.create(...)
    log.info("alert -> %s: %s", ALERT_SMS, msg)

async def file_pleading(draft: dict, audit: dict) -> FilingResult:
    now = dt.datetime.utcnow().isoformat() + "Z"
    if audit.get("auditor_veto"):
        return FilingResult(draft["draft_id"], False, "",
                            "blocked by AUDITOR veto", now)
    staged = f"./out/staged/{draft['draft_id']}.json"
    os.makedirs("./out/staged", exist_ok=True)
    with open(staged, "w") as f:
        json.dump({"draft": draft, "audit": audit, "staged_at": now}, f, indent=2)
    if not GATED:
        await _send_alert(f"FILING STAGED (not submitted): {draft['draft_id']}")
        return FilingResult(draft["draft_id"], False, staged,
                            "GATED_FILING_SUBMIT=false (staged only)", now)
    # GATED path: still requires explicit human ack downstream
    await _send_alert(
        f"FILING READY for human ack: {draft['draft_id']}. Reply YES to submit."
    )
    log.warning("W3 will NOT auto-submit; awaiting human ack for %s", draft["draft_id"])
    return FilingResult(draft["draft_id"], False, staged,
                        "awaiting human ack", now)
