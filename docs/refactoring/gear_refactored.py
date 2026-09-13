"""Облік зносу бігового взуття та попередження про заміну.

ВЕРСІЯ «ПІСЛЯ» (Лаб.1, Завд.4).
Застосовані техніки: Guard Clauses, Extract Method, винесення порогів у
конфігураційну таблицю. Поведінка ідентична, усі тести проходять без змін.
"""

SHOE_LIMITS = {
    "daily": 700,
    "tempo": 500,
    "trail": 600,
    "race": 300,
}

DEFAULT_LIMIT_KM = 650

WEAR_THRESHOLDS = (
    (1.0, "replace", "Ресурс вичерпано: амортизація не захищає суглоби, замініть пару"),
    (0.9, "critical", "Залишилось менше 10% ресурсу, плануйте покупку нової пари"),
    (0.75, "warning", "Пара відпрацювала більшу частину ресурсу, стежте за відчуттями"),
)

HIGH_VOLUME_KM = 60
INJURY_FACTOR = 0.85
HIGH_VOLUME_FACTOR = 0.92
ADVANCED_FACTOR = 0.95


def wear_percent(mileage_km: float, limit_km: int) -> float:
    """Відсоток виробленого ресурсу пари."""
    if limit_km <= 0:
        raise ValueError("limit_km must be positive")
    return round(mileage_km * 100 / limit_km, 1)


def remaining_km(mileage_km: float, limit_km: int) -> float:
    """Скільки кілометрів ще можна пробігти до рекомендованої заміни."""
    return round(max(limit_km - mileage_km, 0), 1)


def mileage_limit(shoe: dict, runner: dict | None) -> int:
    """Ліміт пробігу пари з поправкою на профіль бігуна."""
    limit = SHOE_LIMITS.get(shoe.get("category", "daily"), DEFAULT_LIMIT_KM)
    if runner is None:
        return limit
    if runner.get("has_injury_history"):
        return int(limit * INJURY_FACTOR)
    if runner.get("weekly_volume_km", 0) > HIGH_VOLUME_KM:
        return int(limit * HIGH_VOLUME_FACTOR)
    if runner.get("level") == "advanced":
        return int(limit * ADVANCED_FACTOR)
    return limit


def wear_status(ratio: float) -> tuple[str, str]:
    """Статус і рекомендація за часткою виробленого ресурсу."""
    for threshold, status, message in WEAR_THRESHOLDS:
        if ratio >= threshold:
            return status, message
    return "ok", "Пара у робочому стані"


def unknown_shoe_status() -> dict:
    return {
        "shoe_id": None,
        "model": "unknown",
        "mileage_km": 0.0,
        "limit_km": 0,
        "wear_percent": 0.0,
        "status": "unknown",
        "message": "Пара не знайдена",
    }


def retired_shoe_status(shoe: dict) -> dict:
    return {
        "shoe_id": shoe.get("id"),
        "model": shoe.get("model", "unknown"),
        "mileage_km": shoe.get("mileage_km", 0.0),
        "limit_km": 0,
        "wear_percent": 100.0,
        "status": "retired",
        "message": "Пара списана та не використовується в тренуваннях",
    }


def check_equipment_status(shoe: dict, runner: dict | None = None) -> dict:
    """Повертає статус пари кросівок з урахуванням профілю бігуна."""
    if shoe is None:
        return unknown_shoe_status()
    if shoe.get("retired"):
        return retired_shoe_status(shoe)

    limit = mileage_limit(shoe, runner)
    mileage = shoe.get("mileage_km", 0.0)
    status, message = wear_status(mileage / limit)

    return {
        "shoe_id": shoe.get("id"),
        "model": shoe.get("model", "unknown"),
        "mileage_km": round(mileage, 1),
        "limit_km": limit,
        "wear_percent": wear_percent(mileage, limit),
        "status": status,
        "message": message,
    }


def fleet_overview(shoes: list[dict], runner: dict | None = None) -> dict:
    """Зведення по всьому взуттю бігуна."""
    statuses = [check_equipment_status(shoe, runner) for shoe in shoes]
    need_replacement = [item for item in statuses if item["status"] in ("replace", "critical")]
    total_mileage = sum(item["mileage_km"] for item in statuses)
    return {
        "total_pairs": len(statuses),
        "total_mileage_km": round(total_mileage, 1),
        "need_replacement": len(need_replacement),
        "items": statuses,
    }
