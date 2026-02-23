"""Stage 3: Roundaboutness analysis of earnings transcripts via Claude.

Implements Spitznagel's Austrian economics lens - evaluating whether
companies invest in long-term, roundabout production processes (R&D,
moat-building, long-horizon capex) vs. short-term financial engineering
(buybacks, cost-cutting, dividend-maximizing).
"""

from __future__ import annotations

import json
from datetime import datetime

import anthropic
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from afq.config import Config, DATA_DIR
from afq.utils import get_logger, load_json, save_csv, save_json
from pipelines.stage2_roic_filter import FMPClient

log = get_logger(__name__)

ROUNDABOUTNESS_PROMPT = """\
You are an investment analyst applying Austrian economics principles, \
specifically Mark Spitznagel's concept of "roundaboutness" from his book \
"The Dao of Capital."

Roundaboutness measures how much a company invests in indirect, long-term \
productive capacity vs. short-term direct gains. High-roundaboutness companies:
- Invest heavily in R&D and innovation (building future moats)
- Make long-horizon capital expenditures (factories, infrastructure, platforms)
- Build durable competitive advantages even at short-term cost
- Prioritize market position and capability over immediate profitability
- Have management that thinks in decades, not quarters

Low-roundaboutness companies:
- Prioritize share buybacks and dividends over reinvestment
- Focus on cost-cutting and efficiency over growth
- Pursue short-term EPS management
- Make acquisitions primarily for financial engineering
- Show declining R&D as % of revenue

Analyze the following earnings call transcript(s) for {ticker} and evaluate \
the company's roundaboutness.

TRANSCRIPT(S):
{transcripts}

Respond with a JSON object (no markdown, no code fences) with exactly these fields:
{{
  "score": <float 0-10, where 10 is maximum roundaboutness>,
  "confidence": <float 0-1, your confidence in the assessment>,
  "key_evidence": [<list of 3-5 specific quotes or observations from the transcript>],
  "positive_signals": [<list of roundabout investment signals found>],
  "negative_signals": [<list of short-termism signals found>],
  "capex_stance": "<one of: aggressive_investment | moderate_investment | maintenance | reducing>",
  "rd_trajectory": "<one of: accelerating | steady | decelerating | minimal>",
  "management_horizon": "<one of: long_term | medium_term | short_term | unclear>",
  "summary": "<2-3 sentence summary of roundaboutness assessment>"
}}
"""


def fetch_recent_transcripts(
    client: FMPClient, ticker: str, quarters: int = 4
) -> str:
    """Fetch and concatenate recent earnings call transcripts."""
    transcripts = client.get_earnings_transcripts(ticker, limit=quarters)

    if not transcripts:
        return ""

    parts = []
    for t in transcripts:
        quarter = t.get("quarter", "?")
        year = t.get("year", "?")
        content = t.get("content", "")
        if content:
            parts.append(f"--- Q{quarter} {year} Earnings Call ---\n{content}")

    return "\n\n".join(parts)


def analyze_roundaboutness(
    transcript_text: str,
    ticker: str,
    cfg: Config,
) -> dict:
    """Send transcript to Claude for roundaboutness analysis."""
    if not transcript_text:
        return {
            "score": None,
            "confidence": 0,
            "key_evidence": [],
            "positive_signals": [],
            "negative_signals": [],
            "capex_stance": "unknown",
            "rd_trajectory": "unknown",
            "management_horizon": "unclear",
            "summary": "No transcript data available for analysis.",
            "error": "no_transcript",
        }

    # Truncate if too long (Claude context limit management)
    max_chars = 100_000
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars] + "\n\n[Transcript truncated]"

    prompt = ROUNDABOUTNESS_PROMPT.format(
        ticker=ticker,
        transcripts=transcript_text,
    )

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    message = client.messages.create(
        model=cfg.claude_model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Parse JSON response
    try:
        # Handle potential markdown code fences
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        result = json.loads(response_text)
    except json.JSONDecodeError:
        log.warning(f"Failed to parse Claude response as JSON for {ticker}")
        result = {
            "score": None,
            "confidence": 0,
            "summary": response_text[:500],
            "error": "json_parse_failed",
        }

    return result


def run_stage3(cfg: Config, tickers: list[str] | None = None) -> list[dict]:
    """Run Stage 3: fetch transcripts, analyze roundaboutness, rank results.

    If tickers is None, loads from Stage 2 passed output.
    """
    cfg.validate_stage3()

    # Load Stage 2 results if needed
    if tickers is None:
        passed_path = DATA_DIR / "stage2" / "roic_passed_latest.json"
        if not passed_path.exists():
            raise FileNotFoundError(
                f"Stage 2 output not found at {passed_path}. Run Stage 2 first."
            )
        stage2_data = load_json(passed_path)
        tickers = [
            row.get("ticker", "").strip()
            for row in stage2_data
            if row.get("ticker", "").strip()
        ]

    if not tickers:
        log.warning("No tickers to process.")
        return []

    log.info(f"Stage 3: Analyzing roundaboutness for {len(tickers)} tickers...")
    fmp_client = FMPClient(cfg)
    results = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Analyzing transcripts...", total=len(tickers))

        for ticker in tickers:
            progress.update(task, description=f"Roundaboutness: {ticker}")

            try:
                # Fetch transcripts
                transcript_text = fetch_recent_transcripts(fmp_client, ticker)
                transcript_chars = len(transcript_text)

                # Analyze with Claude
                analysis = analyze_roundaboutness(transcript_text, ticker, cfg)

                result = {
                    "ticker": ticker,
                    "transcript_chars": transcript_chars,
                    "transcript_quarters": transcript_text.count("Earnings Call"),
                    **analysis,
                }
                results.append(result)

                score = analysis.get("score")
                score_str = f"{score:.1f}" if score is not None else "N/A"
                log.info(
                    f"  {ticker}: score={score_str}/10, "
                    f"confidence={analysis.get('confidence', 0):.2f}"
                )

            except Exception as e:
                log.error(f"  {ticker}: Error - {e}")
                results.append({
                    "ticker": ticker,
                    "score": None,
                    "confidence": 0,
                    "summary": f"Error: {e}",
                    "error": str(e),
                })

            progress.advance(task)

    fmp_client.close()

    # Sort by score descending (None values last)
    results.sort(key=lambda r: r.get("score") or -1, reverse=True)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = DATA_DIR / "stage3"

    save_json(results, output_dir / f"roundaboutness_{timestamp}.json")
    save_json(results, output_dir / "roundaboutness_latest.json")

    # Save CSV summary (flatten for readability)
    csv_rows = []
    for r in results:
        csv_rows.append({
            "ticker": r.get("ticker"),
            "score": r.get("score"),
            "confidence": r.get("confidence"),
            "capex_stance": r.get("capex_stance"),
            "rd_trajectory": r.get("rd_trajectory"),
            "management_horizon": r.get("management_horizon"),
            "summary": r.get("summary", "")[:300],
        })
    save_csv(csv_rows, output_dir / f"roundaboutness_{timestamp}.csv")

    log.info(f"Stage 3 complete: {len(results)} stocks analyzed.")
    return results


if __name__ == "__main__":
    config = Config.load()
    results = run_stage3(config)
    print("\n=== Top Roundaboutness Scores ===")
    for r in results[:10]:
        score = r.get("score")
        if score is not None:
            print(f"  {r['ticker']}: {score:.1f}/10 - {r.get('summary', '')[:80]}")
