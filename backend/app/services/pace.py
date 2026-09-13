"""Розрахунки темпу, спліт-таблиць та прогнозу результату на дистанції."""
# Примітка: показник RIEGEL_EXPONENT підібраний для дистанцій 5–42 км
RIEGEL_EXPONENT = 1.06

RACE_DISTANCES = {
    "5k": 5.0,
    "10k": 10.0,
    "half": 21.0975,
    "marathon": 42.195,
}


def pace_seconds_per_km(distance_km: float, duration_sec: int) -> float:
    """Середній темп у секундах на кілометр."""
    if distance_km <= 0:
        raise ValueError("distance_km must be positive")
    return duration_sec / distance_km


def format_pace(seconds_per_km: float) -> str:
    """Форматує темп у вигляді 5:24 /км."""
    total = int(round(seconds_per_km))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


def format_duration(duration_sec: int) -> str:
    """Форматує тривалість у вигляді 1:23:45 або 23:45."""
    hours, remainder = divmod(int(duration_sec), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def speed_kmh(distance_km: float, duration_sec: int) -> float:
    """Середня швидкість у км/год."""
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    return distance_km / (duration_sec / 3600)


def predict_race_time(
    known_distance_km: float, known_time_sec: int, target_distance_km: float
) -> int:
    """Прогноз часу на цільовій дистанції за формулою Рігеля."""
    if known_distance_km <= 0 or known_time_sec <= 0:
        raise ValueError("known result must be positive")
    ratio = target_distance_km / known_distance_km
    return int(round(known_time_sec * ratio**RIEGEL_EXPONENT))


def split_table(target_distance_km: float, target_time_sec: int) -> list[dict]:
    """Рівномірна розкладка по кілометрах для цільового часу."""
    pace = pace_seconds_per_km(target_distance_km, target_time_sec)
    splits = []
    full_km = int(target_distance_km)
    for km in range(1, full_km + 1):
        splits.append(
            {
                "km": km,
                "split": format_pace(pace),
                "elapsed": format_duration(int(pace * km)),
            }
        )
    return splits


def training_paces(threshold_pace_sec: float) -> dict[str, str]:
    """Похідні тренувальні темпи від порогового (за логікою Деніелса, спрощено)."""
    return {
        "recovery": format_pace(threshold_pace_sec * 1.25),
        "easy": format_pace(threshold_pace_sec * 1.15),
        "marathon": format_pace(threshold_pace_sec * 1.06),
        "threshold": format_pace(threshold_pace_sec),
        "interval": format_pace(threshold_pace_sec * 0.93),
    }
