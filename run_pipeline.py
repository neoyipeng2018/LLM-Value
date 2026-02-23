#!/usr/bin/env python3
"""AFQ Pipeline - Anti-Fragile Quality Investment Screening System.

Usage:
    python run_pipeline.py                    # Run all 3 stages
    python run_pipeline.py --stage 2          # Start from Stage 2 (uses saved Stage 1 data)
    python run_pipeline.py --stage 3          # Start from Stage 3 (uses saved Stage 2 data)
    python run_pipeline.py --headless false   # Run with visible browser
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
            "name": s1.get("name", ""),
            "market_cap": s1.get("market_cap", ""),
            # ROIC data
            "roic_avg": s2.get("avg"),
            "roic_trend": s2.get("trend"),
            "roic_min": s2.get("min"),
            "roic_max": s2.get("max"),
            # Roundaboutness data
            "roundaboutness_score": row.get("score"),
            "confidence": row.get("confidence"),
            "capex_stance": row.get("capex_stance"),
            "rd_trajectory": row.get("rd_trajectory"),
            "management_horizon": row.get("management_horizon"),
            "summary": row.get("summary", ""),
        }
        final.append(merged)

    # Sort by roundaboutness score descending
    final.sort(key=lambda r: r.get("roundaboutness_score") or -1, reverse=True)

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
    table.add_column("Name", width=25)
    table.add_column("ROIC Avg", justify="right", width=9)
    table.add_column("ROIC Trend", width=12)
    table.add_column("Roundabout", justify="right", width=10)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("CapEx", width=12)
    table.add_column("R&D", width=12)
    table.add_column("Horizon", width=11)

    for row in report:
        score = row.get("roundaboutness_score")
        score_str = f"{score:.1f}/10" if score is not None else "N/A"
        conf = row.get("confidence")
        conf_str = f"{conf:.0%}" if conf is not None else "N/A"
        roic = row.get("roic_avg")
        roic_str = f"{roic:.1f}%" if roic is not None else "N/A"

        table.add_row(
            str(row.get("rank", "")),
            row.get("ticker", ""),
            (row.get("name", "") or "")[:25],
            roic_str,
            row.get("roic_trend", ""),
            score_str,
            conf_str,
            row.get("capex_stance", ""),
            row.get("rd_trajectory", ""),
            row.get("management_horizon", ""),
        )

    console.print(table)

    # Print top picks summary
    top = [r for r in report if (r.get("roundaboutness_score") or 0) >= 7]
    if top:
        console.print(f"\n[bold green]Top picks (score >= 7.0):[/bold green]")
        for r in top:
            console.print(
                f"  [cyan]{r['ticker']}[/cyan] - "
                f"Score: {r['roundaboutness_score']:.1f}, "
                f"ROIC: {r.get('roic_avg', 'N/A')}%"
            )
            if r.get("summary"):
                console.print(f"    {r['summary'][:120]}")


def main():
    parser = argparse.ArgumentParser(
        description="AFQ Investment Screening Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stages:
  1  Magic Formula screen (requires MF_EMAIL, MF_PASSWORD)
  2  ROIC consistency filter (requires FMP_API_KEY)
  3  Roundaboutness analysis (requires FMP_API_KEY, ANTHROPIC_API_KEY)
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
    args = parser.parse_args()

    cfg = Config.load()
    cfg.headless = args.headless.lower() == "true"

    console.rule("[bold]AFQ Investment Screening Pipeline[/bold]")
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

        stage2_results = run_stage2(cfg)
        if not stage2_results:
            log.error("Stage 2: No stocks passed the ROIC filter. Aborting.")
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
