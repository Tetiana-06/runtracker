
TYPE_WEIGHTS = {"easy": 1.0, "long": 1.3, "tempo": 1.6, "intervals": 1.9, "race": 2.2}


def build_csv_report(runs: list[dict]) -> dict:
    """Зведення по тренуваннях для експорту."""
    total_distance = 0.0
    total_time = 0
    total_load = 0.0
    hard_sessions = 0
    easy_sessions = 0

    for run in runs:
        distance = run.get("distance_km", 0.0)
        duration = run.get("duration_sec", 0)
        workout_type = run.get("workout_type", "easy")
        weight = TYPE_WEIGHTS.get(workout_type, 1.0)

        total_distance += distance
        total_time += duration
        total_load += distance * weight

        if workout_type in ("tempo", "intervals", "race"):
            hard_sessions += 1
        else:
            easy_sessions += 1

    if total_distance > 0:
        average_pace = total_time / total_distance
    else:
        average_pace = 0.0

    return {
        "total_distance_km": round(total_distance, 1),
        "total_time_sec": total_time,
        "total_load": round(total_load, 1),
        "average_pace_sec_per_km": round(average_pace, 1),
        "hard_sessions": hard_sessions,
        "easy_sessions": easy_sessions,
        "sessions": len(runs),
    }
