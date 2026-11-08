"""  3 - ORM-моделі предметної області: бігун, тренування, кросівки, план, згоди, аудит.

Відповідає принципам Privacy by Design та вимогам GDPR (Articles 7, 15, 17):
- Зберігання PII (ім'я, email, телефон, налаштування).
- Підтримка статусу анонімізації (is_anonymized).
- Керування згодами суб'єкта даних (UserConsent).
- Журнали аудиту для доказовості (ConsentAuditLog, PrivacyAuditLog).
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Runner(Base):
    """Профіль бігуна (суб'єкт персональних даних / User Profile)."""

    __tablename__ = "runners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    resting_hr: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="beginner")
    weekly_volume_km: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    has_injury_history: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # !!!!!!!!
    is_anonymized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Зв'язки сутностей
    runs: Mapped[list["Run"]] = relationship(back_populates="runner", cascade="all, delete-orphan")
    shoes: Mapped[list["Shoe"]] = relationship(back_populates="runner", cascade="all, delete-orphan")
    plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="runner", cascade="all, delete-orphan")
    consents: Mapped[list["UserConsent"]] = relationship(back_populates="runner", cascade="all, delete-orphan")


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
    """Одне виконане тренування (активність користувача)."""

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


class UserConsent(Base):
    """Модель згоди суб'єкта даних (GDPR Article 7 - Conditions for consent).
    
    Зберігає актуальний стан згоди для конкретної мети (purpose-specific),
    версію політики, джерело згоди та часові мітки надання/відкликання.
    """

    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., MARKETING_EMAIL, OPTIONAL_ANALYTICS
    is_granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="web_settings")
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    runner: Mapped["Runner"] = relationship(back_populates="consents")


class ConsentAuditLog(Base):
    """Незмінний журнал історії змін згод (Accountability / Доказовість).
    
    Дозволяє відтворити хронологію надання та відкликання згод користувачем.
    """

    __tablename__ = "consent_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runner_id: Mapped[int] = mapped_column(ForeignKey("runners.id"), nullable=False)
    consent_id: Mapped[int | None] = mapped_column(ForeignKey("user_consents.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # GRANT, REVOKE
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PrivacyAuditLog(Base):
    """Безпечний журнал аудиту операцій з персональними даними.
    
    Фіксує факт виконання Privacy-операцій (експорт, анонімізація)
    БЕЗ збереження самих видалених чи експортованих PII-значень.
    """

    __tablename__ = "privacy_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # DATA_EXPORT, ERASURE_ANONYMIZE
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # SUCCESS, DENIED
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
