"""Pydantic-схеми запитів і відповідей API.

Включає схеми предметної області та моделі для Privacy Engineering:
- Персональні дані бігуна.
- Контракт експорту персональних даних (GDPR Article 15).
- Керування згодами (GDPR Article 7).
- Відповіді на запити анонімізації (GDPR Article 17).
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunnerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, max_length=100)
    age: int = Field(ge=10, le=95, default=30)
    resting_hr: int = Field(ge=30, le=110, default=60)
    level: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    weekly_volume_km: float = Field(ge=0, le=250, default=20.0)
    has_injury_history: bool = False
    preferences: str | dict[str, Any] | None = None


class RunnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    age: int
    resting_hr: int
    level: str
    weekly_volume_km: float
    has_injury_history: int
    is_active: bool = True
    is_anonymized: bool = False
    created_at: datetime | None = None


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


# ============================================================================
# Privacy & GDPR Schemas (Articles 7, 15, 17)
# ============================================================================

class ExportMetadata(BaseModel):
    """Метадані вивантаження персональних даних (контрольованість і стабільність схеми)."""
    export_id: str
    schema_version: str = "1.0"
    generated_at: str
    subject_id: int
    data_controller: str = "RunTracker Privacy Service"
    legal_basis: str = "GDPR Article 15 (Right of Access)"


class PersonalDataExport(BaseModel):
    """Повний структурований пакет персональних даних відповідно до GDPR Art. 15."""
    export_metadata: ExportMetadata
    categories: list[str]
    profile: dict[str, Any]
    settings: dict[str, Any]
    runs: list[dict[str, Any]]
    shoes: list[dict[str, Any]]
    training_plans: list[dict[str, Any]]
    consents: list[dict[str, Any]]


class AnonymizeResponse(BaseModel):
    """Результат виконання workflow незворотної анонімізації (GDPR Art. 17)."""
    subject_id: int
    status: str
    message: str
    anonymized_at: str
    affected_entities: dict[str, int]


class ConsentGrantRequest(BaseModel):
    """Запит на надання згоди на конкретну мету обробки (GDPR Art. 7)."""
    purpose: str = Field(
        ...,
        pattern="^(MARKETING_EMAIL|OPTIONAL_ANALYTICS|THIRD_PARTY_SHARING)$",
        description="Конкретна мета обробки даних",
    )
    policy_version: str = Field(default="1.0", max_length=20)
    source: str = Field(default="web_privacy_center", max_length=50)


class ConsentRevokeRequest(BaseModel):
    """Запит на відкликання згоди."""
    purpose: str = Field(
        ...,
        pattern="^(MARKETING_EMAIL|OPTIONAL_ANALYTICS|THIRD_PARTY_SHARING)$",
        description="Мета, для якої згода відкликається",
    )


class UserConsentOut(BaseModel):
    """Представлення актуальної згоди користувача."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    runner_id: int
    purpose: str
    is_granted: bool
    policy_version: str
    source: str
    granted_at: datetime | None
    withdrawn_at: datetime | None
    updated_at: datetime


class ConsentAuditOut(BaseModel):
    """Запис аудиту життєвого циклу згоди."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    runner_id: int
    purpose: str
    action: str
    policy_version: str
    source: str
    timestamp: datetime


class MarketingDigestResponse(BaseModel):
    """Результат виконання маркетингової операції під контролем Policy Gate."""
    status: str
    action: str
    recipient_id: int
    sent_at: str
    digest_preview: str


class TrackAnalyticsResponse(BaseModel):
    """Результат аналітичної операції під контролем Policy Gate."""
    status: str
    action: str
    subject_id: int
    recorded_at: str
    event_id: str
