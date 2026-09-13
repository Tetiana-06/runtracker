"""Pydantic-схеми запитів і відповідей API."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class RunnerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=10, le=95, default=30)
    resting_hr: int = Field(ge=30, le=110, default=60)
    level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    weekly_volume_km: float = Field(ge=0, le=250, default=20.0)
    has_injury_history: bool = False


class RunnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    resting_hr: int
    level: str
    weekly_volume_km: float
    has_injury_history: int


class ShoeCreate(BaseModel):
    runner_id: int
    model: str = Field(min_length=2, max_length=80)
    category: str = Field(default="daily", pattern="^(daily|tempo|trail|race)$")
    mileage_km: float = Field(ge=0, default=0.0)


class ShoeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    runner_id: int
    model: str
    category: str
    mileage_km: float
    retired: int
    purchased_on: date


class ShoeStatus(BaseModel):
    shoe_id: int
    model: str
    mileage_km: float
    limit_km: int
    wear_percent: float
    status: str
    message: str


class RunCreate(BaseModel):
    runner_id: int
    shoe_id: int | None = None
    distance_km: float = Field(gt=0, le=300)
    duration_sec: int = Field(gt=0, le=200_000)
    avg_hr: int | None = Field(default=None, ge=60, le=230)
    workout_type: str = Field(default="easy", pattern="^(easy|long|tempo|intervals|race)$")
    notes: str | None = Field(default=None, max_length=255)
    run_date: date | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    runner_id: int
    shoe_id: int | None
    run_date: date
    distance_km: float
    duration_sec: int
    avg_hr: int | None
    workout_type: str
    notes: str | None


class PlanRequest(BaseModel):
    runner_id: int
    target_distance_km: float = Field(default=10.0)
    weeks: int = Field(ge=4, le=24, default=8)


class PlanOut(BaseModel):
    runner_id: int
    target_distance_km: float
    weeks: int
    plan: list[dict]


class ZoneOut(BaseModel):
    zone: int
    name: str
    lower_hr: int
    upper_hr: int
    purpose: str


class WeeklySummary(BaseModel):
    week_start: date
    total_km: float
    total_time_sec: int
    avg_pace_sec_per_km: float
    runs_count: int
    load: float
