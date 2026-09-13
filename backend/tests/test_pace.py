"""Тести розрахунків темпу та прогнозу результату."""

import pytest

from app.services.pace import (
    format_duration,
    format_pace,
    pace_seconds_per_km,
    predict_race_time,
    speed_kmh,
    split_table,
    training_paces,
)


def test_pace_seconds_per_km():
    assert pace_seconds_per_km(10, 3000) == 300


def test_pace_rejects_zero_distance():
    with pytest.raises(ValueError):
        pace_seconds_per_km(0, 1200)


def test_format_pace():
    assert format_pace(324) == "5:24"


def test_format_duration_with_hours():
    assert format_duration(5025) == "1:23:45"


def test_format_duration_without_hours():
    assert format_duration(1425) == "23:45"


def test_speed_kmh():
    assert round(speed_kmh(10, 3600), 1) == 10.0


def test_predict_race_time_is_slower_on_longer_distance():
    half = predict_race_time(10, 3000, 21.0975)
    assert half > 3000 * 2


def test_split_table_length():
    splits = split_table(5, 1500)
    assert len(splits) == 5
    assert splits[0]["km"] == 1


def test_training_paces_keys():
    paces = training_paces(270)
    assert set(paces) == {"recovery", "easy", "marathon", "threshold", "interval"}
