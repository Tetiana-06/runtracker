"""  4 -Інтеграційні тести для Завдання 4: Consent Management Engine (GDPR Article 7).

Перевіряють:
- Повний життєвий цикл згоди та Policy Gate за сценарієм:
  GRANT -> ALLOW -> REVOKE -> DENY
- Фіксацію обов'язкових метаданих: policy_version, timestamps (granted_at, withdrawn_at), source.
- Доказовість та історію змін у незмінному журналі ConsentAuditLog (Accountability).
- Принцип ізоляції цілей (Purpose Limitation: згода на маркетинг не відкриває аналітику).
- Негайне застосування відкликання без затримок (Zero Delay Enforcement).
- Незалежність базової бізнес-функціональності від опціональних згод.
- Авторизацію та захист від модифікації згод сторонніми користувачами (403 Forbidden).
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Runner

client = TestClient(app)


def setup_function():
    """Створює чисту схему БД перед кожним тестом."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_full_consent_lifecycle_scenario_grant_allow_revoke_deny():
    """Еталонний інтеграційний тест сценарію:
    1. Початковий стан: DENY (відсутність згоди блокує залежну дію).
    2. GRANT: Надання згоди на мету MARKETING_EMAIL з фіксацією версії 1.0 та джерела.
    3. ALLOW: Дозволене виконання залежної дії з фіксацією бізнес-результату.
    4. Ізоляція цілей: Згода на маркетинг НЕ дозволяє виконання аналітики (DENY).
    5. REVOKE: Негайне відкликання згоди на MARKETING_EMAIL.
    6. DENY: Повторна дія миттєво блокується Policy Gate без побічного ефекту.
    7. Журнал аудиту: Повна історія переходів збережена в ConsentAuditLog.
    """
    db = SessionLocal()
    try:
        runner = Runner(
            name="Андрій Кравченко",
            email="andriy.kravchenko@run.ua",
            phone="+380503332211",
        )
        db.add(runner)
        db.commit()
        db.refresh(runner)
        subject_id = runner.id
    finally:
        db.close()

    headers = {"X-User-Id": str(subject_id)}

    # -------------------------------------------------------------------------
    # Етап 1: Початковий стан (NO CONSENT) -> DENY
    # -------------------------------------------------------------------------
    resp_init = client.post(
        f"/api/users/{subject_id}/actions/marketing-digest",
        headers=headers,
    )
    assert resp_init.status_code == 403
    assert "no active consent for purpose 'MARKETING_EMAIL'" in resp_init.json()["detail"]

    # -------------------------------------------------------------------------
    # Етап 2: GRANT згоди на MARKETING_EMAIL
    # -------------------------------------------------------------------------
    grant_payload = {
        "purpose": "MARKETING_EMAIL",
        "policy_version": "1.0",
        "source": "web_privacy_modal",
    }
    resp_grant = client.post(
        f"/api/users/{subject_id}/consents/grant",
        json=grant_payload,
        headers=headers,
    )
    assert resp_grant.status_code == 200
    consent_data = resp_grant.json()
    assert consent_data["purpose"] == "MARKETING_EMAIL"
    assert consent_data["is_granted"] is True
    assert consent_data["policy_version"] == "1.0"
    assert consent_data["source"] == "web_privacy_modal"
    assert consent_data["granted_at"] is not None
    assert consent_data["withdrawn_at"] is None

    # -------------------------------------------------------------------------
    # Етап 3: ALLOW -> залежна дія дозволена та виконана
    # -------------------------------------------------------------------------
    resp_allow = client.post(
        f"/api/users/{subject_id}/actions/marketing-digest",
        headers=headers,
    )
    assert resp_allow.status_code == 200
    assert resp_allow.json()["status"] == "allowed"
    assert resp_allow.json()["action"] == "marketing_digest_sent"
    assert resp_allow.json()["recipient_id"] == subject_id

    # -------------------------------------------------------------------------
    # Етап 4: Ізоляція цілей (Purpose Limitation)
    # Згода на MARKETING_EMAIL не відкриває доступ до OPTIONAL_ANALYTICS
    # -------------------------------------------------------------------------
    resp_analytics = client.post(
        f"/api/users/{subject_id}/actions/track-analytics",
        headers=headers,
    )
    assert resp_analytics.status_code == 403
    assert "OPTIONAL_ANALYTICS" in resp_analytics.json()["detail"]

    # -------------------------------------------------------------------------
    # Етап 5: REVOKE згоди
    # -------------------------------------------------------------------------
    revoke_payload = {"purpose": "MARKETING_EMAIL"}
    resp_revoke = client.post(
        f"/api/users/{subject_id}/consents/revoke",
        json=revoke_payload,
        headers=headers,
    )
    assert resp_revoke.status_code == 200
    revoked_data = resp_revoke.json()
    assert revoked_data["purpose"] == "MARKETING_EMAIL"
    assert revoked_data["is_granted"] is False
    assert revoked_data["withdrawn_at"] is not None

    # -------------------------------------------------------------------------
    # Етап 6: Миттєвий DENY після відкликання (Zero Delay)
    # -------------------------------------------------------------------------
    resp_deny = client.post(
        f"/api/users/{subject_id}/actions/marketing-digest",
        headers=headers,
    )
    assert resp_deny.status_code == 403
    assert "no active consent for purpose 'MARKETING_EMAIL'" in resp_deny.json()["detail"]

    # -------------------------------------------------------------------------
    # Етап 7: Перевірка повноти історії аудиту (Accountability Log)
    # -------------------------------------------------------------------------
    resp_history = client.get(
        f"/api/users/{subject_id}/consents/history",
        headers=headers,
    )
    assert resp_history.status_code == 200
    history = resp_history.json()
    assert len(history) == 2

    # Перша подія - GRANT
    assert history[0]["action"] == "GRANT"
    assert history[0]["purpose"] == "MARKETING_EMAIL"
    assert history[0]["policy_version"] == "1.0"
    assert history[0]["source"] == "web_privacy_modal"

    # Друга подія - REVOKE
    assert history[1]["action"] == "REVOKE"
    assert history[1]["purpose"] == "MARKETING_EMAIL"


def test_core_functionality_not_blocked_by_optional_consent():
    """Тест: базова бізнес-логіка (створення забігу) НЕ залежить від маркетингових згод."""
    db = SessionLocal()
    try:
        runner = Runner(name="Сергій", email="serhiy@run.ua")
        db.add(runner)
        db.commit()
        db.refresh(runner)
        subject_id = runner.id
    finally:
        db.close()

    # Жодної згоди не надано, але додавання забігу має успішно працювати
    run_payload = {
        "runner_id": subject_id,
        "distance_km": 5.0,
        "duration_sec": 1500,
        "workout_type": "easy",
    }
    resp = client.post("/api/runs", json=run_payload)
    assert resp.status_code == 201
    assert resp.json()["distance_km"] == 5.0


def test_negative_authorization_consent_modification():
    """Негативний тест: спроба стороннього користувача змінити чужу згоду (403 Forbidden)."""
    db = SessionLocal()
    try:
        runner1 = Runner(name="Власник", email="owner@run.ua")
        runner2 = Runner(name="Сторонній", email="other@run.ua")
        db.add_all([runner1, runner2])
        db.commit()
        id1, id2 = runner1.id, runner2.id
    finally:
        db.close()

    attacker_headers = {"X-User-Id": str(id2)}
    grant_payload = {"purpose": "MARKETING_EMAIL", "policy_version": "1.0"}

    # Спроба Користувача 2 надати згоду від імені Користувача 1
    resp = client.post(
        f"/api/users/{id1}/consents/grant",
        json=grant_payload,
        headers=attacker_headers,
    )
    assert resp.status_code == 403
    assert "Access forbidden" in resp.json()["detail"]
