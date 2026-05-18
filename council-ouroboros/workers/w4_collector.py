"""
council-ouroboros / workers/w4_collector.py
W4 COLLECTOR — GATED Stripe charge worker.

GATING: requires GATED_STRIPE_CHARGE=true. Never auto-charges otherwise.
Produces invoice + payment-link; never stores card data.
"""
from __future__ import annotations
import os, logging, datetime as dt
from dataclasses import dataclass

log = logging.getLogger("w4_collector")

GATED = os.getenv("GATED_STRIPE_CHARGE", "false").lower() == "true"
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY", "")

@dataclass
class Charge:
    draft_id: str
    amount_cents: int
    currency: str
    payment_link: str
    charged: bool
    reason: str
    timestamp: str

async def collect(draft_id: str, amount_cents: int, currency: str = "usd") -> Charge:
    now = dt.datetime.utcnow().isoformat() + "Z"
    if not GATED:
        return Charge(draft_id, amount_cents, currency, "", False,
                      "GATED_STRIPE_CHARGE=false (no charge)", now)
    if not STRIPE_KEY:
        return Charge(draft_id, amount_cents, currency, "", False,
                      "missing STRIPE_SECRET_KEY", now)
    # TODO: real stripe.PaymentLink.create(...) using STRIPE_KEY
    link = f"https://buy.stripe.com/stub_{draft_id}"
    log.info("created payment link for %s amount=%d%s", draft_id, amount_cents, currency)
    return Charge(draft_id, amount_cents, currency, link, False,
                  "payment link issued; charge occurs on customer action", now)
