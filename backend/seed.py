"""Наповнення бази демонстраційними даними: python seed.py"""

import random
from datetime import date, timedelta

from app.database import SessionLocal, init_db
from app.models import Run, Runner, Shoe

WORKOUT_TYPES = ["easy", "easy", "long", "tempo", "intervals"]


def create_demo_runner(db) -> Runner:
    runner = Runner(
        name="Олег Демо",
        age=28,
        resting_hr=54,
        level="intermediate",
        weekly_volume_km=45,
        has_injury_history=0,
    )
    db.add(runner)
    db.flush()
    return runner


def create_demo_shoes(db, runner: Runner) -> list[Shoe]:
    shoes = [
        Shoe(runner_id=runner.id, model="Nike Pegasus 40", category="daily", mileage_km=430),
        Shoe(runner_id=runner.id, model="Adidas Adizero SL", category="tempo", mileage_km=480),
        Shoe(runner_id=runner.id, model="Saucony Endorphin Pro", category="race", mileage_km=120),
    ]
    db.add_all(shoes)
    db.flush()
    return shoes


def create_demo_runs(db, runner: Runner, shoes: list[Shoe]) -> None:
    random.seed(42)
    today = date.today()
    for day_offset in range(0, 56, 2):
        workout_type = random.choice(WORKOUT_TYPES)
        distance = round(random.uniform(5, 18) if workout_type == "long" else random.uniform(5, 12), 1)
        pace = random.randint(270, 330)
        db.add(
            Run(
                runner_id=runner.id,
                shoe_id=random.choice(shoes).id,
                run_date=today - timedelta(days=day_offset),
                distance_km=distance,
                duration_sec=int(distance * pace),
                avg_hr=random.randint(135, 172),
                workout_type=workout_type,
                notes=None,
            )
        )


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Runner).count() > 0:
            print("База вже містить дані, пропускаю.")
            return
        runner = create_demo_runner(db)
        shoes = create_demo_shoes(db, runner)
        create_demo_runs(db, runner, shoes)
        db.commit()
        print(f"Створено демо-бігуна id={runner.id} з тренуваннями та взуттям.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
