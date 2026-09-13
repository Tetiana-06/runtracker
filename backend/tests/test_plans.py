"""Тести генератора планів підготовки."""

from app.services.plans import base_long_run_km, generate_training_plan, plan_volume

BEGINNER = {"level": "beginner", "weekly_volume_km": 20, "has_injury_history": 0}
ADVANCED = {"level": "advanced", "weekly_volume_km": 70, "has_injury_history": 0}


def test_base_long_run_for_5k():
    assert base_long_run_km(5) == 4.0


def test_plan_has_requested_number_of_weeks():
    plan = generate_training_plan(BEGINNER, 10, 8)
    assert len(plan) == 8


def test_beginner_gets_three_sessions():
    plan = generate_training_plan(BEGINNER, 10, 6)
    assert len(plan[0]["workouts"]) == 3


def test_advanced_gets_five_sessions():
    plan = generate_training_plan(ADVANCED, 21.0975, 10)
    assert len(plan[0]["workouts"]) == 5


def test_last_weeks_are_taper():
    plan = generate_training_plan(ADVANCED, 21.0975, 10)
    assert plan[-1]["phase"] == "taper"


def test_zero_weeks_returns_empty_plan():
    assert generate_training_plan(BEGINNER, 10, 0) == []


def test_plan_volume_is_positive():
    plan = generate_training_plan(BEGINNER, 10, 8)
    assert plan_volume(plan) > 0
