"""Генератор індивідуальних планів підготовки до забігів 5 км / 10 км / 21 км."""

WORKOUT_LIBRARY = {
    "easy": "Легкий біг у 2-й зоні",
    "long": "Довгий біг у рівному темпі",
    "tempo": "Темповий відрізок на рівні ПАНО",
    "intervals": "Інтервали 400–1000 м",
    "recovery": "Відновлювальний крос або крос-тренінг",
    "rest": "Відпочинок",
}

TAPER_FACTOR = 0.6


def base_long_run_km(target_distance_km: float) -> float:
    """Стартова довжина довгого бігу залежно від цільової дистанції."""
    if target_distance_km <= 5:
        return 4.0
    if target_distance_km <= 10:
        return 6.0
    if target_distance_km <= 21.1:
        return 10.0
    return 14.0


def generate_training_plan(
    runner: dict, target_distance_km: float, weeks: int
) -> list[dict]:
    """Будує потижневий план тренувань.

    УВАГА (Лаб.1, Завд.4): метод свідомо написаний «драбинкою» if-else —
    це основний кандидат на рефакторинг (Cognitive Complexity ≈ 20).
    """
    plan = []
    if runner is not None:
        if weeks > 0:
            if runner.get("has_injury_history"):
                sessions_per_week = 3
            else:
                if runner.get("level") == "beginner":
                    sessions_per_week = 3
                else:
                    if runner.get("level") == "intermediate":
                        sessions_per_week = 4
                    else:
                        sessions_per_week = 5
            long_run = base_long_run_km(target_distance_km)
            for week in range(1, weeks + 1):
                workouts = []
                if week > weeks - 2:
                    week_long_run = round(long_run * TAPER_FACTOR, 1)
                    phase = "taper"
                else:
                    week_long_run = round(long_run + week * 0.8, 1)
                    phase = "build"
                    if week % 4 == 0:
                        week_long_run = round(week_long_run * 0.8, 1)
                        phase = "recovery"
                for session in range(sessions_per_week):
                    if session == 0:
                        workout_type = "easy"
                        share = 0.5
                    elif session == 1:
                        if runner.get("level") == "beginner":
                            workout_type = "easy"
                            share = 0.45
                        elif phase == "build":
                            workout_type = "tempo"
                            share = 0.6
                        else:
                            workout_type = "recovery"
                            share = 0.4
                    elif session == 2:
                        workout_type = "long"
                        share = 1.0
                    elif phase == "build" and runner.get("level") == "advanced":
                        workout_type = "intervals"
                        share = 0.55
                    else:
                        workout_type = "easy"
                        share = 0.5
                    workouts.append(
                        {
                            "day": session + 1,
                            "type": workout_type,
                            "description": WORKOUT_LIBRARY[workout_type],
                            "distance_km": round(week_long_run * share, 1),
                        }
                    )
                plan.append(
                    {
                        "week": week,
                        "phase": phase,
                        "total_km": round(sum(w["distance_km"] for w in workouts), 1),
                        "workouts": workouts,
                    }
                )
        else:
            return []
    return plan


def plan_volume(plan: list[dict]) -> float:
    """Сумарний обсяг усього плану в кілометрах."""
    return round(sum(week["total_km"] for week in plan), 1)
