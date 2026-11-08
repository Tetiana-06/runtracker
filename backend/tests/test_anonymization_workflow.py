"""Інтеграційні тести для Завдання 3: Right to Erasure / Anonymization Workflow (GDPR Article 17).

Перевіряють:
- Транзакційний та незворотний workflow анонімізації персональних даних.
- Повну відсутність початкових PII в усіх охоплених сутностях (профіль, забіги, згоди).
- Збереження бізнес-записів (Retention rule: забіги зберігаються для зведеної аналітики).
- Збереження референційної цілісності бази даних (відсутність broken foreign keys та orphan rows).
- Ідемпотентність повторного запуску (safe replay без помилок).
- Контроль доступу (заборона виконання стороннім користувачем - 403 Forbidden).
- Фіксацію privacy-safe audit event без збереження видалених значень.
"""

from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import ConsentAuditLog, PrivacyAuditLog, Run, Runner, Shoe, UserConsent

client = TestClient(app)


def setup_function():
    """Створює чисту схему БД перед кожним тестом."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_user_with_full_footprint(db: Session) -> Runner:
    """Створює повний слід користувача в системі з PII та зв'язками."""
    runner = Runner(
        name="Оксана Коваль",
        email="oksana.koval@sport.ua",
        phone="+380951112233",
        password_hash="argon2$secret_user_password_hash_value",
        age=28,
        resting_hr=52,
        level="advanced",
        weekly_volume_km=60.0,
        has_injury_history=1,
        preferences='{"locale": "uk_UA", "private_account": true}',
    )
    db.add(runner)
    db.commit()
    db.refresh(runner)

    shoe = Shoe(
        runner_id=runner.id,
        model="Asics Gel Nimbus 25",
        category="daily",
        purchased_on=date(2026, 2, 1),
        mileage_km=320.0,
    )
    db.add(shoe)
    db.commit()
    db.refresh(shoe)

    run = Run(
        runner_id=runner.id,
        shoe_id=shoe.id,
        run_date=date(2026, 3, 10),
        distance_km=15.0,
        duration_sec=4500,
        avg_hr=150,
        workout_type="long",
        notes="Тренування на стадіоні Динамо з тренером Володимиром",
    )
    db.add(run)

    consent = UserConsent(
        runner_id=runner.id,
        purpose="MARKETING_EMAIL",
        is_granted=True,
        policy_version="1.0",
        source="promo_page",
    )
    db.add(consent)

    db.commit()
    db.refresh(runner)
    return runner


def test_positive_anonymization_workflow_and_referential_integrity():
    """Позитивний тест: повна деперсоналізація суб'єкта зі збереженням бізнес-записів."""
    db = SessionLocal()
    try:
        runner = create_user_with_full_footprint(db)
        subject_id = runner.id
        shoe_id = runner.shoes[0].id
        run_id = runner.runs[0].id
    finally:
        db.close()

    # Авторизований запит на виконання workflow анонімізації
    headers = {"X-User-Id": str(subject_id)}
    response = client.post(f"/api/users/{subject_id}/anonymize", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["subject_id"] == subject_id
    assert data["status"] == "anonymized"
    assert "affected_entities" in data
    assert data["affected_entities"]["runs_sanitized"] == 1
    assert data["affected_entities"]["consents_revoked"] == 1

    # =========================================================================
    # Перевірка фактичного стану сховища даних (Бази Даних)
    # =========================================================================
    db = SessionLocal()
    try:
        updated_runner = db.get(Runner, subject_id)
        assert updated_runner is not None

        # 1. Прямі ідентифікатори незворотно замінені
        assert updated_runner.name == f"Anonymized Runner #{subject_id}"
        assert updated_runner.email == f"deleted_runner_{subject_id}@anonymized.local"
        assert updated_runner.phone is None
        assert updated_runner.password_hash is None
        assert updated_runner.preferences == "{}"
        assert updated_runner.is_active is False
        assert updated_runner.is_anonymized is True
        assert updated_runner.has_injury_history == 0

        # Перевірка: оригінальні PII повністю відсутні в об'єкті
        assert "Оксана Коваль" != updated_runner.name
        assert "oksana.koval@sport.ua" != updated_runner.email
        assert "+380951112233" != updated_runner.phone

        # 2. Перевірка збереження бізнес-записів та референційної цілісності (Runs)
        runs = db.query(Run).filter(Run.runner_id == subject_id).all()
        assert len(runs) == 1
        anonymized_run = runs[0]
        assert anonymized_run.id == run_id
        assert anonymized_run.distance_km == 15.0  # Збережено для статистики
        assert anonymized_run.duration_sec == 4500
        # Чутливі коментарі деперсоналізовано
        assert anonymized_run.notes == "[REDACTED_NOTES]"
        assert "Володимиром" not in (anonymized_run.notes or "")

        # 3. Перевірка екіпірування
        shoes = db.query(Shoe).filter(Shoe.runner_id == subject_id).all()
        assert len(shoes) == 1
        assert shoes[0].retired == 1

        # 4. Перевірка згод суб'єкта
        consents = db.query(UserConsent).filter(UserConsent.runner_id == subject_id).all()
        assert len(consents) == 1
        assert consents[0].is_granted is False
        assert consents[0].withdrawn_at is not None
        assert consents[0].source == "gdpr_erasure_workflow"

        # 5. Перевірка фіксації відкликання в аудит-лозі згод
        consent_audits = db.query(ConsentAuditLog).filter(ConsentAuditLog.runner_id == subject_id).all()
        assert any(ca.action == "REVOKE" and ca.source == "gdpr_erasure_workflow" for ca in consent_audits)

        # 6. Перевірка запису в безпечному журналі PrivacyAuditLog
        privacy_audits = (
            db.query(PrivacyAuditLog)
            .filter(
                PrivacyAuditLog.subject_id == subject_id,
                PrivacyAuditLog.event_type == "ERASURE_ANONYMIZE",
            )
            .all()
        )
        assert len(privacy_audits) >= 1
        audit_rec = privacy_audits[0]
        assert audit_rec.status == "SUCCESS"
        # Перевірка: audit_rec НЕ містить старих PII!
        assert "oksana" not in audit_rec.details.lower()
        assert "380951112233" not in audit_rec.details

    finally:
        db.close()


def test_idempotency_of_anonymization_workflow():
    """Тест ідемпотентності: повторний запуск не викликає помилок і повертає safe status."""
    db = SessionLocal()
    try:
        runner = create_user_with_full_footprint(db)
        subject_id = runner.id
    finally:
        db.close()

    headers = {"X-User-Id": str(subject_id)}

    # Перший запуск -> успішна анонімізація
    resp1 = client.post(f"/api/users/{subject_id}/anonymize", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "anonymized"

    # Другий запуск (replay) -> ідемпотентна відповідь already_anonymized
    resp2 = client.post(f"/api/users/{subject_id}/anonymize", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_anonymized"

    # Перевірка через DELETE /api/runners/{id}
    resp3 = client.delete(f"/api/runners/{subject_id}", headers=headers)
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "already_anonymized"


def test_negative_authorization_anonymize_other_user():
    """Негативний тест: спроба стороннього користувача анонімізувати чужий профіль (403 Forbidden)."""
    db = SessionLocal()
    try:
        victim = Runner(name="Жертва", email="victim@run.ua")
        attacker = Runner(name="Зловмисник", email="attacker@run.ua")
        db.add_all([victim, attacker])
        db.commit()
        victim_id, attacker_id = victim.id, attacker.id
    finally:
        db.close()

    attacker_headers = {"X-User-Id": str(attacker_id)}
    response = client.post(f"/api/users/{victim_id}/anonymize", headers=attacker_headers)

    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]

    # Перевірка: дані жертви залишилися недоторканими
    db = SessionLocal()
    try:
        unchanged = db.get(Runner, victim_id)
        assert unchanged.is_anonymized is False
        assert unchanged.name == "Жертва"
        assert unchanged.email == "victim@run.ua"
    finally:
        db.close()
