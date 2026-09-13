"""Маршрути обліку бігового взуття."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Runner, Shoe
from app.schemas import ShoeCreate, ShoeOut, ShoeStatus
from app.services.gear import check_equipment_status, fleet_overview

router = APIRouter(prefix="/api/shoes", tags=["shoes"])


def to_dict(shoe: Shoe) -> dict:
    return {
        "id": shoe.id,
        "model": shoe.model,
        "category": shoe.category,
        "mileage_km": shoe.mileage_km,
        "retired": shoe.retired,
    }


def runner_to_dict(runner: Runner | None) -> dict | None:
    if runner is None:
        return None
    return {
        "level": runner.level,
        "weekly_volume_km": runner.weekly_volume_km,
        "has_injury_history": runner.has_injury_history,
    }


@router.post("", response_model=ShoeOut, status_code=status.HTTP_201_CREATED)
def create_shoe(payload: ShoeCreate, db: Session = Depends(get_db)) -> Shoe:
    if db.get(Runner, payload.runner_id) is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    shoe = Shoe(
        runner_id=payload.runner_id,
        model=payload.model,
        category=payload.category,
        mileage_km=payload.mileage_km,
    )
    db.add(shoe)
    db.commit()
    db.refresh(shoe)
    return shoe


@router.get("", response_model=list[ShoeOut])
def list_shoes(runner_id: int, db: Session = Depends(get_db)) -> list[Shoe]:
    return db.query(Shoe).filter(Shoe.runner_id == runner_id).order_by(Shoe.id).all()


@router.get("/{shoe_id}/status", response_model=ShoeStatus)
def shoe_status(shoe_id: int, db: Session = Depends(get_db)) -> dict:
    shoe = db.get(Shoe, shoe_id)
    if shoe is None:
        raise HTTPException(status_code=404, detail="Shoe not found")
    runner = db.get(Runner, shoe.runner_id)
    return check_equipment_status(to_dict(shoe), runner_to_dict(runner))


@router.get("/overview/{runner_id}")
def overview(runner_id: int, db: Session = Depends(get_db)) -> dict:
    runner = db.get(Runner, runner_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    shoes = db.query(Shoe).filter(Shoe.runner_id == runner_id).all()
    return fleet_overview([to_dict(shoe) for shoe in shoes], runner_to_dict(runner))


@router.post("/{shoe_id}/retire", response_model=ShoeOut)
def retire_shoe(shoe_id: int, db: Session = Depends(get_db)) -> Shoe:
    shoe = db.get(Shoe, shoe_id)
    if shoe is None:
        raise HTTPException(status_code=404, detail="Shoe not found")
    shoe.retired = 1
    db.commit()
    db.refresh(shoe)
    return shoe
