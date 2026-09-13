"""Агрегована аналітика тренувань: тижневі зведення та тренувальне навантаження."""

from datetime import date, timedelta

from app.services.pace import pace_seconds_per_km

TYPE_WEIGHTS = {
    "easy": 1.0,
    "long": 1.3,
    "tempo": 1.6,
    "intervals": 1.9,
    "race": 2.2,
}


def week_start(day: date) -> date:
    """Понеділок того тижня, до якого належить дата."""
    return day - timedelta(days=day.weekday())


def session_load(distance_km: float, workout_type: str) -> float:
    """Умовне навантаження однієї сесії: кілометри з коефіцієнтом інтенсивності."""
    weight = TYPE_WEIGHTS.get(workout_type, 1.0)
    return round(distance_km * weight, 2)


def weekly_summaries(runs: list[dict], limit: int = 8) -> list[dict]:
    """Групує тренування по тижнях і рахує ключові показники."""
    buckets: dict[date, list[dict]] = {}
    for run in runs:
        key = week_start(run["run_date"])
        buckets.setdefault(key, []).append(run)

    summaries = []
    for start in sorted(buckets, reverse=True)[:limit]:
        week_runs = buckets[start]
        total_km = sum(item["distance_km"] for item in week_runs)
        total_time = sum(item["duration_sec"] for item in week_runs)
        load = sum(session_load(i["distance_km"], i["workout_type"]) for i in week_runs)
        summaries.append(
            {
                "week_start": start,
                "total_km": round(total_km, 1),
                "total_time_sec": total_time,
                "avg_pace_sec_per_km": round(pace_seconds_per_km(total_km, total_time), 1),
                "runs_count": len(week_runs),
                "load": round(load, 1),
            }
        )
    return list(reversed(summaries))


def volume_trend(summaries: list[dict]) -> str:
    """Порівнює обсяг останнього тижня з попереднім."""
    if len(summaries) < 2:
        return "not_enough_data"
    current = summaries[-1]["total_km"]
    previous = summaries[-2]["total_km"]
    if previous == 0:
        return "restart"
    change = (current - previous) / previous
    if change > 0.15:
        return "sharp_increase"
    if change > 0.02:
        return "growth"
    if change < -0.15:
        return "sharp_drop"
    return "stable"


def personal_bests(runs: list[dict]) -> dict[str, dict]:
    """Найшвидший темп на типових дистанціях серед усіх тренувань."""
    targets = {"5k": 5.0, "10k": 10.0, "half": 21.0}
    bests: dict[str, dict] = {}
    for label, distance in targets.items():
        candidates = [r for r in runs if r["distance_km"] >= distance * 0.97]
        if not candidates:
            continue
        best = min(candidates, key=lambda r: r["duration_sec"] / r["distance_km"])
        bests[label] = {
            "run_date": best["run_date"],
            "distance_km": best["distance_km"],
            "duration_sec": best["duration_sec"],
        }
    return bests
