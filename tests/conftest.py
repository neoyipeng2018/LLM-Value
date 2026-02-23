"""Shared fixtures for AFQ tests."""

import pytest
from pathlib import Path
import tempfile

from afq.cache import FileCache


@pytest.fixture
def tmp_cache(tmp_path):
    """Provide a FileCache backed by a temporary directory."""
    return FileCache(ttl_hours=24, cache_dir=tmp_path)


@pytest.fixture
def sample_roic_stable():
    """Sample ROIC values: stable high performer."""
    return [18.2, 19.1, 17.8, 18.5, 19.0, 18.3, 19.5, 18.8, 19.2, 18.9]


@pytest.fixture
def sample_roic_upward():
    """Sample ROIC values: steadily improving."""
    return [10.0, 12.5, 14.0, 15.5, 17.0, 18.5, 20.0, 21.5, 23.0, 24.5]


@pytest.fixture
def sample_roic_cyclical():
    """Sample ROIC values: volatile, cyclical pattern."""
    return [20.0, 8.0, 22.0, 5.0, 18.0, 7.0, 25.0, 6.0, 19.0, 9.0]


@pytest.fixture
def sample_roic_declining():
    """Sample ROIC values: steadily declining."""
    return [25.0, 23.0, 20.0, 18.0, 15.0, 12.0, 10.0, 8.0, 6.0, 4.0]
