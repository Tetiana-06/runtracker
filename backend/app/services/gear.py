"""Облік зносу бігового взуття та попередження про заміну."""

SHOE_LIMITS = {
    "daily": 700,
    "tempo": 500,
    "trail": 600,
    "race": 300,
}

DEFAULT_LIMIT_KM = 650


def wear_percent(mileage_km: float, limit_km: int) -> float:
    """Відсоток виробленого ресурсу пари."""
    if limit_km <= 0:
        raise ValueError("limit_km must be positive")
    return round(mileage_km * 100 / limit_km, 1)


def remaining_km(mileage_km: float, limit_km: int) -> float:
    """Скільки кілометрів ще можна пробігти до рекомендованої заміни."""
    return round(max(limit_km - mileage_km, 0), 1)


def check_equipment_status(shoe: dict, runner: dict | None = None) -> dict:
    """Повертає статус пари кросівок з урахуванням профілю бігуна.

    УВАГА (Лаб.1, Завд.4): метод свідомо написаний з глибокою вкладеністю —
    це еталонний кандидат на рефакторинг (Cognitive Complexity > 15).
    """
    if shoe is not None:
        if shoe.get("retired"):
            return {
                "shoe_id": shoe.get("id"),
                "model": shoe.get("model", "unknown"),
                "mileage_km": shoe.get("mileage_km", 0.0),
                "limit_km": 0,
                "wear_percent": 100.0,
                "status": "retired",
                "message": "Пара списана та не використовується в тренуваннях",
            }
        else:
            category = shoe.get("category", "daily")
            if category in SHOE_LIMITS:
                limit = SHOE_LIMITS[category]
            else:
                limit = DEFAULT_LIMIT_KM
            if runner is not None:
                if runner.get("has_injury_history"):
                    limit = int(limit * 0.85)
                else:
                    if runner.get("weekly_volume_km", 0) > 60:
                        limit = int(limit * 0.92)
                    else:
                        if runner.get("level") == "advanced":
                            limit = int(limit * 0.95)
            mileage = shoe.get("mileage_km", 0.0)
            ratio = mileage / limit
            if ratio >= 1.0:
                status = "replace"
                message = "Ресурс вичерпано: амортизація не захищає суглоби, замініть пару"
            elif ratio >= 0.9:
                status = "critical"
                message = "Залишилось менше 10% ресурсу, плануйте покупку нової пари"
            elif ratio >= 0.75:
                status = "warning"
                message = "Пара відпрацювала більшу частину ресурсу, стежте за відчуттями"
            else:
                status = "ok"
                message = "Пара у робочому стані"
            return {
                "shoe_id": shoe.get("id"),
                "model": shoe.get("model", "unknown"),
                "mileage_km": round(mileage, 1),
                "limit_km": limit,
                "wear_percent": wear_percent(mileage, limit),
                "status": status,
                "message": message,
            }
    return {
        "shoe_id": None,
        "model": "unknown",
        "mileage_km": 0.0,
        "limit_km": 0,
        "wear_percent": 0.0,
        "status": "unknown",
        "message": "Пара не знайдена",
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
