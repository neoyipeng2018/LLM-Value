"""Shared utilities: logging, rate limiting, I/O helpers."""

from __future__ import annotations

import csv
import json
import logging
import time
from pathlib import Path

import pandas as pd
from rich.logging import RichHandler


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a logger with rich formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, show_path=False)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


class RateLimiter:
    """Simple rate limiter that ensures minimum delay between calls."""

    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self._last_call: float = 0.0

    def wait(self) -> None:
        """Block until enough time has passed since the last call."""
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.time()


def save_json(data: list | dict, path: Path) -> None:
    """Write data to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def load_json(path: Path) -> list | dict:
    """Read data from a JSON file."""
    return json.loads(path.read_text())


def save_csv(rows: list[dict], path: Path) -> None:
    """Write a list of dicts to a CSV file."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = rows[0].keys()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path) -> list[dict]:
    """Read a CSV file into a list of dicts."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def df_from_records(records: list[dict]) -> pd.DataFrame:
    """Create a DataFrame from a list of dicts."""
    return pd.DataFrame.from_records(records)
