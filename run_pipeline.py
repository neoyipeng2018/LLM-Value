#!/usr/bin/env python3
"""AFQ Pipeline - Anti-Fragile Quality Investment Screening System.

Usage:
    python run_pipeline.py                    # Run all 3 stages
    python run_pipeline.py --stage 2          # Start from Stage 2 (uses saved Stage 1 data)
    python run_pipeline.py --stage 3          # Start from Stage 3 (uses saved Stage 2 data)
    python run_pipeline.py --headless false   # Run with visible browser
    python run_pipeline.py --demo             # Demo with known large-cap tickers (FMP free plan)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table

from afq.config import Config, DATA_DIR
from afq.utils import get_logger, load_json, save_csv, save_json

log = get_logger("afq")
console = Console()


def build_final_report(cfg: Config) -> list[dict]:
    """Merge Stage 1, 2, and 3 data into a ranked final report."""
    # Load all available data
    stage1_path = DATA_DIR / "raw" / "magic_formula_latest.json"
    stage2_path = DATA_DIR / "stage2" / "roic_passed_latest.json"
    stage3_path = DATA_DIR / "stage3" / "roundaboutness_latest.json"

    # Build lookup dicts
    stage1_lookup = {}
    if stage1_path.exists():
        for row in load_json(stage1_path):
            ticker = row.get("ticker", "").strip()
            if ticker:
                stage1_lookup[ticker] = row

    stage2_lookup = {}
    if stage2_path.exists():
        for row in load_json(stage2_path):
            ticker = row.get("ticker", "").strip()
            if ticker:
                stage2_lookup[ticker] = row

    # Stage 3 is the primary source (already filtered and ranked)
    if not stage3_path.exists():
        log.warning("Stage 3 results not found. Final report will be incomplete.")
        # Fall back to Stage 2 data
        if stage2_path.exists():
            return load_json(stage2_path)
        return []

    stage3_data = load_json(stage3_path)

    # Merge all stages
    final = []
    for row in stage3_data:
        ticker = row.get("ticker", "")
        s1 = stage1_lookup.get(ticker, {})
        s2 = stage2_lookup.get(ticker, {})

        merged = {
            "rank": len(final) + 1,
            "ticker": ticker,
            "name": row.get("company_name") or s1.get("name", ""),
            "market_cap": s1.get("market_cap", ""),
            # ROIC data
            "roic_avg": s2.get("avg"),
            "roic_trend": s2.get("trend"),
            "roic_min": s2.get("min"),
            "roic_max": s2.get("max"),
            # Roundaboutness data (4-pass)
            "transcript_score": row.get("transcript_score"),
            "transcript_decision": row.get("transcript_decision"),
            "filings_score": row.get("filings_score"),
            "filings_decision": row.get("filings_decision"),
            "combined_decision": row.get("combined_decision"),
        }
        final.append(merged)

    # Sort: PASS first, then WATCH, then FAIL
    decision_order = {"PASS": 0, "WATCH": 1, "FAIL": 2, "ERROR": 3, "UNKNOWN": 4}
    final.sort(
        key=lambda r: (
            decision_order.get(r.get("combined_decision", "UNKNOWN"), 4),
            -(r.get("filings_score") or -99),
            -(r.get("transcript_score") or -99),
        )
    )

    # Re-rank
    for i, row in enumerate(final):
        row["rank"] = i + 1

    return final


def print_summary(report: list[dict]) -> None:
    """Print a formatted summary table to the console."""
    if not report:
        console.print("[yellow]No results to display.[/yellow]")
        return

    table = Table(
        title="AFQ Investment Screening Results",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Ticker", style="bold cyan", width=8)
    table.add_column("Name", width=22)
    table.add_column("ROIC Avg", justify="right", width=9)
    table.add_column("ROIC Trend", width=10)
    table.add_column("T-Score", justify="right", width=8)
    table.add_column("T-Dec", width=6)
    table.add_column("F-Score", justify="right", width=8)
    table.add_column("F-Dec", width=6)
    table.add_column("Final", style="bold", width=6)

    for row in report:
        roic = row.get("roic_avg")
        roic_str = f"{roic:.1f}%" if roic is not None else "N/A"

        t_score = row.get("transcript_score")
        t_str = f"{t_score:+d}" if t_score is not None else "N/A"
        f_score = row.get("filings_score")
        f_str = f"{f_score:+d}" if f_score is not None else "N/A"

        decision = row.get("combined_decision", "?")
        decision_style = {
            "PASS": "bold green",
            "WATCH": "yellow",
            "FAIL": "red",
        }.get(decision, "dim")

        table.add_row(
            str(row.get("rank", "")),
            row.get("ticker", ""),
            (row.get("name", "") or "")[:22],
            roic_str,
            row.get("roic_trend", ""),
            t_str,
            row.get("transcript_decision", ""),
            f_str,
            row.get("filings_decision", ""),
            f"[{decision_style}]{decision}[/{decision_style}]",
        )

    console.print(table)

    # Print top picks summary
    passed = [r for r in report if r.get("combined_decision") == "PASS"]
    watched = [r for r in report if r.get("combined_decision") == "WATCH"]
    if passed:
        console.print(f"\n[bold green]PASS — proceed to position sizing:[/bold green]")
        for r in passed:
            console.print(
                f"  [cyan]{r['ticker']}[/cyan] — "
                f"T={r.get('transcript_score', 'N/A')}, "
                f"F={r.get('filings_score', 'N/A')}, "
                f"ROIC={r.get('roic_avg', 'N/A')}%"
            )
    if watched:
        console.print(f"\n[yellow]WATCH — needs more evidence:[/yellow]")
        for r in watched:
            console.print(
                f"  [cyan]{r['ticker']}[/cyan] — "
                f"T={r.get('transcript_score', 'N/A')}, "
                f"F={r.get('filings_score', 'N/A')}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="AFQ Investment Screening Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stages:
  1  Magic Formula screen (requires MF_EMAIL, MF_PASSWORD)
  2  ROIC consistency filter (requires FMP_API_KEY)
  3  Roundaboutness 4-pass analysis (requires ANTHROPIC_API_KEY, EDGAR_IDENTITY)
        """,
    )
    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Stage to start from (default: 1). Later stages load saved data.",
    )
    parser.add_argument(
        "--headless",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Run browser in headless mode (default: true)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo mode: skip Stage 1 and use known large-cap tickers compatible with FMP free plan",
    )
    args = parser.parse_args()

    cfg = Config.load()
    cfg.headless = args.headless.lower() == "true"

    console.rule("[bold]AFQ Investment Screening Pipeline[/bold]")

    # Demo mode: use known free-plan-compatible tickers
    if args.demo:
        log.info("Demo mode: using large-cap tickers (FMP free plan compatible)")
        demo_tickers = ["AAPL", "MSFT", "AMZN", "META", "NVDA"]
        args.stage = 2  # skip Stage 1

        # Save fake Stage 1 data for the final report
        from afq.utils import save_json as _save
        _save(
            [{"ticker": t, "name": t, "market_cap": ""} for t in demo_tickers],
            DATA_DIR / "raw" / "magic_formula_latest.json",
        )
    else:
        demo_tickers = None

    log.info(f"Starting from Stage {args.stage}")

    # Stage 1
    if args.stage <= 1:
        console.rule("Stage 1: Magic Formula Screening")
        from pipelines.stage1_magic_formula import run_stage1

        stage1_results = run_stage1(cfg)
        if not stage1_results:
            log.error("Stage 1 produced no results. Aborting.")
            sys.exit(1)

    # Stage 2
    if args.stage <= 2:
        console.rule("Stage 2: ROIC Consistency Filter")
        from pipelines.stage2_roic_filter import run_stage2

        stage2_results = run_stage2(cfg, tickers=demo_tickers)
        if not stage2_results:
            log.warning("Stage 2: No stocks passed the ROIC filter.")
            if not args.demo:
                log.info(
                    "Tip: FMP free plan only covers major stocks. "
                    "Use --demo to test with large-cap tickers, or upgrade your FMP plan."
                )
                sys.exit(1)

    # Stage 3
    if args.stage <= 3:
        console.rule("Stage 3: Roundaboutness Analysis")
        from pipelines.stage3_roundaboutness import run_stage3

        stage3_results = run_stage3(cfg)

    # Final report
    console.rule("Final Report")
    report = build_final_report(cfg)

    if report:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_dir = DATA_DIR / "final"
        save_json(report, final_dir / f"afq_report_{timestamp}.json")
        save_csv(
            [{k: v for k, v in r.items() if not isinstance(v, list)} for r in report],
            final_dir / f"afq_report_{timestamp}.csv",
        )
        save_json(report, final_dir / "afq_report_latest.json")
        log.info(f"Final report saved to {final_dir}")

    print_summary(report)


if __name__ == "__main__":
    main()
