"""Stage 2: ROIC consistency filter using Financial Modeling Prep API.

Implements Spitznagel's Siegfried criterion - filters for companies with
consistently high, non-cyclical returns on invested capital.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from afq.cache import FileCache
from afq.config import Config, DATA_DIR
from afq.utils import RateLimiter, get_logger, load_json, save_csv, save_json

log = get_logger(__name__)


class FMPClient:
    """Rate-limited, cached HTTP client for Financial Modeling Prep API."""

    def __init__(self, cfg: Config):
        self.api_key = cfg.fmp_api_key
        self.base_url = cfg.fmp_base_url
        self.cache = FileCache(ttl_hours=cfg.cache_ttl_hours)
        self.limiter = RateLimiter(min_interval=cfg.fmp_rate_limit)
        self._client = httpx.Client(timeout=30.0)

    def get(self, endpoint: str, params: dict | None = None) -> list | dict:
        """Make a cached, rate-limited GET request to FMP API."""
        params = params or {}
        params["apikey"] = self.api_key

        cache_key = f"fmp:{endpoint}:{sorted(params.items())}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        self.limiter.wait()
        url = f"{self.base_url}/{endpoint}"
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        self.cache.set(cache_key, data)
        return data

    def get_roic_history(self, ticker: str, years: int = 10) -> list[dict]:
        """Fetch annual key metrics for ROIC data."""
        data = self.get(f"key-metrics/{ticker}", {"period": "annual", "limit": years})
        if isinstance(data, dict) and "Error Message" in data:
            log.warning(f"FMP error for {ticker}: {data['Error Message']}")
            return []
        return data if isinstance(data, list) else []

    def get_earnings_transcripts(
        self, ticker: str, limit: int = 4
    ) -> list[dict]:
        """Fetch recent earnings call transcripts."""
        data = self.get(f"earning_call_transcript/{ticker}", {"limit": limit})
        return data if isinstance(data, list) else []

    def close(self):
        self._client.close()


def analyze_roic(roic_values: list[float]) -> dict:
    """Compute ROIC statistics and trend classification.

    Returns dict with: avg, min, max, std, trend, trend_detail, passed
    """
    if not roic_values or len(roic_values) < 3:
        return {
            "avg": None,
            "min": None,
            "max": None,
            "std": None,
            "trend": "insufficient_data",
            "trend_detail": "Need at least 3 years of data",
            "passed": False,
        }

    arr = np.array(roic_values, dtype=float)
    avg = float(np.mean(arr))
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    std = float(np.std(arr))

    trend, detail = _classify_trend(arr)

    # Pass if avg ROIC >= threshold and trend is not cyclical or declining
    passed = avg >= 10.0 and trend in ("upward", "stable")

    return {
        "avg": round(avg, 2),
        "min": round(mn, 2),
        "max": round(mx, 2),
        "std": round(std, 2),
        "trend": trend,
        "trend_detail": detail,
        "passed": passed,
    }


def _classify_trend(values: np.ndarray) -> tuple[str, str]:
    """Classify ROIC trend using linear regression, direction changes, and max drawdown.

    Returns (trend_label, explanation).
    Trend labels: "upward", "stable", "cyclical", "declining"
    """
    n = len(values)
    x = np.arange(n, dtype=float)

    # Linear regression: slope
    slope, intercept = np.polyfit(x, values, 1)
    slope_pct_per_year = slope  # ROIC points per year

    # Count direction changes (sign changes in year-over-year diff)
    diffs = np.diff(values)
    sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
    reversal_ratio = sign_changes / max(len(diffs) - 1, 1)

    # Max drawdown from peak
    cummax = np.maximum.accumulate(values)
    drawdowns = cummax - values
    max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Classification logic
    if reversal_ratio > 0.6 and max_drawdown > 8:
        trend = "cyclical"
        detail = (
            f"High volatility: {sign_changes} reversals, "
            f"max drawdown {max_drawdown:.1f}pp"
        )
    elif slope_pct_per_year < -1.0:
        trend = "declining"
        detail = f"Declining at {slope_pct_per_year:.2f}pp/year"
    elif slope_pct_per_year > 0.5:
        trend = "upward"
        detail = f"Growing at +{slope_pct_per_year:.2f}pp/year"
    else:
        if max_drawdown > 10:
            trend = "cyclical"
            detail = f"Flat slope but max drawdown {max_drawdown:.1f}pp"
        else:
            trend = "stable"
            detail = f"Stable (slope {slope_pct_per_year:+.2f}pp/yr, drawdown {max_drawdown:.1f}pp)"

    return trend, detail


def run_stage2(cfg: Config, tickers: list[str] | None = None) -> list[dict]:
    """Run Stage 2: fetch ROIC data, analyze trends, filter stocks.

    If tickers is None, loads from Stage 1 latest output.
    """
    cfg.validate_stage2()

    # Load Stage 1 results if needed
    if tickers is None:
        latest_path = DATA_DIR / "raw" / "magic_formula_latest.json"
        if not latest_path.exists():
            raise FileNotFoundError(
                f"Stage 1 output not found at {latest_path}. Run Stage 1 first."
            )
        stage1_data = load_json(latest_path)
        tickers = [
            row.get("ticker", "").strip()
            for row in stage1_data
            if row.get("ticker", "").strip()
        ]

    if not tickers:
        log.warning("No tickers to process.")
        return []

    log.info(f"Stage 2: Analyzing ROIC for {len(tickers)} tickers...")
    client = FMPClient(cfg)
    results = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Fetching ROIC data...", total=len(tickers))

        for ticker in tickers:
            progress.update(task, description=f"ROIC: {ticker}")
            try:
                metrics = client.get_roic_history(ticker, years=cfg.roic_years)

                roic_values = []
                years_data = []
                for entry in metrics:
                    roic = entry.get("roic")
                    year = entry.get("date", "")[:4]
                    if roic is not None:
                        roic_values.append(float(roic) * 100)  # Convert to percentage
                        years_data.append(year)

                # Reverse so oldest first
                roic_values.reverse()
                years_data.reverse()

                analysis = analyze_roic(roic_values)
                result = {
                    "ticker": ticker,
                    "roic_years": len(roic_values),
                    "roic_values": roic_values,
                    "years": years_data,
                    **analysis,
                }
                results.append(result)

                status = "PASS" if analysis["passed"] else "FAIL"
                log.debug(
                    f"  {ticker}: avg={analysis['avg']}%, "
                    f"trend={analysis['trend']} -> {status}"
                )

            except Exception as e:
                log.warning(f"  {ticker}: Error fetching ROIC - {e}")
                results.append({
                    "ticker": ticker,
                    "roic_years": 0,
                    "roic_values": [],
                    "years": [],
                    "avg": None,
                    "trend": "error",
                    "trend_detail": str(e),
                    "passed": False,
                })

            progress.advance(task)

    client.close()

    # Separate pass/fail
    passed = [r for r in results if r["passed"]]
    failed = [r for r in results if not r["passed"]]

    log.info(f"Stage 2 complete: {len(passed)} passed, {len(failed)} filtered out.")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = DATA_DIR / "stage2"

    save_json(results, output_dir / f"roic_all_{timestamp}.json")
    save_json(passed, output_dir / "roic_passed_latest.json")

    # Save a readable CSV (without the roic_values list)
    csv_rows = [
        {k: v for k, v in r.items() if k not in ("roic_values", "years")}
        for r in results
    ]
    save_csv(csv_rows, output_dir / f"roic_analysis_{timestamp}.csv")

    return passed


if __name__ == "__main__":
    config = Config.load()
    passed = run_stage2(config)
    for r in passed:
        print(f"  {r['ticker']}: avg ROIC={r['avg']}%, trend={r['trend']}")
