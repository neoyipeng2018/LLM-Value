"""Stage 1: Magic Formula Investing screen via Playwright browser automation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from rich.progress import Progress, SpinnerColumn, TextColumn

from afq.config import Config, DATA_DIR
from afq.utils import get_logger, save_csv, save_json

log = get_logger(__name__)


def login(page: Page, cfg: Config) -> None:
    """Navigate to Magic Formula login page and authenticate."""
    log.info("Navigating to login page...")
    page.goto(cfg.mf_login_url, wait_until="networkidle")

    page.fill('input[name="Email"]', cfg.mf_email)
    page.fill('input[name="Password"]', cfg.mf_password)
    page.click('input[type="submit"]')

    # Wait for redirect after login
    page.wait_for_load_state("networkidle")

    # Verify login succeeded by checking we're not still on the login page
    if "/Account/LogOn" in page.url:
        raise RuntimeError(
            "Login failed - still on login page. Check MF_EMAIL and MF_PASSWORD."
        )
    log.info("Login successful.")


def run_screening(page: Page, cfg: Config) -> None:
    """Navigate to screening page and configure parameters."""
    log.info("Navigating to screening page...")
    page.goto(cfg.mf_screening_url, wait_until="networkidle")

    # Set minimum market cap
    min_cap_select = page.locator('select[name="MinimumMarketCap"]')
    if min_cap_select.count() > 0:
        # Try to select the closest option
        options = min_cap_select.locator("option").all()
        best_option = None
        for opt in options:
            val = opt.get_attribute("value")
            if val and val.isdigit() and int(val) >= cfg.mf_min_market_cap:
                best_option = val
                break
        if best_option:
            min_cap_select.select_option(best_option)
            log.info(f"Set minimum market cap to ${best_option}M")

    # Select number of stocks
    num_stocks_select = page.locator('select[name="NumStocks"]')
    if num_stocks_select.count() > 0:
        num_stocks_select.select_option(str(cfg.mf_top_n))
        log.info(f"Selected top {cfg.mf_top_n} stocks")

    # Submit the screening form
    submit_btn = page.locator('input[type="submit"][value="Get Stocks"]')
    if submit_btn.count() == 0:
        submit_btn = page.locator('input[type="submit"]')
    submit_btn.click()
    page.wait_for_load_state("networkidle")
    log.info("Screening submitted.")


def scrape_results(page: Page) -> list[dict]:
    """Parse the results table from the screening page."""
    results = []

    # Look for the results table
    table = page.locator("table.screeningdata, table.divScreeningResults table, #tabledata table, table")
    if table.count() == 0:
        log.warning("No results table found on the page.")
        return results

    # Use the first matching table that has data rows
    target_table = None
    for i in range(table.count()):
        t = table.nth(i)
        rows = t.locator("tr")
        if rows.count() > 1:  # header + at least one data row
            target_table = t
            break

    if target_table is None:
        log.warning("No table with data rows found.")
        return results

    rows = target_table.locator("tr").all()
    if len(rows) < 2:
        return results

    # Extract headers from the first row
    header_cells = rows[0].locator("th, td").all()
    headers = [cell.inner_text().strip().lower().replace(" ", "_") for cell in header_cells]

    # Map common header names
    header_map = {
        "company_name": "name",
        "company": "name",
        "ticker": "ticker",
        "symbol": "ticker",
        "market_cap_($mil)": "market_cap",
        "market_cap": "market_cap",
        "price_from_high": "price_from_high",
        "most_recent_quarter_data": "recent_quarter",
        "p/e": "pe_ratio",
    }

    normalized_headers = []
    for h in headers:
        normalized_headers.append(header_map.get(h, h))

    # Extract data rows
    for row in rows[1:]:
        cells = row.locator("td").all()
        if len(cells) < 2:
            continue

        values = [cell.inner_text().strip() for cell in cells]
        record = {}
        for j, val in enumerate(values):
            if j < len(normalized_headers):
                record[normalized_headers[j]] = val

        # Only add if we have a ticker
        if record.get("ticker") or record.get("name"):
            results.append(record)

    log.info(f"Scraped {len(results)} stocks from results table.")
    return results


def run_stage1(cfg: Config) -> list[dict]:
    """Run the complete Stage 1 pipeline: login, screen, scrape, save."""
    cfg.validate_stage1()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = DATA_DIR / "raw"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Stage 1: Magic Formula screening...", total=None)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=cfg.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            try:
                login(page, cfg)
                run_screening(page, cfg)
                results = scrape_results(page)
            finally:
                browser.close()

        progress.update(task, description="Stage 1: Saving results...")

    if not results:
        log.warning("No stocks found. Check credentials and site availability.")
        return results

    # Save outputs
    csv_path = output_dir / f"magic_formula_{timestamp}.csv"
    json_path = output_dir / f"magic_formula_{timestamp}.json"
    latest_path = output_dir / "magic_formula_latest.json"

    save_csv(results, csv_path)
    save_json(results, json_path)
    save_json(results, latest_path)

    log.info(f"Stage 1 complete: {len(results)} stocks saved to {output_dir}")
    return results


if __name__ == "__main__":
    config = Config.load()
    config.headless = False  # Run headed for debugging
    run_stage1(config)
