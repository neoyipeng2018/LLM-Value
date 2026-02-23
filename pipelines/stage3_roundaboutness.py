"""Stage 3: 4-pass roundaboutness analysis using Claude.

Implements Spitznagel's Austrian economics lens with separate analysis of:
- Earnings call transcripts (Pass 1: evidence extraction, Pass 2: scoring)
- SEC filings 10-K + DEF 14A (Pass 3: evidence extraction, Pass 4: scoring)

Final verdict combines both transcript and filings scores.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import anthropic
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from afq.config import Config, DATA_DIR, PROJECT_ROOT
from afq.filing_fetcher import FilingData, fetch_filings
from afq.transcript_fetcher import fetch_transcript
from afq.utils import get_logger, load_json, save_csv, save_json

log = get_logger(__name__)

REFERENCE_DIR = PROJECT_ROOT / "reference"


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the reference directory."""
    path = REFERENCE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text()


# Prompt filenames
TRANSCRIPT_EXTRACT_PROMPT_FILE = "Transcript Evidence Extraction Prompt.md"
TRANSCRIPT_SCORE_PROMPT_FILE = "Transcript Scoring Prompt.md"
FILINGS_EXTRACT_PROMPT_FILE = "Filings Evidence Extraction Prompt.md"
FILINGS_SCORE_PROMPT_FILE = "Filings Scoring Prompt.md"


def _call_claude(
    client: anthropic.Anthropic,
    model: str,
    prompt: str,
    max_tokens: int = 4096,
) -> str:
    """Send a prompt to Claude and return the response text."""
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _parse_json_response(text: str) -> dict | None:
    """Try to parse JSON from Claude's response, handling code fences."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _extract_score_from_text(text: str, key: str = "TOTAL SCORE") -> int | None:
    """Extract a numeric score from structured text output."""
    import re

    # Look for patterns like "**TOTAL SCORE**: 7" or "TOTAL SCORE: +7"
    pattern = rf"\*?\*?{re.escape(key)}\*?\*?\s*:?\s*[+]?(-?\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_decision_from_text(text: str) -> str:
    """Extract PASS/WATCH/FAIL decision from text."""
    import re

    match = re.search(r"\*?\*?DECISION\*?\*?\s*:?\s*\*?\*?(PASS|WATCH|FAIL)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"


def _ensure_ticker_dir(ticker: str) -> Path:
    """Create and return the per-ticker output directory."""
    ticker_dir = DATA_DIR / "stage3" / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    return ticker_dir


def run_pass1_transcript_extraction(
    client: anthropic.Anthropic,
    model: str,
    ticker: str,
    company_name: str,
    transcript_text: str,
    ticker_dir: Path,
) -> str:
    """Pass 1: Extract evidence from earnings transcript."""
    prompt_template = _load_prompt(TRANSCRIPT_EXTRACT_PROMPT_FILE)

    # Fill in template variables
    prompt = prompt_template.replace("{COMPANY_NAME}", company_name)
    prompt = prompt.replace("{TICKER}", ticker)
    prompt = prompt.replace("{DATE}", "most recent")
    prompt += f"\n\n---\n\nTRANSCRIPT:\n{transcript_text}"

    response = _call_claude(client, model, prompt, max_tokens=4096)

    # Save raw output
    save_json(
        {"ticker": ticker, "pass": 1, "response": response},
        ticker_dir / "pass1_transcript_evidence.json",
    )
    return response


def run_pass2_transcript_scoring(
    client: anthropic.Anthropic,
    model: str,
    ticker: str,
    company_name: str,
    pass1_output: str,
    ticker_dir: Path,
) -> dict:
    """Pass 2: Score transcript evidence on 7 dimensions."""
    prompt_template = _load_prompt(TRANSCRIPT_SCORE_PROMPT_FILE)

    # Fill in template — the scoring prompt expects the Pass 1 output
    prompt = prompt_template.replace("{COMPANY_NAME}", company_name)
    prompt = prompt.replace("{TICKER}", ticker)
    prompt = prompt.replace("{DATE}", "most recent")
    prompt = prompt.replace("{PASTE PASS 1 OUTPUT HERE}", pass1_output)

    response = _call_claude(client, model, prompt, max_tokens=4096)

    # Try to parse structured data
    total_score = _extract_score_from_text(response)
    decision = _extract_decision_from_text(response)

    result = {
        "ticker": ticker,
        "pass": 2,
        "total_score": total_score,
        "decision": decision,
        "raw_response": response,
    }

    save_json(result, ticker_dir / "pass2_transcript_score.json")
    return result


def run_pass3_filings_extraction(
    client: anthropic.Anthropic,
    model: str,
    ticker: str,
    company_name: str,
    filing_data: FilingData,
    ticker_dir: Path,
) -> str:
    """Pass 3: Extract evidence from SEC filings."""
    prompt_template = _load_prompt(FILINGS_EXTRACT_PROMPT_FILE)

    filings_text = filing_data.combined_filings_text()

    # Fill in template
    prompt = prompt_template.replace("{COMPANY_NAME}", company_name)
    prompt = prompt.replace("{TICKER}", ticker)
    prompt = prompt.replace("{YEAR}", filing_data.tenk_date[:4] if filing_data.tenk_date else "latest")
    prompt += f"\n\n---\n\nFILINGS:\n{filings_text}"

    # Filings can be very long — truncate if needed
    max_prompt_chars = 180_000
    if len(prompt) > max_prompt_chars:
        prompt = prompt[:max_prompt_chars] + "\n\n[Filing text truncated]"

    response = _call_claude(client, model, prompt, max_tokens=6000)

    save_json(
        {"ticker": ticker, "pass": 3, "response": response},
        ticker_dir / "pass3_filings_evidence.json",
    )
    return response


def run_pass4_filings_scoring(
    client: anthropic.Anthropic,
    model: str,
    ticker: str,
    company_name: str,
    pass3_output: str,
    filing_data: FilingData,
    ticker_dir: Path,
) -> dict:
    """Pass 4: Score filings evidence on 8 dimensions."""
    prompt_template = _load_prompt(FILINGS_SCORE_PROMPT_FILE)

    dates = []
    if filing_data.tenk_date:
        dates.append(f"10-K: {filing_data.tenk_date}")
    if filing_data.proxy_date:
        dates.append(f"DEF 14A: {filing_data.proxy_date}")
    dates_str = "; ".join(dates) if dates else "latest"

    prompt = prompt_template.replace("{COMPANY_NAME}", company_name)
    prompt = prompt.replace("{TICKER}", ticker)
    prompt = prompt.replace("{DATES}", dates_str)
    prompt = prompt.replace("{PASTE PASS 1 OUTPUT HERE}", pass3_output)

    response = _call_claude(client, model, prompt, max_tokens=6000)

    total_score = _extract_score_from_text(response)
    decision = _extract_decision_from_text(response)

    result = {
        "ticker": ticker,
        "pass": 4,
        "total_score": total_score,
        "decision": decision,
        "raw_response": response,
    }

    save_json(result, ticker_dir / "pass4_filings_score.json")
    return result


def _combine_decisions(
    transcript_score: int | None,
    transcript_decision: str,
    filings_score: int | None,
    filings_decision: str,
) -> str:
    """Combine transcript and filings decisions into a final verdict.

    PASS: transcript >= +4 AND filings >= +5
    FAIL: either is FAIL
    WATCH: everything else
    """
    t_score = transcript_score if transcript_score is not None else 0
    f_score = filings_score if filings_score is not None else 0

    if t_score >= 4 and f_score >= 5:
        return "PASS"
    if transcript_decision == "FAIL" or filings_decision == "FAIL":
        return "FAIL"
    if t_score < 0 or f_score <= 0:
        return "FAIL"
    return "WATCH"


def analyze_ticker(
    ticker: str,
    cfg: Config,
    claude_client: anthropic.Anthropic,
) -> dict:
    """Run the full 4-pass analysis for a single ticker."""
    ticker_dir = _ensure_ticker_dir(ticker)
    company_name = ticker  # Will be updated from filings

    result = {
        "ticker": ticker,
        "company_name": company_name,
        "transcript_source": None,
        "transcript_chars": 0,
        "transcript_score": None,
        "transcript_decision": "UNKNOWN",
        "filings_tenk_date": None,
        "filings_proxy_date": None,
        "filings_score": None,
        "filings_decision": "UNKNOWN",
        "combined_decision": "UNKNOWN",
        "errors": [],
    }

    # --- Fetch data ---

    # Transcript
    log.info(f"  {ticker}: Fetching transcript...")
    transcript_text = fetch_transcript(ticker, fmp_api_key=cfg.fmp_api_key)
    result["transcript_chars"] = len(transcript_text)

    if transcript_text:
        result["transcript_source"] = "available"
        # Save raw transcript
        (ticker_dir / "transcript.txt").write_text(transcript_text)
    else:
        result["transcript_source"] = "none"
        result["errors"].append("No transcript available")

    # Filings
    log.info(f"  {ticker}: Fetching SEC filings...")
    filing_data = fetch_filings(ticker, edgar_identity=cfg.edgar_identity)
    result["company_name"] = filing_data.company_name or ticker
    company_name = result["company_name"]
    result["filings_tenk_date"] = filing_data.tenk_date
    result["filings_proxy_date"] = filing_data.proxy_date

    # Save raw filings
    if filing_data.mda:
        (ticker_dir / "filings_mda.txt").write_text(filing_data.mda)
    if filing_data.risk_factors:
        (ticker_dir / "filings_risk.txt").write_text(filing_data.risk_factors)
    if filing_data.business:
        (ticker_dir / "filings_business.txt").write_text(filing_data.business)
    if filing_data.proxy_text:
        (ticker_dir / "filings_proxy.txt").write_text(filing_data.proxy_text)

    if filing_data.errors:
        result["errors"].extend(filing_data.errors)

    # --- Pass 1 & 2: Transcript analysis ---

    if transcript_text:
        try:
            log.info(f"  {ticker}: Pass 1 - Extracting transcript evidence...")
            pass1_output = run_pass1_transcript_extraction(
                claude_client, cfg.claude_model, ticker, company_name,
                transcript_text, ticker_dir,
            )

            log.info(f"  {ticker}: Pass 2 - Scoring transcript...")
            pass2_result = run_pass2_transcript_scoring(
                claude_client, cfg.claude_model, ticker, company_name,
                pass1_output, ticker_dir,
            )

            result["transcript_score"] = pass2_result["total_score"]
            result["transcript_decision"] = pass2_result["decision"]

        except Exception as e:
            log.error(f"  {ticker}: Transcript analysis error: {e}")
            result["errors"].append(f"Transcript analysis error: {e}")
    else:
        log.warning(f"  {ticker}: Skipping transcript passes (no data)")

    # --- Pass 3 & 4: Filings analysis ---

    if filing_data.has_tenk() or filing_data.has_proxy():
        try:
            log.info(f"  {ticker}: Pass 3 - Extracting filings evidence...")
            pass3_output = run_pass3_filings_extraction(
                claude_client, cfg.claude_model, ticker, company_name,
                filing_data, ticker_dir,
            )

            log.info(f"  {ticker}: Pass 4 - Scoring filings...")
            pass4_result = run_pass4_filings_scoring(
                claude_client, cfg.claude_model, ticker, company_name,
                pass3_output, filing_data, ticker_dir,
            )

            result["filings_score"] = pass4_result["total_score"]
            result["filings_decision"] = pass4_result["decision"]

        except Exception as e:
            log.error(f"  {ticker}: Filings analysis error: {e}")
            result["errors"].append(f"Filings analysis error: {e}")
    else:
        log.warning(f"  {ticker}: Skipping filings passes (no data)")

    # --- Combine decisions ---

    result["combined_decision"] = _combine_decisions(
        result["transcript_score"],
        result["transcript_decision"],
        result["filings_score"],
        result["filings_decision"],
    )

    log.info(
        f"  {ticker}: T={result['transcript_score']}({result['transcript_decision']}) "
        f"F={result['filings_score']}({result['filings_decision']}) "
        f"=> {result['combined_decision']}"
    )

    return result


def run_stage3(cfg: Config, tickers: list[str] | None = None) -> list[dict]:
    """Run Stage 3: 4-pass roundaboutness analysis for all tickers.

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

    log.info(f"Stage 3: 4-pass roundaboutness analysis for {len(tickers)} tickers...")
    log.info(f"Tickers: {', '.join(tickers)}")

    claude_client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    results = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Analyzing...", total=len(tickers))

        for ticker in tickers:
            progress.update(task, description=f"Stage 3: {ticker}")

            try:
                result = analyze_ticker(ticker, cfg, claude_client)
                results.append(result)
            except Exception as e:
                log.error(f"  {ticker}: Fatal error - {e}")
                results.append({
                    "ticker": ticker,
                    "combined_decision": "ERROR",
                    "errors": [str(e)],
                })

            progress.advance(task)

    # Sort: PASS first, then WATCH, then FAIL/ERROR, then by filings score desc
    decision_order = {"PASS": 0, "WATCH": 1, "FAIL": 2, "ERROR": 3, "UNKNOWN": 4}
    results.sort(
        key=lambda r: (
            decision_order.get(r.get("combined_decision", "UNKNOWN"), 4),
            -(r.get("filings_score") or -99),
            -(r.get("transcript_score") or -99),
        )
    )

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = DATA_DIR / "stage3"

    save_json(results, output_dir / f"roundaboutness_{timestamp}.json")
    save_json(results, output_dir / "roundaboutness_latest.json")

    # Save CSV summary
    csv_rows = []
    for r in results:
        csv_rows.append({
            "ticker": r.get("ticker"),
            "company_name": r.get("company_name", ""),
            "transcript_score": r.get("transcript_score"),
            "transcript_decision": r.get("transcript_decision"),
            "filings_score": r.get("filings_score"),
            "filings_decision": r.get("filings_decision"),
            "combined_decision": r.get("combined_decision"),
            "transcript_chars": r.get("transcript_chars"),
            "filings_tenk_date": r.get("filings_tenk_date"),
            "filings_proxy_date": r.get("filings_proxy_date"),
            "errors": "; ".join(r.get("errors", [])),
        })
    save_csv(csv_rows, output_dir / f"roundaboutness_{timestamp}.csv")

    # Print summary
    log.info(f"\nStage 3 complete: {len(results)} tickers analyzed.")
    for r in results:
        t = r.get("transcript_score")
        f = r.get("filings_score")
        t_str = f"T={t:+d}" if t is not None else "T=N/A"
        f_str = f"F={f:+d}" if f is not None else "F=N/A"
        log.info(
            f"  {r['ticker']:6s} {t_str:8s} {f_str:8s} => {r.get('combined_decision', '?')}"
        )

    return results


if __name__ == "__main__":
    config = Config.load()
    results = run_stage3(config)
