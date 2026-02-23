"""Configuration management - loads .env and validates required keys."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data subdirectories exist
for sub in ("raw", "stage2", "stage3", "cache", "final"):
    (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)


@dataclass
class Config:
    """Central configuration loaded from environment variables."""

    mf_email: str = ""
    mf_password: str = ""
    fmp_api_key: str = ""
    anthropic_api_key: str = ""

    # Defaults
    headless: bool = True
    fmp_base_url: str = "https://financialmodelingprep.com/api/v3"
    cache_ttl_hours: int = 24
    fmp_rate_limit: float = 0.5  # seconds between requests
    claude_model: str = "claude-sonnet-4-20250514"

    # Magic Formula settings
    mf_login_url: str = "https://www.magicformulainvesting.com/Account/LogOn"
    mf_screening_url: str = "https://www.magicformulainvesting.com/Screening/StockScreening"
    mf_min_market_cap: int = 250  # millions
    mf_top_n: int = 50

    # ROIC filter thresholds
    roic_min_avg: float = 10.0  # percent
    roic_years: int = 10

    @classmethod
    def load(cls, env_path: Path | None = None) -> Config:
        """Load config from .env file and environment variables."""
        if env_path is None:
            env_path = PROJECT_ROOT / ".env"
        load_dotenv(env_path)

        return cls(
            mf_email=os.getenv("MF_EMAIL", ""),
            mf_password=os.getenv("MF_PASSWORD", ""),
            fmp_api_key=os.getenv("FMP_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )

    def validate_stage1(self) -> None:
        """Validate credentials needed for Stage 1."""
        missing = []
        if not self.mf_email:
            missing.append("MF_EMAIL")
        if not self.mf_password:
            missing.append("MF_PASSWORD")
        if missing:
            raise ValueError(f"Missing env vars for Stage 1: {', '.join(missing)}")

    def validate_stage2(self) -> None:
        """Validate credentials needed for Stage 2."""
        if not self.fmp_api_key:
            raise ValueError("Missing env var for Stage 2: FMP_API_KEY")

    def validate_stage3(self) -> None:
        """Validate credentials needed for Stage 3."""
        missing = []
        if not self.fmp_api_key:
            missing.append("FMP_API_KEY")
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise ValueError(f"Missing env vars for Stage 3: {', '.join(missing)}")
