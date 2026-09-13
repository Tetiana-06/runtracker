"""Пульсові зони: оцінка максимального пульсу та розрахунок зон за Карвоненом."""

ZONE_DEFINITIONS = [
    (1, "Відновлення", 0.50, 0.60, "Легкий біг для відновлення між тренуваннями"),
    (2, "Аеробна база", 0.60, 0.70, "Основний обсяг, розвиток витривалості"),
    (3, "Темпова", 0.70, 0.80, "Марафонський темп, робота на економічність"),
    (4, "Порогова", 0.80, 0.90, "ПАНО, підвищення лактатного порогу"),
    (5, "МСК", 0.90, 1.00, "Інтервали, максимальне споживання кисню"),
]


def estimate_max_hr(age: int) -> int:
    """Оцінка максимального пульсу за формулою Танаки: 208 - 0.7 * вік."""
    if age <= 0:
        raise ValueError("age must be positive")
    return int(round(208 - 0.7 * age))


def karvonen_zones(age: int, resting_hr: int) -> list[dict]:
    """Пульсові зони за резервом серця (метод Карвонена)."""
    max_hr = estimate_max_hr(age)
    reserve = max_hr - resting_hr
    if reserve <= 0:
        raise ValueError("resting_hr is too high for this age")

    zones = []
    for number, name, low, high, purpose in ZONE_DEFINITIONS:
        zones.append(
            {
                "zone": number,
                "name": name,
                "lower_hr": int(round(resting_hr + reserve * low)),
                "upper_hr": int(round(resting_hr + reserve * high)),
                "purpose": purpose,
            }
        )
    return zones


def classify_hr(avg_hr: int, zones: list[dict]) -> int:
    """Визначає номер зони для середнього пульсу тренування."""
    for zone in zones:
        if zone["lower_hr"] <= avg_hr <= zone["upper_hr"]:
            return zone["zone"]
    if avg_hr < zones[0]["lower_hr"]:
        return 1
    return len(zones)


def zone_distribution(runs: list[dict], zones: list[dict]) -> dict[int, float]:
    """Розподіл часу тренувань за зонами у відсотках."""
    totals = {zone["zone"]: 0 for zone in zones}
    tracked_time = 0
    for run in runs:
        if not run.get("avg_hr"):
            continue
        zone_number = classify_hr(run["avg_hr"], zones)
        totals[zone_number] += run["duration_sec"]
        tracked_time += run["duration_sec"]

    if tracked_time == 0:
        return {zone: 0.0 for zone in totals}
    return {zone: round(value * 100 / tracked_time, 1) for zone, value in totals.items()}
