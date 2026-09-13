"""Тести пульсових зон."""

import pytest

from app.services.heart_rate import (
    classify_hr,
    estimate_max_hr,
    karvonen_zones,
    zone_distribution,
)


def test_estimate_max_hr():
    assert estimate_max_hr(30) == 187


def test_estimate_max_hr_rejects_invalid_age():
    with pytest.raises(ValueError):
        estimate_max_hr(0)


def test_karvonen_zones_are_ordered():
    zones = karvonen_zones(30, 60)
    assert len(zones) == 5
    assert zones[0]["lower_hr"] < zones[-1]["upper_hr"]


def test_classify_hr_returns_zone_number():
    zones = karvonen_zones(30, 60)
    assert classify_hr(zones[2]["lower_hr"] + 1, zones) == 3


def test_zone_distribution_sums_to_100():
    zones = karvonen_zones(30, 60)
    runs = [
        {"avg_hr": zones[1]["lower_hr"] + 1, "duration_sec": 1800},
        {"avg_hr": zones[3]["lower_hr"] + 1, "duration_sec": 1800},
    ]
    distribution = zone_distribution(runs, zones)
    assert round(sum(distribution.values())) == 100
