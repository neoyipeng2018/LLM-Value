#!/usr/bin/env python3
"""Quick test to verify FMP API key and data format."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from afq.config import Config
from afq.utils import get_logger
from pipelines.stage2_roic_filter import FMPClient

log = get_logger("test_fmp")

TEST_TICKER = "AAPL"


def main():
    cfg = Config.load()
    try:
        cfg.validate_stage2()
    except ValueError as e:
        log.error(f"Config error: {e}")
        log.info("Make sure .env has FMP_API_KEY set.")
        return

    client = FMPClient(cfg)

    # Test 1: Key metrics endpoint
    log.info(f"Testing key-metrics endpoint for {TEST_TICKER}...")
    metrics = client.get_roic_history(TEST_TICKER, years=5)
    if metrics:
        log.info(f"Got {len(metrics)} years of data.")
        latest = metrics[0]
        roic = latest.get("roic")
        date = latest.get("date")
        log.info(f"  Latest: date={date}, ROIC={roic}")
        if roic is not None:
            log.info(f"  ROIC as percentage: {float(roic) * 100:.2f}%")
    else:
        log.error("No key metrics data returned. Check API key and plan limits.")
        return

    # Test 2: Earnings transcripts
    log.info(f"\nTesting earnings transcripts for {TEST_TICKER}...")
    transcripts = client.get_earnings_transcripts(TEST_TICKER, limit=1)
    if transcripts:
        t = transcripts[0]
        log.info(f"  Quarter: {t.get('quarter')} {t.get('year')}")
        content = t.get("content", "")
        log.info(f"  Content length: {len(content)} characters")
        log.info(f"  Preview: {content[:200]}...")
    else:
        log.warning("No transcripts returned (may require paid FMP plan).")

    client.close()
    log.info("\nFMP connection test complete.")


if __name__ == "__main__":
    main()
