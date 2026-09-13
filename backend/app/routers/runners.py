"""Маршрути профілю бігуна та пульсових зон."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Runner
from app.schemas import RunnerCreate, RunnerOut, ZoneOut
from app.services.heart_rate import karvonen_zones

router = APIRouter(prefix="/api/runners", tags=["runners"])


def get_runner_or_404(db: Session, runner_id: int) -> Runner:
    runner = db.get(Runner, runner_id)
    if runner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runner not found")
    return runner


@router.post("", response_model=RunnerOut, status_code=status.HTTP_201_CREATED)
def create_runner(payload: RunnerCreate, db: Session = Depends(get_db)) -> Runner:
    runner = Runner(
        name=payload.name,
        age=payload.age,
        resting_hr=payload.resting_hr,
        level=payload.level,
        weekly_volume_km=payload.weekly_volume_km,
        has_injury_history=int(payload.has_injury_history),
    )
    db.add(runner)
    db.commit()
    db.refresh(runner)
    return runner


@router.get("", response_model=list[RunnerOut])
def list_runners(db: Session = Depends(get_db)) -> list[Runner]:
    return db.query(Runner).order_by(Runner.id).all()


@router.get("/{runner_id}", response_model=RunnerOut)
def get_runner(runner_id: int, db: Session = Depends(get_db)) -> Runner:
    return get_runner_or_404(db, runner_id)


@router.get("/{runner_id}/zones", response_model=list[ZoneOut])
def get_zones(runner_id: int, db: Session = Depends(get_db)) -> list[dict]:
    runner = get_runner_or_404(db, runner_id)
    return karvonen_zones(runner.age, runner.resting_hr)
