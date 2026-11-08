""" - API-маршрути Privacy Engineering та вимог GDPR (Articles 7, 15, 17).

Ендпоінти:
- GET /api/users/{id}/personal-data: Експорт персональних даних (Право на доступ).
- POST /api/users/{id}/anonymize: Workflow незворотної анонімізації (Право на забуття).
- POST /api/users/{id}/consents/grant: Надання згоди на конкретну мету.
- POST /api/users/{id}/consents/revoke: Негайне відкликання згоди.
- GET /api/users/{id}/consents: Перегляд дійсних згод.
- GET /api/users/{id}/consents/history: Журнал аудиту згод (Accountability).
- POST /api/users/{id}/actions/marketing-digest: Дія під контролем Consent Policy Gate.
- POST /api/users/{id}/actions/track-analytics: Додаткова дія під контролем Consent Policy Gate.
(Усі маршрути також доступні за аліасом /api/runners/{id}/...).
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.privacy.policy_gate import ConsentPolicyGate
from app.privacy.security import Principal, get_current_principal, verify_subject_access
from app.privacy.service import (
    anonymize_user_data,
    export_personal_data,
    get_consent_history,
    get_user_consents,
    grant_consent,
    revoke_consent,
)
from app.schemas import (
    AnonymizeResponse,
    ConsentAuditOut,
    ConsentGrantRequest,
    ConsentRevokeRequest,
    MarketingDigestResponse,
    PersonalDataExport,
    TrackAnalyticsResponse,
    UserConsentOut,
)

router = APIRouter(tags=["privacy"])


def _extract_meta(request: Request, principal: Principal) -> tuple[str, str]:
    """Витягує correlation_id та безпечний actor_id із контексту запиту."""
    correlation_id = getattr(request.state, "correlation_id", None) or f"gen-{uuid.uuid4().hex[:8]}"
    actor_id = getattr(request.state, "actor_id", None) or (f"user-{principal.user_id}" if principal.user_id else "anonymous")
    return correlation_id, actor_id


# Завдання 2: Експорт персональних даних (GDPR Article 15)

@router.get("/api/users/{subject_id}/personal-data", response_model=PersonalDataExport)
@router.get("/api/runners/{subject_id}/personal-data", response_model=PersonalDataExport)
def get_personal_data_export(
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Формує авторизований structured export персональних даних суб'єкта."""
    # Контроль доступу (захист від IDOR): лише власник або admin
    verify_subject_access(principal, subject_id)

    correlation_id, actor_id = _extract_meta(request, principal)
    return export_personal_data(db, subject_id, actor_id, correlation_id)



# Завдання 3: Right to Erasure / Anonymization Workflow (GDPR Article 17)

@router.post("/api/users/{subject_id}/anonymize", response_model=AnonymizeResponse)
@router.post("/api/runners/{subject_id}/anonymize", response_model=AnonymizeResponse)
@router.delete("/api/users/{subject_id}", response_model=AnonymizeResponse)
@router.delete("/api/runners/{subject_id}", response_model=AnonymizeResponse)
def anonymize_user(
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Виконує транзакційний та ідемпотентний workflow незворотної анонімізації суб'єкта."""
    verify_subject_access(principal, subject_id)

    correlation_id, actor_id = _extract_meta(request, principal)
    return anonymize_user_data(db, subject_id, actor_id, correlation_id)



# Завдання 4: Consent Management Engine (GDPR Article 7)

@router.get("/api/users/{subject_id}/consents", response_model=list[UserConsentOut])
@router.get("/api/runners/{subject_id}/consents", response_model=list[UserConsentOut])
def list_consents(
    subject_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Повертає список актуальних згод користувача."""
    verify_subject_access(principal, subject_id)
    return get_user_consents(db, subject_id)


@router.post("/api/users/{subject_id}/consents/grant", response_model=UserConsentOut, status_code=status.HTTP_200_OK)
@router.post("/api/runners/{subject_id}/consents/grant", response_model=UserConsentOut, status_code=status.HTTP_200_OK)
def handle_grant_consent(
    subject_id: int,
    payload: ConsentGrantRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Реєструє надання згоди для конкретної мети обробки."""
    verify_subject_access(principal, subject_id)
    return grant_consent(
        db,
        runner_id=subject_id,
        purpose=payload.purpose,
        policy_version=payload.policy_version,
        source=payload.source,
    )


@router.post("/api/users/{subject_id}/consents/revoke", response_model=UserConsentOut, status_code=status.HTTP_200_OK)
@router.post("/api/runners/{subject_id}/consents/revoke", response_model=UserConsentOut, status_code=status.HTTP_200_OK)
def handle_revoke_consent(
    subject_id: int,
    payload: ConsentRevokeRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Негайно відкликає надану згоду (Zero Delay Revocation)."""
    verify_subject_access(principal, subject_id)
    return revoke_consent(
        db,
        runner_id=subject_id,
        purpose=payload.purpose,
    )


@router.get("/api/users/{subject_id}/consents/history", response_model=list[ConsentAuditOut])
@router.get("/api/runners/{subject_id}/consents/history", response_model=list[ConsentAuditOut])
def get_history(
    subject_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Повертає історію аудиту змін згод (Accountability)."""
    verify_subject_access(principal, subject_id)
    return get_consent_history(db, subject_id)



# Залежні операції для перевірки Policy Gate

@router.post("/api/users/{subject_id}/actions/marketing-digest", response_model=MarketingDigestResponse)
@router.post("/api/runners/{subject_id}/actions/marketing-digest", response_model=MarketingDigestResponse)
def send_marketing_digest(
    subject_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Маркетингова операція: виконується ТІЛЬКИ за наявності активної згоди MARKETING_EMAIL."""
    verify_subject_access(principal, subject_id)

    # Consent Policy Gate перевіряє актуальний стан згоди безпосередньо перед дією
    ConsentPolicyGate.enforce(db, subject_id, "MARKETING_EMAIL")

    return {
        "status": "allowed",
        "action": "marketing_digest_sent",
        "recipient_id": subject_id,
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "digest_preview": "Weekly Marathon Preparation Digest: Tips, Hydration & Shoe Discounts",
    }


@router.post("/api/users/{subject_id}/actions/track-analytics", response_model=TrackAnalyticsResponse)
@router.post("/api/runners/{subject_id}/actions/track-analytics", response_model=TrackAnalyticsResponse)
def track_optional_analytics(
    subject_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Any:
    """Збір розширеної аналітики: виконується ТІЛЬКИ за згоди OPTIONAL_ANALYTICS (ізоляція цілей)."""
    verify_subject_access(principal, subject_id)

    # Consent Policy Gate для іншої окремої мети
    ConsentPolicyGate.enforce(db, subject_id, "OPTIONAL_ANALYTICS")

    return {
        "status": "allowed",
        "action": "analytics_event_recorded",
        "subject_id": subject_id,
        "recorded_at": datetime.utcnow().isoformat() + "Z",
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
    }
