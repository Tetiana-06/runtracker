"""Маршрути тренувань: додавання, перелік, аналітика."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Run, Runner, Shoe
from app.schemas import RunCreate, RunOut, WeeklySummary
from app.services.analytics import personal_bests, volume_trend, weekly_summaries
from app.services.pace import format_duration, format_pace, pace_seconds_per_km

router = APIRouter(prefix="/api/runs", tags=["runs"])


def serialize(run: Run) -> dict:
    return {
        "run_date": run.run_date,
        "distance_km": run.distance_km,
        "duration_sec": run.duration_sec,
        "workout_type": run.workout_type,
        "avg_hr": run.avg_hr,
    }


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> Run:
    if db.get(Runner, payload.runner_id) is None:
        raise HTTPException(status_code=404, detail="Runner not found")

    run = Run(
        runner_id=payload.runner_id,
        shoe_id=payload.shoe_id,
        run_date=payload.run_date or date.today(),
        distance_km=payload.distance_km,
        duration_sec=payload.duration_sec,
        avg_hr=payload.avg_hr,
        workout_type=payload.workout_type,
        notes=payload.notes,
    )
    db.add(run)

    if payload.shoe_id is not None:
        shoe = db.get(Shoe, payload.shoe_id)
        if shoe is None:
            raise HTTPException(status_code=404, detail="Shoe not found")
        shoe.mileage_km = round(shoe.mileage_km + payload.distance_km, 1)

    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[RunOut])
def list_runs(runner_id: int, db: Session = Depends(get_db)) -> list[Run]:
    return (
        db.query(Run)
        .filter(Run.runner_id == runner_id)
        .order_by(Run.run_date.desc(), Run.id.desc())
        .all()
    )


@router.get("/{run_id}/details")
def run_details(run_id: int, db: Session = Depends(get_db)) -> dict:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    pace = pace_seconds_per_km(run.distance_km, run.duration_sec)
    return {
        "id": run.id,
        "distance_km": run.distance_km,
        "duration": format_duration(run.duration_sec),
        "pace": f"{format_pace(pace)} /км",
        "workout_type": run.workout_type,
        "avg_hr": run.avg_hr,
        "notes": run.notes,
    }


@router.get("/summary/weekly", response_model=list[WeeklySummary])
def weekly(runner_id: int, db: Session = Depends(get_db)) -> list[dict]:
    runs = db.query(Run).filter(Run.runner_id == runner_id).all()
    if not runs:
        return []
    return weekly_summaries([serialize(run) for run in runs])


@router.get("/summary/insights")
def insights(runner_id: int, db: Session = Depends(get_db)) -> dict:
    runs = [serialize(run) for run in db.query(Run).filter(Run.runner_id == runner_id).all()]
    summaries = weekly_summaries(runs)
    return {
        "trend": volume_trend(summaries),
        "personal_bests": personal_bests(runs),
        "total_runs": len(runs),
        "total_km": round(sum(run["distance_km"] for run in runs), 1),
    }
