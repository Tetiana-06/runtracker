"""ORM-моделі предметної області: бігун, тренування, кросівки, план."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Runner(Base):
    """Профіль бігуна: базові антропометричні та тренувальні дані."""

    __tablename__ = "runners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    resting_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="beginner")
    weekly_volume_km: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    has_injury_history: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    runs: Mapped[list["Run"]] = relationship(back_populates="runner", cascade="all, delete-orphan")
    shoes: Mapped[list["Shoe"]] = relationship(back_populates="runner", cascade="all, delete-orphan")
    plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="runner", cascade="all, delete-orphan")


class Shoe(Base):
    """Бігові кросівки та їхній накопичений пробіг."""

    __tablename__ = "shoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    purchased_on: Mapped[date] = mapped_column(Date, default=date.today)
    mileage_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    retired: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    runner: Mapped["Runner"] = relationship(back_populates="shoes")
    runs: Mapped[list["Run"]] = relationship(back_populates="shoe")


class Run(Base):
    """Одне виконане тренування."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), nullable=False)
    shoe_id: Mapped[int | None] = mapped_column(ForeignKey("shoes.id"), nullable=True)
    run_date: Mapped[date] = mapped_column(Date, default=date.today)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workout_type: Mapped[str] = mapped_column(String(20), nullable=False, default="easy")
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    runner: Mapped["Runner"] = relationship(back_populates="runs")
    shoe: Mapped["Shoe | None"] = relationship(back_populates="runs")


class TrainingPlan(Base):
    """Згенерований план підготовки до забігу (тижні зберігаються як JSON)."""

    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), nullable=False)
    target_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    runner: Mapped["Runner"] = relationship(back_populates="plans")
