import pytest
from datetime import date, datetime

from calculations import (
    calculate_points_from_packages,
    format_currency,
    format_points,
    get_milestone_progress,
    get_rewards_status,
    get_year_month,
)


class TestCalculatePointsFromPackages:
    def test_positive(self):
        assert calculate_points_from_packages(5) == 5

    def test_one(self):
        assert calculate_points_from_packages(1) == 1

    def test_large(self):
        assert calculate_points_from_packages(500) == 500

    def test_zero(self):
        assert calculate_points_from_packages(0) == 0

    def test_negative(self):
        assert calculate_points_from_packages(-3) == 0

    def test_negative_large(self):
        assert calculate_points_from_packages(-999) == 0


class TestFormatCurrency:
    def test_zero(self):
        assert format_currency(0) == "R$ 0,00"

    def test_simple(self):
        assert format_currency(38.0) == "R$ 38,00"

    def test_cents(self):
        assert format_currency(0.50) == "R$ 0,50"

    def test_thousands(self):
        assert format_currency(1234.56) == "R$ 1.234,56"

    def test_large(self):
        assert format_currency(10000.00) == "R$ 10.000,00"

    def test_negative(self):
        result = format_currency(-50.0)
        assert "-" in result


class TestFormatPoints:
    def test_zero(self):
        assert format_points(0) == "0 pts"

    def test_one(self):
        assert format_points(1) == "1 pt"

    def test_two(self):
        assert format_points(2) == "2 pts"

    def test_many(self):
        assert format_points(500) == "500 pts"


class TestGetYearMonth:
    def test_none_returns_today(self):
        today = date.today()
        year, month = get_year_month(None)
        assert year == today.year
        assert month == today.month

    def test_date_object(self):
        assert get_year_month(date(2025, 3, 15)) == (2025, 3)

    def test_datetime_object(self):
        assert get_year_month(datetime(2024, 12, 1, 10, 30)) == (2024, 12)

    def test_iso_string_date(self):
        assert get_year_month("2026-06-22") == (2026, 6)

    def test_iso_string_with_time(self):
        assert get_year_month("2026-01-15T08:00:00") == (2026, 1)

    def test_january(self):
        assert get_year_month(date(2026, 1, 1)) == (2026, 1)

    def test_december(self):
        assert get_year_month(date(2025, 12, 31)) == (2025, 12)


class TestGetMilestoneProgress:
    def test_zero_packages(self):
        result = get_milestone_progress(0)
        assert result["percent"] == 0.0
        assert result["remaining"] == 500
        assert result["reached"] is False
        assert result["total_bought"] == 0

    def test_halfway(self):
        result = get_milestone_progress(250)
        assert result["percent"] == 50.0
        assert result["remaining"] == 250
        assert result["reached"] is False

    def test_one_before_threshold(self):
        result = get_milestone_progress(499)
        assert result["reached"] is False
        assert result["remaining"] == 1

    def test_exact_threshold(self):
        result = get_milestone_progress(500)
        assert result["reached"] is True
        assert result["remaining"] == 0
        assert result["percent"] == 100.0

    def test_exceeds_threshold_caps_at_100(self):
        result = get_milestone_progress(600)
        assert result["reached"] is True
        assert result["percent"] == 100.0
        assert result["remaining"] == 0

    def test_custom_threshold(self):
        result = get_milestone_progress(100, threshold=200)
        assert result["percent"] == 50.0
        assert result["threshold"] == 200
        assert result["reached"] is False

    def test_custom_threshold_reached(self):
        result = get_milestone_progress(200, threshold=200)
        assert result["reached"] is True

    def test_zero_threshold_guard_falls_back_to_500(self):
        result = get_milestone_progress(100, threshold=0)
        assert result["threshold"] == 500
        assert result["percent"] == 20.0

    def test_negative_threshold_guard(self):
        result = get_milestone_progress(100, threshold=-10)
        assert result["threshold"] == 500

    def test_progress_text_shows_faltam_when_not_reached(self):
        result = get_milestone_progress(100)
        assert "Faltam" in result["progress_text"]

    def test_progress_text_shows_meta_atingida_when_reached(self):
        result = get_milestone_progress(500)
        assert "META ATINGIDA" in result["progress_text"]

    def test_progress_text_contains_counts(self):
        result = get_milestone_progress(250)
        assert "250" in result["progress_text"]
        assert "500" in result["progress_text"]


class TestGetRewardsStatus:
    def test_returns_required_keys(self):
        result = get_rewards_status(100, 100)
        assert "milestone_500" in result
        assert "summary_text" in result

    def test_not_reached(self):
        result = get_rewards_status(50, 50)
        assert result["milestone_500"]["reached"] is False

    def test_reached_at_500(self):
        result = get_rewards_status(500, 500)
        assert result["milestone_500"]["reached"] is True

    def test_custom_threshold_via_rules(self):
        result = get_rewards_status(0, 300, rules={"milestone_packages_threshold": 300})
        assert result["milestone_500"]["reached"] is True

    def test_default_rules_when_none(self):
        result = get_rewards_status(0, 0, rules=None)
        assert result["milestone_500"]["threshold"] == 500

    def test_summary_text_is_string(self):
        result = get_rewards_status(100, 100)
        assert isinstance(result["summary_text"], str)
        assert len(result["summary_text"]) > 0
