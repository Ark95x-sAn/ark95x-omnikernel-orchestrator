"""
council-ouroboros / workers/w0_scanner.py
W0 SCANNER — Iowa county foreclosure feed ingestion.

Targets (env IOWA_COUNTY_LIST, default 5 counties):
  Winnebago, Hancock, Cerro_Gordo, Wright, Franklin

Sources per county:
  - Iowa Courts Online (public docket search; respects robots.txt + ToS)
  - County sheriff sale notices (RSS where available, else weekly PDF)
  - County recorder NOD (Notice of Default) filings

Output: list[Lead] persisted to postgres `leads` table + emitted on bus.
Never scrapes paywalled or personal data. Public records only.
"""
from __future__ import annotations
import os, asyncio, logging, hashlib, datetime as dt
from dataclasses import dataclass, asdict
from typing import Iterable

log = logging.getLogger("w0_scanner")

COUNTIES = [c.strip() for c in os.getenv(
    "IOWA_COUNTY_LIST",
    "Winnebago,Hancock,Cerro_Gordo,Wright,Franklin"
).split(",") if c.strip()]

INTERVAL_MIN = int(os.getenv("FORECLOSURE_SCRAPE_INTERVAL_MIN", "60"))

@dataclass
class Lead:
    lead_id: str        # sha256(county|case_no|filed_date)[:16]
    county: str
    case_no: str
    filed_date: str     # ISO
    parties: str        # "Bank A v. Doe"
    property_addr: str  # public address from filing
    stage: str          # NOD | LIS_PENDENS | JUDGMENT | SALE
    source_url: str
    scraped_at: str

def _lead_id(county: str, case_no: str, filed: str) -> str:
    return hashlib.sha256(f"{county}|{case_no}|{filed}".encode()).hexdigest()[:16]

async def _fetch_county(county: str) -> list[Lead]:
    """Per-county adapter. Real impl plugs into iowacourts.gov + recorder feeds.
    Stub returns empty list; production overrides via adapters/<county>.py
    """
    log.info("scanning county=%s", county)
    # TODO: real HTTP adapter with rate-limit, robots.txt respect, cached ETag
    return []

async def scan() -> list[Lead]:
    batches = await asyncio.gather(*[_fetch_county(c) for c in COUNTIES])
    leads = [l for b in batches for l in b]
    log.info("w0_scanner produced %d leads across %d counties", len(leads), len(COUNTIES))
    return leads

async def loop() -> None:
    while True:
        try:
            leads = await scan()
            # downstream: emit to bus / persist to postgres (handled by loop.py)
            yield_count = len(leads)
            log.info("cycle complete, yielded=%d, sleep=%dm", yield_count, INTERVAL_MIN)
        except Exception as e:
            log.exception("scanner cycle failed: %s", e)
        await asyncio.sleep(INTERVAL_MIN * 60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(loop())
