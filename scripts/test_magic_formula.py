#!/usr/bin/env python3
"""Quick headed-browser test for Magic Formula login."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from afq.config import Config
from afq.utils import get_logger
from pipelines.stage1_magic_formula import login, run_screening, scrape_results

from playwright.sync_api import sync_playwright

log = get_logger("test_magic_formula")


def main():
    cfg = Config.load()
    try:
        cfg.validate_stage1()
    except ValueError as e:
        log.error(f"Config error: {e}")
        log.info("Make sure .env has MF_EMAIL and MF_PASSWORD set.")
        return

    log.info("Launching headed browser for visual verification...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()

        try:
            login(page, cfg)
            log.info("Login successful! Running screening...")
            run_screening(page, cfg)
            results = scrape_results(page)
            log.info(f"Found {len(results)} stocks.")
            if results:
                log.info(f"First result: {results[0]}")

            input("Press Enter to close browser...")
        except Exception as e:
            log.error(f"Test failed: {e}")
            input("Press Enter to close browser (inspect page for debugging)...")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
