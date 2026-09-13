"""Тести обліку зносу взуття."""

from app.services.gear import check_equipment_status, fleet_overview, wear_percent


def shoe(mileage: float, category: str = "daily") -> dict:
    return {"id": 1, "model": "Pegasus 40", "category": category, "mileage_km": mileage}


def test_wear_percent():
    assert wear_percent(350, 700) == 50.0


def test_fresh_shoe_is_ok():
    assert check_equipment_status(shoe(100))["status"] == "ok"


def test_worn_shoe_requires_replacement():
    assert check_equipment_status(shoe(720))["status"] == "replace"


def test_injury_history_lowers_limit():
    runner = {"level": "beginner", "weekly_volume_km": 20, "has_injury_history": 1}
    assert check_equipment_status(shoe(600), runner)["limit_km"] == 595


def test_retired_shoe_reported_separately():
    data = shoe(500)
    data["retired"] = 1
    assert check_equipment_status(data)["status"] == "retired"


def test_fleet_overview_counts_pairs():
    overview = fleet_overview([shoe(100), shoe(690)])
    assert overview["total_pairs"] == 2
    assert overview["need_replacement"] == 1
