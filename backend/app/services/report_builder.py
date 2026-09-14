"""ВИПРАВЛЕННЯ дублювання (Лаб.1, Завд.3, крок «повернення до PASS»).

Важливо: за умовами роботи дубльований код треба ВИНЕСТИ в окремий
багаторазовий модуль, а не просто видалити.

Як використати:
  1) створіть backend/app/services/report_builder.py з кодом нижче;
  2) у report_export_csv.py та report_export_json.py залиште по 3–4 рядки:

        from app.services.report_builder import build_report_summary

        def build_csv_report(runs: list[dict]) -> dict:
            return build_report_summary(runs)

  3) видаліть файл notifications.py з порушенням №1 (або приберіть з нього
     хардкод, ділення на нуль, MD5 і verify=False);
  4) закомітьте і запустіть повторне сканування — статус повернеться в PASS.
"""

TYPE_WEIGHTS = {"easy": 1.0, "long": 1.3, "tempo": 1.6, "intervals": 1.9, "race": 2.2}
HARD_TYPES = ("tempo", "intervals", "race")


def build_report_summary(runs: list[dict]) -> dict:
    """Єдина реалізація зведення, спільна для всіх форматів експорту."""
    total_distance = sum(run.get("distance_km", 0.0) for run in runs)
    total_time = sum(run.get("duration_sec", 0) for run in runs)
    total_load = sum(
        run.get("distance_km", 0.0) * TYPE_WEIGHTS.get(run.get("workout_type", "easy"), 1.0)
        for run in runs
    )
    hard_sessions = sum(1 for run in runs if run.get("workout_type") in HARD_TYPES)

    return {
        "total_distance_km": round(total_distance, 1),
        "total_time_sec": total_time,
        "total_load": round(total_load, 1),
        "average_pace_sec_per_km": round(total_time / total_distance, 1) if total_distance else 0.0,
        "hard_sessions": hard_sessions,
        "easy_sessions": len(runs) - hard_sessions,
        "sessions": len(runs),
    }
