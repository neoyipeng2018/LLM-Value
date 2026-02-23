"""Tests for Stage 2 ROIC analysis logic (no API keys needed)."""

import numpy as np

from pipelines.stage2_roic_filter import analyze_roic, _classify_trend


class TestAnalyzeRoic:
    def test_stable_high_roic_passes(self, sample_roic_stable):
        result = analyze_roic(sample_roic_stable)
        assert result["passed"] is True
        assert result["trend"] == "stable"
        assert result["avg"] > 10.0

    def test_upward_trend_passes(self, sample_roic_upward):
        result = analyze_roic(sample_roic_upward)
        assert result["passed"] is True
        assert result["trend"] == "upward"
        assert result["avg"] > 10.0

    def test_cyclical_fails(self, sample_roic_cyclical):
        result = analyze_roic(sample_roic_cyclical)
        assert result["passed"] is False
        assert result["trend"] == "cyclical"

    def test_declining_fails(self, sample_roic_declining):
        result = analyze_roic(sample_roic_declining)
        assert result["passed"] is False
        assert result["trend"] == "declining"

    def test_insufficient_data(self):
        result = analyze_roic([15.0])
        assert result["passed"] is False
        assert result["trend"] == "insufficient_data"

    def test_empty_data(self):
        result = analyze_roic([])
        assert result["passed"] is False
        assert result["trend"] == "insufficient_data"

    def test_low_avg_roic_fails(self):
        # Stable but below 10% threshold
        result = analyze_roic([5.0, 5.5, 5.2, 5.1, 5.3, 5.4, 5.0, 5.2, 5.3, 5.1])
        assert result["passed"] is False
        assert result["avg"] < 10.0

    def test_stats_computed(self, sample_roic_stable):
        result = analyze_roic(sample_roic_stable)
        assert result["avg"] is not None
        assert result["min"] is not None
        assert result["max"] is not None
        assert result["std"] is not None
        assert result["min"] <= result["avg"] <= result["max"]


class TestClassifyTrend:
    def test_upward(self):
        values = np.array([10, 12, 14, 16, 18, 20, 22, 24, 26, 28], dtype=float)
        trend, detail = _classify_trend(values)
        assert trend == "upward"

    def test_stable(self):
        values = np.array([15, 15.1, 14.9, 15.2, 14.8, 15.0, 15.1, 14.9, 15.2, 15.0], dtype=float)
        trend, detail = _classify_trend(values)
        assert trend == "stable"

    def test_declining(self):
        values = np.array([30, 28, 25, 22, 19, 16, 13, 10, 7, 4], dtype=float)
        trend, detail = _classify_trend(values)
        assert trend == "declining"

    def test_cyclical_high_volatility(self):
        values = np.array([20, 5, 22, 4, 21, 6, 23, 3, 20, 7], dtype=float)
        trend, detail = _classify_trend(values)
        assert trend == "cyclical"
