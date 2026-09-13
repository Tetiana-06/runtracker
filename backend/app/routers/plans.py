"""Маршрути генерації планів підготовки до забігу."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Runner, TrainingPlan
from app.schemas import PlanOut, PlanRequest
from app.services.pace import RACE_DISTANCES, predict_race_time, split_table
from app.services.plans import generate_training_plan, plan_volume

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanRequest, db: Session = Depends(get_db)) -> dict:
    runner = db.get(Runner, payload.runner_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Runner not found")

    profile = {
        "level": runner.level,
        "weekly_volume_km": runner.weekly_volume_km,
        "has_injury_history": runner.has_injury_history,
    }
    plan = generate_training_plan(profile, payload.target_distance_km, payload.weeks)

    record = TrainingPlan(
        runner_id=runner.id,
        target_distance_km=payload.target_distance_km,
        weeks=payload.weeks,
        payload=json.dumps(plan, ensure_ascii=False),
    )
    db.add(record)
    db.commit()

    return {
        "runner_id": runner.id,
        "target_distance_km": payload.target_distance_km,
        "weeks": payload.weeks,
        "plan": plan,
    }


@router.get("/{runner_id}/latest", response_model=PlanOut)
def latest_plan(runner_id: int, db: Session = Depends(get_db)) -> dict:
    record = (
        db.query(TrainingPlan)
        .filter(TrainingPlan.runner_id == runner_id)
        .order_by(TrainingPlan.id.desc())
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {
        "runner_id": record.runner_id,
        "target_distance_km": record.target_distance_km,
        "weeks": record.weeks,
        "plan": json.loads(record.payload),
    }


@router.get("/{runner_id}/volume")
def total_volume(runner_id: int, db: Session = Depends(get_db)) -> dict:
    plan = latest_plan(runner_id, db)
    return {"runner_id": runner_id, "total_km": plan_volume(plan["plan"])}


@router.get("/race/forecast")
def race_forecast(
    known_distance_km: float,
    known_time_sec: int,
    race: str = "10k",
) -> dict:
    if race not in RACE_DISTANCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown race: {race}",
        )
    target = RACE_DISTANCES[race]
    predicted = predict_race_time(known_distance_km, known_time_sec, target)
    return {
        "race": race,
        "distance_km": target,
        "predicted_time_sec": predicted,
        "splits": split_table(target, predicted),
    }
