"""  2-  Сервісний шар реалізації вимог GDPR (Privacy Engineering Service).

Реалізує:
- Експорт персональних даних (GDPR Article 15 - Right of Access).
- Керований транзакційний workflow незворотної анонімізації (GDPR Article 17 - Right to Erasure).
- Реєстрацію, відкликання та аудит згод (GDPR Article 7 - Consent Management).
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ConsentAuditLog, PrivacyAuditLog, Run, Runner, Shoe, TrainingPlan, UserConsent

logger = logging.getLogger("app.privacy.service")


def get_runner_or_404(db: Session, runner_id: int) -> Runner:
    """Отримує профіль бігуна за ID або повертає 404 без витоку деталей."""
    runner = db.get(Runner, runner_id)
    if runner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with ID {runner_id} not found",
        )
    return runner


# Завдання 2: Експорт персональних даних (Right of Access)

def _to_iso(dt: Any) -> Any:
    return dt.isoformat() if dt else None


def _parse_preferences(raw_prefs: Any) -> dict[str, Any]:
    if not raw_prefs:
        return {}
    try:
        return json.loads(raw_prefs)
    except Exception:
        return {"raw": raw_prefs}


def _format_run(run: Any) -> dict[str, Any]:
    return {
        "id": run.id,
        "run_date": _to_iso(run.run_date),
        "distance_km": run.distance_km,
        "duration_sec": run.duration_sec,
        "avg_hr": run.avg_hr,
        "workout_type": run.workout_type,
        "notes": run.notes,
    }


def _format_shoe(shoe: Any) -> dict[str, Any]:
    return {
        "id": shoe.id,
        "model": shoe.model,
        "category": shoe.category,
        "mileage_km": shoe.mileage_km,
        "retired": bool(shoe.retired),
        "purchased_on": _to_iso(shoe.purchased_on),
    }


def _format_plan(plan: Any) -> dict[str, Any]:
    return {
        "id": plan.id,
        "target_distance_km": plan.target_distance_km,
        "weeks": plan.weeks,
        "created_at": _to_iso(plan.created_at),
    }


def _format_consent(consent: Any) -> dict[str, Any]:
    return {
        "purpose": consent.purpose,
        "is_granted": consent.is_granted,
        "policy_version": consent.policy_version,
        "source": consent.source,
        "granted_at": _to_iso(consent.granted_at),
        "withdrawn_at": _to_iso(consent.withdrawn_at),
        "updated_at": _to_iso(consent.updated_at),
    }


def export_personal_data(
    db: Session,
    runner_id: int,
    actor_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Формує структурований пакет персональних даних суб'єкта.
    
    Вимоги:
    - Агрегація з усіх джерел (профіль, налаштування, забіги, взуття, плани, згоди).
    - Мінімізація: password_hash, токени та внутрішні секрети НІКОЛИ не повертаються.
    - Передбачувані порожні списки для відсутніх категорій.
    - Фіксація безпечної події аудиту без витоку PII в журнал.
    """
    runner = get_runner_or_404(db, runner_id)

    # 1. Розбір налаштувань користувача
    parsed_settings = _parse_preferences(runner.preferences)

    # 2-5. Агрегація пов'язаних сутностей
    runs_data = [_format_run(run) for run in runner.runs]
    shoes_data = [_format_shoe(shoe) for shoe in runner.shoes]
    plans_data = [_format_plan(plan) for plan in runner.plans]
    consents_data = [_format_consent(consent) for consent in runner.consents]

    export_payload = {
        "export_metadata": {
            "export_id": f"exp-{runner.id}-{uuid.uuid4().hex[:8]}",
            "schema_version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "subject_id": runner.id,
            "data_controller": "RunTracker Privacy Service",
            "legal_basis": "GDPR Article 15 (Right of Access)",
        },
        "categories": [
            "profile",
            "settings",
            "runs",
            "shoes",
            "training_plans",
            "consents",
        ],
        "profile": {
            "id": runner.id,
            "name": runner.name,
            "email": runner.email,
            "phone": runner.phone,
            "age": runner.age,
            "resting_hr": runner.resting_hr,
            "level": runner.level,
            "weekly_volume_km": runner.weekly_volume_km,
            "has_injury_history": runner.has_injury_history,
            "is_active": runner.is_active,
            "is_anonymized": runner.is_anonymized,
            "created_at": _to_iso(runner.created_at),
        },
        "settings": parsed_settings,
        "runs": runs_data,
        "shoes": shoes_data,
        "training_plans": plans_data,
        "consents": consents_data,
    }

    # Фіксація безпечного запису аудиту (без PII у полях аудиту)
    audit = PrivacyAuditLog(
        event_type="DATA_EXPORT",
        subject_id=runner.id,
        actor_id=actor_id,
        status="SUCCESS",
        correlation_id=correlation_id,
        details="Structured personal data export generated (Article 15)",
    )
    db.add(audit)
    db.commit()

    # Безпечне логування події (без витоку самого вмісту JSON)
    logger.info(
        "Privacy Audit | Event=DATA_EXPORT | Subject=%d | Actor=%s | Correlation-ID=%s",
        runner.id,
        actor_id,
        correlation_id,
    )

    return export_payload



# Завдання 3: Анонімізація даних (Right to Erasure / Article 17)

def anonymize_user_data(
    db: Session,
    runner_id: int,
    actor_id: str,
    correlation_id: str,
) -> dict[str, Any]:
    """Виконує транзакційний та ідемпотентний workflow незворотної анонімізації.
    
    Політика обробки сутностей:
    - Runner: ANONYMIZE (ім'я -> нейтральний псевдонім, унікальний анонімний email, видалення телефону та паролю).
    - Runs: RETAIN з деперсоналізацією (збереження показників забігів для спортивної аналітики, видалення notes).
    - Shoes: RETAIN / RETIRE (збереження моделей та пробігу для статистики зносу взуття).
    - Consents: REVOKE (негайне відкликання з фіксацією дати у журналі).
    - Цілісність: зберігаються первинні ключі та зв'язки, відсутні broken foreign keys.
    """
    runner = get_runner_or_404(db, runner_id)

    # 1. Перевірка на ідемпотентність (якщо вже анонімізовано - повертаємо успіх без помилки)
    if runner.is_anonymized:
        return {
            "subject_id": runner.id,
            "status": "already_anonymized",
            "message": "Subject has already been irreversibly anonymized.",
            "anonymized_at": datetime.utcnow().isoformat() + "Z",
            "affected_entities": {
                "runner": 0,
                "runs_sanitized": 0,
                "shoes_retired": 0,
                "consents_revoked": 0,
            },
        }

    try:
        # 2. Незворотна анонімізація профілю бігуна
        runner.name = f"Anonymized Runner #{runner.id}"
        runner.email = f"deleted_runner_{runner.id}@anonymized.local"
        runner.phone = None
        runner.password_hash = None
        runner.preferences = "{}"
        runner.has_injury_history = 0
        runner.is_active = False
        runner.is_anonymized = True

        # 3. Деперсоналізація забігів (Retention rule: метрики зберігаються, примітки видаляються)
        runs_count = 0
        for run in runner.runs:
            run.notes = "[REDACTED_NOTES]"
            runs_count += 1

        # 4. Переведення кросівок у стан retired
        shoes_count = 0
        for shoe in runner.shoes:
            shoe.retired = 1
            shoes_count += 1

        # 5. Очищення тренувальних планів
        for plan in runner.plans:
            plan.payload = "{}"

        # 6. Відкликання всіх активних згод суб'єкта
        revoked_consents = 0
        now_dt = datetime.utcnow()
        for consent in runner.consents:
            if consent.is_granted:
                consent.is_granted = False
                consent.withdrawn_at = now_dt
                consent.source = "gdpr_erasure_workflow"
                revoked_consents += 1

                # Запис в аудит-лог згод про відкликання
                audit_consent = ConsentAuditLog(
                    runner_id=runner.id,
                    consent_id=consent.id,
                    purpose=consent.purpose,
                    action="REVOKE",
                    policy_version=consent.policy_version,
                    source="gdpr_erasure_workflow",
                    timestamp=now_dt,
                )
                db.add(audit_consent)

        # 7. Запис у безпечний Privacy Audit Log (без збереження видалених PII!)
        audit = PrivacyAuditLog(
            event_type="ERASURE_ANONYMIZE",
            subject_id=runner.id,
            actor_id=actor_id,
            status="SUCCESS",
            correlation_id=correlation_id,
            details=f"Anonymized profile, sanitized {runs_count} runs, revoked {revoked_consents} consents",
        )
        db.add(audit)

        # Атомарна фіксація транзакції в БД
        db.commit()

        # Безпечне логування операції
        logger.info(
            "Privacy Audit | Event=ERASURE_ANONYMIZE | Subject=%d | Actor=%s | RunsSanitized=%d | Correlation-ID=%s",
            runner.id,
            actor_id,
            runs_count,
            correlation_id,
        )

        return {
            "subject_id": runner.id,
            "status": "anonymized",
            "message": "Subject personal data has been irreversibly anonymized.",
            "anonymized_at": now_dt.isoformat() + "Z",
            "affected_entities": {
                "runner": 1,
                "runs_sanitized": runs_count,
                "shoes_retired": shoes_count,
                "consents_revoked": revoked_consents,
            },
        }

    except Exception:
        db.rollback()
        logger.error(
            "Privacy Audit | Event=ERASURE_FAILED | Subject=%d | Actor=%s | Correlation-ID=%s",
            runner_id,
            actor_id,
            correlation_id,
        )
        raise


# ============================================================================
# Завдання 4: Керування згодами (Consent Management Engine)
# ============================================================================

def grant_consent(
    db: Session,
    runner_id: int,
    purpose: str,
    policy_version: str,
    source: str,
) -> UserConsent:
    """Реєструє надання згоди для конкретної мети із фіксацією версії та аудиту."""
    runner = get_runner_or_404(db, runner_id)

    consent = (
        db.query(UserConsent)
        .filter(UserConsent.runner_id == runner.id, UserConsent.purpose == purpose)
        .first()
    )

    now_dt = datetime.utcnow()
    if not consent:
        consent = UserConsent(
            runner_id=runner.id,
            purpose=purpose,
            is_granted=True,
            policy_version=policy_version,
            source=source,
            granted_at=now_dt,
            withdrawn_at=None,
        )
        db.add(consent)
        db.flush()
    else:
        consent.is_granted = True
        consent.policy_version = policy_version
        consent.source = source
        consent.granted_at = now_dt
        consent.withdrawn_at = None

    # Фіксація події надання згоди у незмінному журналі аудиту
    audit = ConsentAuditLog(
        runner_id=runner.id,
        consent_id=consent.id,
        purpose=purpose,
        action="GRANT",
        policy_version=policy_version,
        source=source,
        timestamp=now_dt,
    )
    db.add(audit)
    db.commit()
    db.refresh(consent)

    logger.info(
        "Consent Audit | Action=GRANT | Subject=%d | Purpose=%s | Version=%s | Source=%s",
        runner.id,
        purpose,
        policy_version,
        source,
    )
    return consent


def revoke_consent(
    db: Session,
    runner_id: int,
    purpose: str,
    source: str = "web_settings",
) -> UserConsent:
    """Негайно відкликає згоду суб'єкта даних із фіксацією у журналі аудиту (Zero Delay)."""
    runner = get_runner_or_404(db, runner_id)

    consent = (
        db.query(UserConsent)
        .filter(UserConsent.runner_id == runner.id, UserConsent.purpose == purpose)
        .first()
    )

    now_dt = datetime.utcnow()
    if not consent:
        consent = UserConsent(
            runner_id=runner.id,
            purpose=purpose,
            is_granted=False,
            policy_version="1.0",
            source=source,
            granted_at=None,
            withdrawn_at=now_dt,
        )
        db.add(consent)
        db.flush()
    else:
        consent.is_granted = False
        consent.withdrawn_at = now_dt

    audit = ConsentAuditLog(
        runner_id=runner.id,
        consent_id=consent.id,
        purpose=purpose,
        action="REVOKE",
        policy_version=consent.policy_version,
        source=source,
        timestamp=now_dt,
    )
    db.add(audit)
    db.commit()
    db.refresh(consent)

    logger.info(
        "Consent Audit | Action=REVOKE | Subject=%d | Purpose=%s | Timestamp=%s",
        runner.id,
        purpose,
        now_dt.isoformat(),
    )
    return consent


def get_user_consents(db: Session, runner_id: int) -> list[UserConsent]:
    """Повертає перелік актуальних згод користувача."""
    get_runner_or_404(db, runner_id)
    return db.query(UserConsent).filter(UserConsent.runner_id == runner_id).all()


def get_consent_history(db: Session, runner_id: int) -> list[ConsentAuditLog]:
    """Повертає повну історію змін згод (Accountability log)."""
    get_runner_or_404(db, runner_id)
    return (
        db.query(ConsentAuditLog)
        .filter(ConsentAuditLog.runner_id == runner_id)
        .order_by(ConsentAuditLog.timestamp.asc())
        .all()
    )
