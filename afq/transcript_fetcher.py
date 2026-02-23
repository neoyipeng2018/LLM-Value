"""Fetch earnings call transcripts from multiple sources.

Strategy:
1. Check for local TIKR PDF in data/transcripts/
2. Try Motley Fool scraping
3. Fallback to FMP API
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup

from afq.config import DATA_DIR
from afq.utils import get_logger

log = get_logger(__name__)

TIKR_PDF_DIR = DATA_DIR / "transcripts"
TIKR_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Known TIKR PDF filenames in ~/Downloads mapped to ticker
_TIKR_DOWNLOADS = Path.home() / "Downloads"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

FOOL_RATE_LIMIT = 1.5  # seconds between requests
_last_fool_request = 0.0


def _fool_wait() -> None:
    """Rate-limit Motley Fool requests."""
    global _last_fool_request
    now = time.time()
    elapsed = now - _last_fool_request
    if elapsed < FOOL_RATE_LIMIT:
        time.sleep(FOOL_RATE_LIMIT - elapsed)
    _last_fool_request = time.time()


def _find_tikr_pdf(ticker: str) -> Path | None:
    """Find a TIKR Terminal PDF for the given ticker.

    Checks data/transcripts/ first, then ~/Downloads.
    """
    # Check local data dir
    for pdf in TIKR_PDF_DIR.glob("*.pdf"):
        if ticker.upper() in pdf.name.upper():
            return pdf

    # Check Downloads
    for pdf in _TIKR_DOWNLOADS.glob("*TIKR Terminal*.pdf"):
        # Match ticker in filename like "MO US$59.46..." or "(MO)"
        name_upper = pdf.name.upper()
        # Match patterns: "MO US$" at start, or "(MO)" anywhere
        if (
            name_upper.startswith(f"{ticker.upper()} ")
            or f"({ticker.upper()})" in name_upper
        ):
            return pdf

    return None


def _extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def _fetch_from_tikr(ticker: str) -> str | None:
    """Try to read transcript from a TIKR Terminal PDF."""
    pdf_path = _find_tikr_pdf(ticker)
    if pdf_path is None:
        return None

    log.info(f"  Found TIKR PDF: {pdf_path.name}")
    text = _extract_pdf_text(pdf_path)

    if len(text) < 500:
        log.warning(f"  TIKR PDF too short ({len(text)} chars), skipping")
        return None

    return text


def _fetch_from_motley_fool(ticker: str) -> str | None:
    """Scrape the most recent earnings call transcript from Motley Fool."""
    # Step 1: Find transcript URLs from the transcripts listing page
    list_url = f"https://www.fool.com/quote/{ticker.upper()}/earnings-call-transcripts/"

    _fool_wait()
    try:
        resp = requests.get(list_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            log.debug(f"  Motley Fool listing returned {resp.status_code} for {ticker}")
            return None
    except requests.RequestException as e:
        log.debug(f"  Motley Fool request failed for {ticker}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find transcript links - they typically contain "earnings-call-transcript" in href
    transcript_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "earnings-call-transcript" in href and href not in transcript_links:
            transcript_links.append(href)

    if not transcript_links:
        log.debug(f"  No transcript links found on Motley Fool for {ticker}")
        return None

    # Take the most recent transcript (first in list)
    transcript_url = transcript_links[0]
    if not transcript_url.startswith("http"):
        transcript_url = f"https://www.fool.com{transcript_url}"

    log.info(f"  Found Motley Fool transcript: {transcript_url}")

    # Step 2: Fetch and extract the transcript page
    _fool_wait()
    try:
        resp = requests.get(transcript_url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            log.debug(f"  Transcript page returned {resp.status_code}")
            return None
    except requests.RequestException as e:
        log.debug(f"  Transcript page request failed: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract article content - Motley Fool uses article-body or similar containers
    content_div = (
        soup.find("div", class_=re.compile(r"article-body|tailwind-article-body"))
        or soup.find("div", {"class": "article-content"})
        or soup.find("article")
    )

    if content_div is None:
        # Try to find the main content area
        content_div = soup.find("div", class_=re.compile(r"content-body"))

    if content_div is None:
        log.debug(f"  Could not find article content for {ticker}")
        return None

    # Extract text, preserving paragraph structure
    paragraphs = content_div.find_all(["p", "h2", "h3"])
    text_parts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text:
            text_parts.append(text)

    full_text = "\n\n".join(text_parts)

    if len(full_text) < 1000:
        log.debug(f"  Motley Fool transcript too short ({len(full_text)} chars)")
        return None

    return full_text


def _fetch_from_fmp(ticker: str, fmp_api_key: str) -> str | None:
    """Fallback: fetch transcript from FMP API (limited on free plan)."""
    if not fmp_api_key:
        return None

    url = f"https://financialmodelingprep.com/stable/earning-call-transcript"
    params = {"symbol": ticker, "apikey": fmp_api_key}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data or not isinstance(data, list):
            return None

        # Concatenate most recent transcripts
        parts = []
        for t in data[:2]:  # last 2 quarters
            content = t.get("content", "")
            quarter = t.get("quarter", "?")
            year = t.get("year", "?")
            if content:
                parts.append(f"--- Q{quarter} {year} Earnings Call ---\n{content}")

        return "\n\n".join(parts) if parts else None

    except Exception as e:
        log.debug(f"  FMP transcript fetch failed for {ticker}: {e}")
        return None


def fetch_transcript(ticker: str, fmp_api_key: str = "") -> str:
    """Fetch earnings transcript using best available source.

    Priority:
    1. Local TIKR PDF
    2. Motley Fool scraping
    3. FMP API fallback

    Returns transcript text or empty string if unavailable.
    """
    # 1. TIKR PDF
    text = _fetch_from_tikr(ticker)
    if text:
        log.info(f"  {ticker}: Transcript from TIKR PDF ({len(text)} chars)")
        return text

    # 2. Motley Fool
    text = _fetch_from_motley_fool(ticker)
    if text:
        log.info(f"  {ticker}: Transcript from Motley Fool ({len(text)} chars)")
        return text

    # 3. FMP fallback
    text = _fetch_from_fmp(ticker, fmp_api_key)
    if text:
        log.info(f"  {ticker}: Transcript from FMP ({len(text)} chars)")
        return text

    log.warning(f"  {ticker}: No transcript found from any source")
    return ""
