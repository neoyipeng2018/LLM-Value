"""Fetch SEC filings (10-K, DEF 14A) from EDGAR using edgartools.

Provides structured extraction of key filing sections for roundaboutness analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from edgar import Company, set_identity

from afq.utils import get_logger

log = get_logger(__name__)


@dataclass
class FilingData:
    """Structured SEC filing data for a company."""

    ticker: str
    company_name: str = ""
    # 10-K sections
    mda: str = ""  # Management Discussion & Analysis
    risk_factors: str = ""
    business: str = ""
    # DEF 14A
    proxy_text: str = ""
    # Metadata
    tenk_date: str = ""
    proxy_date: str = ""
    errors: list[str] = field(default_factory=list)

    def has_tenk(self) -> bool:
        return bool(self.mda or self.risk_factors or self.business)

    def has_proxy(self) -> bool:
        return bool(self.proxy_text)

    def combined_filings_text(self) -> str:
        """Combine all filing sections into a single text for analysis."""
        sections = []
        if self.business:
            sections.append(f"=== BUSINESS (10-K) ===\n{self.business}")
        if self.mda:
            sections.append(
                f"=== MANAGEMENT DISCUSSION & ANALYSIS (10-K) ===\n{self.mda}"
            )
        if self.risk_factors:
            sections.append(f"=== RISK FACTORS (10-K) ===\n{self.risk_factors}")
        if self.proxy_text:
            sections.append(f"=== PROXY STATEMENT (DEF 14A) ===\n{self.proxy_text}")
        return "\n\n".join(sections)


def _safe_str(obj: object, max_chars: int = 80_000) -> str:
    """Convert an edgartools object to string safely, with truncation.

    Returns empty string if obj is None or converts to 'None'.
    """
    if obj is None:
        return ""
    try:
        text = str(obj)
        if text == "None" or len(text) < 10:
            return ""
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Section truncated]"
        return text
    except Exception as e:
        return f"[Extraction error: {e}]"


def fetch_filings(ticker: str, edgar_identity: str) -> FilingData:
    """Fetch 10-K and DEF 14A filings from EDGAR for a given ticker.

    Args:
        ticker: Stock ticker symbol
        edgar_identity: Email address for SEC EDGAR User-Agent header

    Returns:
        FilingData with extracted filing sections
    """
    set_identity(edgar_identity)
    result = FilingData(ticker=ticker)

    try:
        company = Company(ticker)
        result.company_name = company.name or ticker
    except Exception as e:
        log.error(f"  {ticker}: Could not find company on EDGAR: {e}")
        result.errors.append(f"Company lookup failed: {e}")
        return result

    # Fetch 10-K (skip amendments like 10-K/A, prefer full 10-K)
    try:
        log.info(f"  {ticker}: Fetching 10-K from EDGAR...")
        tenk_filings = company.get_filings(form="10-K")
        if tenk_filings and len(tenk_filings) > 0:
            # Get recent filings and pick the first full 10-K (not 10-K/A)
            filing = None
            recent = tenk_filings.latest(5)  # returns EntityFilings collection
            for f in recent:
                if f.form == "10-K":
                    filing = f
                    break
            if filing is None:
                # Fall back to most recent even if it's an amendment
                filing = tenk_filings.latest(1)

            result.tenk_date = str(filing.filing_date)
            log.info(f"  {ticker}: 10-K ({filing.form}) dated {result.tenk_date}")

            # Try structured section extraction first
            try:
                tenk_obj = filing.obj()

                if hasattr(tenk_obj, "business"):
                    result.business = _safe_str(tenk_obj.business, 40_000)
                if hasattr(tenk_obj, "management_discussion"):
                    result.mda = _safe_str(tenk_obj.management_discussion, 60_000)
                elif hasattr(tenk_obj, "mda"):
                    result.mda = _safe_str(tenk_obj.mda, 60_000)
                if hasattr(tenk_obj, "risk_factors"):
                    result.risk_factors = _safe_str(tenk_obj.risk_factors, 50_000)
            except Exception as e:
                log.debug(f"  {ticker}: Structured 10-K parse failed: {e}")

            # If structured extraction failed, use full filing text
            if not result.mda and not result.risk_factors:
                log.info(f"  {ticker}: Structured extraction empty, using full 10-K text")
                try:
                    full_text = filing.text()
                    if full_text and len(full_text) > 100:
                        result.mda = full_text[:150_000]
                except Exception as e2:
                    result.errors.append(f"10-K text extraction failed: {e2}")
        else:
            log.warning(f"  {ticker}: No 10-K filings found")
            result.errors.append("No 10-K filings found")

    except Exception as e:
        log.error(f"  {ticker}: 10-K fetch error: {e}")
        result.errors.append(f"10-K fetch error: {e}")

    # Fetch DEF 14A (Proxy Statement)
    try:
        log.info(f"  {ticker}: Fetching DEF 14A from EDGAR...")
        proxy_filings = company.get_filings(form="DEF 14A")
        if proxy_filings and len(proxy_filings) > 0:
            proxy_filing = proxy_filings.latest(1)  # returns single EntityFiling
            result.proxy_date = str(proxy_filing.filing_date)
            log.info(f"  {ticker}: DEF 14A dated {result.proxy_date}")

            try:
                proxy_text = proxy_filing.text()
                if proxy_text:
                    if len(proxy_text) > 100_000:
                        proxy_text = proxy_text[:100_000] + "\n\n[Proxy truncated]"
                    result.proxy_text = proxy_text
            except Exception as e:
                log.warning(f"  {ticker}: Could not extract proxy text: {e}")
                result.errors.append(f"DEF 14A text extraction failed: {e}")
        else:
            log.warning(f"  {ticker}: No DEF 14A filings found")
            result.errors.append("No DEF 14A filings found")

    except Exception as e:
        log.error(f"  {ticker}: DEF 14A fetch error: {e}")
        result.errors.append(f"DEF 14A fetch error: {e}")

    # Log summary
    sections_found = []
    if result.business:
        sections_found.append(f"business({len(result.business)})")
    if result.mda:
        sections_found.append(f"mda({len(result.mda)})")
    if result.risk_factors:
        sections_found.append(f"risk({len(result.risk_factors)})")
    if result.proxy_text:
        sections_found.append(f"proxy({len(result.proxy_text)})")

    if sections_found:
        log.info(f"  {ticker}: Filing sections: {', '.join(sections_found)}")
    else:
        log.warning(f"  {ticker}: No filing sections extracted")

    return result
