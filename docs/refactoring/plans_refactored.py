"""Генератор індивідуальних планів підготовки до забігів 5 км / 10 км / 21 км.

ВЕРСІЯ «ПІСЛЯ» (Лаб.1, Завд.4).
Застосовані техніки: Guard Clauses, Extract Method, Replace Nested Conditional
with Lookup Table. Поведінка ідентична, усі тести проходять без змін.
"""

WORKOUT_LIBRARY = {
    "easy": "Легкий біг у 2-й зоні",
    "long": "Довгий біг у рівному темпі",
    "tempo": "Темповий відрізок на рівні ПАНО",
    "intervals": "Інтервали 400–1000 м",
    "recovery": "Відновлювальний крос або крос-тренінг",
    "rest": "Відпочинок",
}

SESSIONS_BY_LEVEL = {"beginner": 3, "intermediate": 4, "advanced": 5}
INJURY_SESSIONS = 3
DEFAULT_SESSIONS = 5
TAPER_FACTOR = 0.6
RECOVERY_FACTOR = 0.8
WEEKLY_PROGRESSION_KM = 0.8


def base_long_run_km(target_distance_km: float) -> float:
    """Стартова довжина довгого бігу залежно від цільової дистанції."""
    if target_distance_km <= 5:
        return 4.0
    if target_distance_km <= 10:
        return 6.0
    if target_distance_km <= 21.1:
        return 10.0
    return 14.0


def sessions_per_week(runner: dict) -> int:
    """Кількість тренувань на тиждень: травми мають пріоритет над рівнем."""
    if runner.get("has_injury_history"):
        return INJURY_SESSIONS
    return SESSIONS_BY_LEVEL.get(runner.get("level"), DEFAULT_SESSIONS)


def week_shape(week: int, weeks: int, long_run_km: float) -> tuple[str, float]:
    """Фаза тижня та довжина довгого бігу в ньому."""
    if week > weeks - 2:
        return "taper", round(long_run_km * TAPER_FACTOR, 1)

    distance = round(long_run_km + week * WEEKLY_PROGRESSION_KM, 1)
    if week % 4 == 0:
        return "recovery", round(distance * RECOVERY_FACTOR, 1)
    return "build", distance


def session_profile(session: int, level: str, phase: str) -> tuple[str, float]:
    """Тип тренування та його частка від довгого бігу тижня."""
    if session == 0:
        return "easy", 0.5
    if session == 2:
        return "long", 1.0
    if session == 1:
        if level == "beginner":
            return "easy", 0.45
        return ("tempo", 0.6) if phase == "build" else ("recovery", 0.4)
    if phase == "build" and level == "advanced":
        return "intervals", 0.55
    return "easy", 0.5


def build_workout(session: int, level: str, phase: str, long_run_km: float) -> dict:
    """Одне тренування дня."""
    workout_type, share = session_profile(session, level, phase)
    return {
        "day": session + 1,
        "type": workout_type,
        "description": WORKOUT_LIBRARY[workout_type],
        "distance_km": round(long_run_km * share, 1),
    }


def generate_training_plan(runner: dict, target_distance_km: float, weeks: int) -> list[dict]:
    """Будує потижневий план тренувань."""
    if not runner or weeks <= 0:
        return []

    sessions = sessions_per_week(runner)
    level = runner.get("level", "beginner")
    long_run = base_long_run_km(target_distance_km)

    plan = []
    for week in range(1, weeks + 1):
        phase, week_long_run = week_shape(week, weeks, long_run)
        workouts = [build_workout(i, level, phase, week_long_run) for i in range(sessions)]
        plan.append(
            {
                "week": week,
                "phase": phase,
                "total_km": round(sum(w["distance_km"] for w in workouts), 1),
                "workouts": workouts,
            }
        )
    return plan


def plan_volume(plan: list[dict]) -> float:
    """Сумарний обсяг усього плану в кілометрах."""
    return round(sum(week["total_km"] for week in plan), 1)
