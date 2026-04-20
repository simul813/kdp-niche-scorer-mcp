"""Unit tests for scoring + revenue logic.

Tool-level tests that hit the RapidAPI client live in test_tools_live.py
(manual, opt-in) so the offline suite stays green without a key.
"""

from __future__ import annotations

from kdp_niche_scorer_mcp.scoring import (
    band_for,
    daily_copies,
    estimate_revenue,
    royalty_per_copy_kindle,
    royalty_per_copy_paperback,
    score_books,
)
from kdp_niche_scorer_mcp.tools import estimate_sales_from_bsr


class TestScoreBooks:
    def test_empty_returns_no_data(self):
        result = score_books([])
        assert result["score"] == 0
        assert result["band"] == "No data"

    def test_strong_niche_scores_well(self, strong_niche_books):
        result = score_books(strong_niche_books, "pick one")
        assert result["score"] >= 55, f"Expected Good+, got {result['score']}"
        assert result["band"] in {"Good", "Great", "Excellent"}
        assert result["breakdown"]["demand_source"] == "bsr"
        # Title-match tracking should be non-zero when keyword matches top titles
        assert result["breakdown"]["title_matches"] >= 3

    def test_saturated_niche_penalized(self, saturated_niche_books):
        result = score_books(saturated_niche_books, "saturated")
        # Huge review counts → competition ~0, price too high → pricing penalty
        assert result["breakdown"]["competition"] == 0
        assert result["breakdown"]["pricing"] <= 4
        assert result["score"] < 55

    def test_top3_dominance_triggers_penalty(self, dominated_niche_books):
        result = score_books(dominated_niche_books, "giant")
        # Top 3 avg BSR ~833, rest ~264K — ratio well over 4x → full 25pt penalty
        assert result["breakdown"]["penalty"] == 25

    def test_no_bsr_falls_back_to_reviews(self, no_bsr_books):
        result = score_books(no_bsr_books, "book")
        assert result["breakdown"]["demand_source"] == "reviews"
        # 10/10 have 20+ reviews, 2/10 have 100+ → demand = round(35 * (1.0*0.5 + 0.2*0.5)) = 21
        assert 18 <= result["breakdown"]["demand"] <= 23

    def test_score_clamped_0_100(self, strong_niche_books):
        result = score_books(strong_niche_books, "pick one")
        assert 0 <= result["score"] <= 100


class TestBandFor:
    def test_band_thresholds(self):
        assert band_for(90) == "Excellent"
        assert band_for(75) == "Great"
        assert band_for(60) == "Good"
        assert band_for(45) == "Okay"
        assert band_for(30) == "Weak"
        assert band_for(10) == "Poor"

    def test_band_boundaries(self):
        assert band_for(85) == "Excellent"
        assert band_for(84) == "Great"
        assert band_for(70) == "Great"
        assert band_for(69) == "Good"


class TestDailyCopies:
    def test_zero_or_none_bsr(self):
        assert daily_copies(0) == 0
        assert daily_copies(None) == 0
        assert daily_copies(-100) == 0

    def test_lookup_table_buckets(self):
        assert daily_copies(50) == 900
        assert daily_copies(300) == 300
        assert daily_copies(700) == 120
        assert daily_copies(3_000) == 35
        assert daily_copies(7_000) == 15
        assert daily_copies(20_000) == 6
        assert daily_copies(45_000) == 3
        assert daily_copies(80_000) == 1.5
        assert daily_copies(200_000) == 0.7
        assert daily_copies(2_000_000) == 0.03


class TestRoyalty:
    def test_kindle_70_in_window(self):
        assert royalty_per_copy_kindle(2.99) == 2.99 * 0.70
        assert royalty_per_copy_kindle(6.99) == 6.99 * 0.70
        assert royalty_per_copy_kindle(9.99) == 9.99 * 0.70

    def test_kindle_35_outside_window(self):
        assert royalty_per_copy_kindle(1.99) == 1.99 * 0.35
        assert royalty_per_copy_kindle(14.99) == 14.99 * 0.35

    def test_kindle_zero_price(self):
        assert royalty_per_copy_kindle(0) == 0
        assert royalty_per_copy_kindle(None) == 0

    def test_paperback_formula(self):
        # price * 0.6 - 2.80, floored at 0.40
        assert royalty_per_copy_paperback(9.99) == 9.99 * 0.6 - 2.80
        assert royalty_per_copy_paperback(14.99) == 14.99 * 0.6 - 2.80

    def test_paperback_floor(self):
        # 3.99 * 0.6 - 2.80 = -0.406 → floored at 0.40
        assert royalty_per_copy_paperback(3.99) == 0.40

    def test_paperback_default_for_none(self):
        assert royalty_per_copy_paperback(None) == 2.0
        assert royalty_per_copy_paperback(0) == 2.0


class TestEstimateRevenue:
    def test_kindle_default_mode(self):
        result = estimate_revenue(45_000, 6.99)
        assert result["mode"] == "kindle"
        assert result["daily_copies"] == 3
        assert result["monthly_copies"] == 90
        # royalty = 6.99 * 0.70 = 4.893 → rounded to 4.89
        assert result["royalty_per_copy"] == 4.89
        # revenue = 90 * 4.893 = 440.37 → round to 440
        assert result["monthly_revenue"] == 440

    def test_paperback_mode(self):
        result = estimate_revenue(45_000, 6.99, mode="paperback")
        assert result["mode"] == "paperback"
        # royalty = 6.99 * 0.6 - 2.80 = 1.394 → 1.39
        assert result["royalty_per_copy"] == 1.39

    def test_zero_bsr(self):
        result = estimate_revenue(0, 6.99)
        assert result["monthly_copies"] == 0
        assert result["monthly_revenue"] == 0


class TestEstimateSalesFromBsrTool:
    def test_rejects_non_positive_bsr(self):
        result = estimate_sales_from_bsr(0)
        assert "error" in result

    def test_returns_full_estimate(self):
        result = estimate_sales_from_bsr(45_000, price=6.99)
        assert result["bsr"] == 45_000
        assert result["mode"] == "kindle"
        assert result["confidence"] == "medium"
        assert "notes" in result

    def test_confidence_bands(self):
        assert estimate_sales_from_bsr(5_000)["confidence"] == "high"
        assert estimate_sales_from_bsr(50_000)["confidence"] == "medium"
        assert estimate_sales_from_bsr(600_000)["confidence"] == "low"
        assert estimate_sales_from_bsr(50)["confidence"] == "low"  # extreme low
