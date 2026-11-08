"""Інтеграційні тести для Завдання 2: Personal Data Export (GDPR Article 15).

Перевіряють:
- Авторизований експорт структурованих персональних даних (Right of Access).
- Повноту агрегації з усіх джерел: профіль, налаштування, забіги, екіпірування, плани, згоди.
- Дотримання принципу мінімізації даних (Data Minimization): повна відсутність password_hash та внутрішніх секретів.
- Передбачуваність схеми для порожніх категорій ([] замість null/помилки).
- Контроль доступу та захист від IDOR (403 Forbidden при спробі доступу до чужого профілю).
- Коректну обробку неіснуючого subject_id (404 Not Found).
- Безпеку логування (відсутність дампу експортованих PII у журналах).
"""

import io
import logging
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Run, Runner, Shoe, TrainingPlan, UserConsent
from app.privacy.logging_config import PrivacyLogFilter, PrivacyLogFormatter

client = TestClient(app)


def setup_function():
    """Створює чисті таблиці перед кожним тестом."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_sample_runner_with_relations(db: Session) -> Runner:
    """Допоміжна функція створення тестового суб'єкта з пов'язаними сутностями."""
    runner = Runner(
        name="Тарас Шевченко",
        email="taras.runner@domain.ua",
        phone="+380671234567",
        password_hash="pbkdf2_sha256$super_secure_hash_value_never_leak",
        age=35,
        resting_hr=58,
        level="intermediate",
        weekly_volume_km=45.0,
        has_injury_history=0,
        preferences='{"theme": "dark", "preferred_unit": "km", "notifications": true}',
    )
    db.add(runner)
    db.commit()
    db.refresh(runner)

    # Додавання екіпірування
    shoe = Shoe(
        runner_id=runner.id,
        model="Nike Pegasus 40",
        category="daily",
        purchased_on=date(2026, 1, 15),
        mileage_km=150.5,
    )
    db.add(shoe)
    db.commit()
    db.refresh(shoe)

    # Додавання тренувань
    run1 = Run(
        runner_id=runner.id,
        shoe_id=shoe.id,
        run_date=date(2026, 3, 1),
        distance_km=10.0,
        duration_sec=3000,
        avg_hr=145,
        workout_type="easy",
        notes="Чудовий забіг парком біля озера",
    )
    db.add(run1)

    # Додавання тренувального плану
    plan = TrainingPlan(
        runner_id=runner.id,
        target_distance_km=21.1,
        weeks=12,
        payload='{"weeks": [{"week": 1, "km": 30}]}',
    )
    db.add(plan)

    # Додавання згоди
    consent = UserConsent(
        runner_id=runner.id,
        purpose="MARKETING_EMAIL",
        is_granted=True,
        policy_version="1.0",
        source="registration_form",
    )
    db.add(consent)

    db.commit()
    db.refresh(runner)
    return runner


def test_positive_personal_data_export_completeness_and_minimization():
    """Позитивний тест: експорт власних даних із повною агрегацією та мінімізацією."""
    db = SessionLocal()
    try:
        runner = create_sample_runner_with_relations(db)
        runner_id = runner.id
    finally:
        db.close()

    # Запит від імені самого користувача (автентифікований principal == subject)
    headers = {"X-User-Id": str(runner_id)}
    response = client.get(f"/api/users/{runner_id}/personal-data", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Перевірка метаданих формування
    meta = data["export_metadata"]
    assert meta["subject_id"] == runner_id
    assert meta["schema_version"] == "1.0"
    assert "data_controller" in meta
    assert "legal_basis" in meta
    assert "generated_at" in meta
    assert meta["export_id"].startswith(f"exp-{runner_id}-")

    # 2. Перевірка наявності всіх обов'язкових розділів
    assert set(data["categories"]) == {
        "profile",
        "settings",
        "runs",
        "shoes",
        "training_plans",
        "consents",
    }

    # 3. Перевірка розділу profile
    profile = data["profile"]
    assert profile["id"] == runner_id
    assert profile["name"] == "Тарас Шевченко"
    assert profile["email"] == "taras.runner@domain.ua"
    assert profile["phone"] == "+380671234567"
    assert profile["age"] == 35

    # КРИТИЧНО: Принцип мінімізації (Data Minimization)
    assert "password_hash" not in profile, "Security Leak: password_hash returned in export profile!"
    assert "password" not in profile, "Security Leak: password returned in export profile!"
    # Перевірка у всьому тексті відповіді
    assert "super_secure_hash_value_never_leak" not in response.text

    # 4. Перевірка налаштувань
    assert data["settings"]["theme"] == "dark"
    assert data["settings"]["preferred_unit"] == "km"

    # 5. Перевірка пов'язаних сутностей
    assert len(data["runs"]) == 1
    assert data["runs"][0]["distance_km"] == 10.0
    assert data["runs"][0]["notes"] == "Чудовий забіг парком біля озера"

    assert len(data["shoes"]) == 1
    assert data["shoes"][0]["model"] == "Nike Pegasus 40"

    assert len(data["training_plans"]) == 1
    assert data["training_plans"][0]["target_distance_km"] == 21.1

    assert len(data["consents"]) == 1
    assert data["consents"][0]["purpose"] == "MARKETING_EMAIL"
    assert data["consents"][0]["is_granted"] is True


def test_export_empty_categories_predictability():
    """Перевірка передбачуваності структури для користувача без активностей ([] замість 500 чи null)."""
    db = SessionLocal()
    try:
        new_runner = Runner(name="Новий Бігун", email="newbie@run.ua")
        db.add(new_runner)
        db.commit()
        db.refresh(new_runner)
        runner_id = new_runner.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer user-{runner_id}"}
    response = client.get(f"/api/runners/{runner_id}/personal-data", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []
    assert data["shoes"] == []
    assert data["training_plans"] == []
    assert data["consents"] == []


def test_negative_authorization_idor_protection():
    """Негативний тест: відмова сторонньому користувачеві (403 Forbidden) без витоку даних."""
    db = SessionLocal()
    try:
        runner1 = Runner(name="Користувач 1", email="user1@domain.ua")
        runner2 = Runner(name="Користувач 2", email="user2@domain.ua")
        db.add_all([runner1, runner2])
        db.commit()
        id1, id2 = runner1.id, runner2.id
    finally:
        db.close()

    # Спроба Користувача 2 запросити дані Користувача 1
    attacker_headers = {"X-User-Id": str(id2)}
    response = client.get(f"/api/users/{id1}/personal-data", headers=attacker_headers)

    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]
    # Перевірка: жодні персональні дані користувача 1 не розкриті у відповіді
    assert "user1@domain.ua" not in response.text


def test_negative_nonexistent_subject():
    """Негативний тест: запит неіснуючого ідентифікатора повертає 404."""
    # Запит від імені admin для перевірки існування суб'єкта
    headers = {"Authorization": "Bearer admin-token"}
    response = client.get("/api/users/999999/personal-data", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_safe_logging_during_export():
    """Перевірка журналювання: операція експорту не створює витоку повного JSON у логи."""
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(PrivacyLogFormatter("%(levelname)s: %(message)s"))
    handler.addFilter(PrivacyLogFilter())

    privacy_logger = logging.getLogger("app.privacy.service")
    privacy_logger.addHandler(handler)
    privacy_logger.setLevel(logging.INFO)

    db = SessionLocal()
    try:
        runner = create_sample_runner_with_relations(db)
        runner_id = runner.id
    finally:
        db.close()

    headers = {"X-User-Id": str(runner_id)}
    response = client.get(f"/api/users/{runner_id}/personal-data", headers=headers)
    assert response.status_code == 200

    log_contents = log_stream.getvalue()

    # Підтвердження збереження факту події, subject_id та відсутності PII
    assert "Event=DATA_EXPORT" in log_contents
    assert f"Subject={runner_id}" in log_contents
    # Підтвердження: персональний email чи телефон НЕ присутні у відкритому вигляді в журналі сервісу
    assert "taras.runner@domain.ua" not in log_contents
    assert "+380671234567" not in log_contents
