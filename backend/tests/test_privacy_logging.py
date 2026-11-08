"""Автоматизовані тести для Завдання 1: Secure Logging та PII Masking.

Перевіряють:
- Часткове маскування email (alice.smith@example.com -> a***h@example.com).
- Часткове маскування телефонів (+380501234567 -> +380***4567).
- Повне видалення/редагування секретів (паролі, Bearer токени, API-ключі -> [REDACTED]).
- Санітизацію структурованих JSON/dict об'єктів.
- Обробку вкладених DTO та повідомлень про винятки (Exception message).
- Відсутність відкритих sensitive-значень у вихідному журналі.
"""

import io
import logging
from pydantic import BaseModel

from app.privacy.logging_config import PrivacyLogFilter, PrivacyLogFormatter
from app.privacy.sanitizer import (
    mask_email,
    mask_phone,
    sanitize_dict,
    sanitize_text,
    sanitize_value,
)


class UserProfileDTO(BaseModel):
    """Тестовий вкладений DTO."""
    user_email: str
    contact_phone: str
    user_password: str
    auth_token: str


def test_unit_mask_email():
    """Тест маскування адрес електронної пошти."""
    assert mask_email("alice.smith@example.com") == "a***h@example.com"
    assert mask_email("john@runtracker.ua") == "j***n@runtracker.ua"
    assert mask_email("me@domain.org") == "m***@domain.org"
    assert mask_email("a@b.com") == "a***@b.com"


def test_unit_mask_phone():
    """Тест часткового маскування номерів телефонів."""
    assert mask_phone("+380501234567") == "+380***4567"
    assert mask_phone("0501234567") == "050***4567"
    assert mask_phone("+12025550199") == "+120***0199"


def test_unit_sanitize_text():
    """Тест санітизації тексту з різними комбінаціями PII та секретів."""
    raw = (
        "Користувач ivan.runner@gmail.com з телефоном +380671112233 "
        "виконав вхід: password='SecretPass123!' та Bearer eyJhbGciOiJIUzI1NiIsInR5cCI..."
    )
    sanitized = sanitize_text(raw)

    assert "ivan.runner@gmail.com" not in sanitized
    assert "i***r@gmail.com" in sanitized

    assert "+380671112233" not in sanitized
    assert "+380***2233" in sanitized

    assert "SecretPass123!" not in sanitized
    assert "password=[REDACTED]" in sanitized

    assert "eyJhbGciOiJIUzI1NiIsInR5cCI" not in sanitized
    assert "Bearer [REDACTED]" in sanitized


def test_unit_sanitize_dict_and_nested_dto():
    """Тест санітизації структурованих словників та вкладених моделей."""
    payload = {
        "user_id": 42,
        "email": "petro.shevchenko@sports.ua",
        "phone": "+380937778899",
        "password": "MegaSuperSecretPassword!",
        "api_key": "test_dummy_key_value",
        "nested_profile": {
            "backup_email": "petro.backup@cloud.com",
            "token": "secret_refresh_token_xyz",
        },
    }

    sanitized = sanitize_dict(payload)

    # Перевірка email
    assert sanitized["email"] == "p***o@sports.ua"
    assert sanitized["nested_profile"]["backup_email"] == "p***p@cloud.com"

    # Перевірка телефону
    assert sanitized["phone"] == "+380***8899"

    # Перевірка секретів
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested_profile"]["token"] == "[REDACTED]"


def test_logger_filter_and_formatter_output():
    """Позитивний тест перехоплення виводу логера."""
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(PrivacyLogFormatter("%(levelname)s: %(message)s"))
    handler.addFilter(PrivacyLogFilter())

    test_logger = logging.getLogger("test.privacy.logger")
    test_logger.setLevel(logging.INFO)
    test_logger.handlers = [handler]
    test_logger.propagate = False

    raw_email = "victim.runner@secure-run.ua"
    raw_phone = "+380509998877"
    raw_secret = "VeryDangerousPassword!@#"
    raw_token = "secret-token-abcdef12345"

    test_logger.info(
        "Login event: user=%s, phone=%s, password=%s, token=%s",
        raw_email,
        raw_phone,
        raw_secret,
        raw_token,
    )

    log_output = log_stream.getvalue()

    # Жодного відкритого sensitive-значення у тексті журналу
    assert raw_email not in log_output, "Original email leaked into log!"
    assert raw_phone not in log_output, "Original phone leaked into log!"
    assert raw_secret not in log_output, "Original password leaked into log!"
    assert raw_token not in log_output, "Original token leaked into log!"

    # Підтвердження наявності маскованих та нейтральних значень
    assert "v***r@secure-run.ua" in log_output
    assert "+380***8877" in log_output
    assert "[REDACTED]" in log_output


def test_negative_scenario_nested_dto_and_exception_message():
    """Негативний сценарій: передача PII через вкладений DTO та повідомлення винятку.
    
    Тест повинен зазнати FAIL, якщо хоча б одне відкрите значення потрапить до логу.
    """
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(PrivacyLogFormatter("%(levelname)s: %(message)s"))
    handler.addFilter(PrivacyLogFilter())

    test_logger = logging.getLogger("test.privacy.negative")
    test_logger.setLevel(logging.INFO)
    test_logger.handlers = [handler]
    test_logger.propagate = False

    dto = UserProfileDTO(
        user_email="nested.dto@testdomain.com",
        contact_phone="+380991114455",
        user_password="PasswordInsideNestedDTO!123",
        auth_token="jwt.secret.payload.inside.dto",
    )

    # 1. Логування об'єкта DTO
    test_logger.info("Processing DTO: %s", sanitize_value(dto))

    # 2. Логування винятку, що містить чутливі дані у повідомленні
    try:
        raise ValueError(
            "Authentication failed for user admin.error@runtracker.ua with password=FatalSecret999!"
        )
    except ValueError as exc:
        test_logger.error("Caught exception: %s", exc)

    log_output = log_stream.getvalue()

    # Контрольна перевірка відсутності всіх оригінальних sensitive-значень
    sensitive_values = [
        "nested.dto@testdomain.com",
        "+380991114455",
        "PasswordInsideNestedDTO!123",
        "jwt.secret.payload.inside.dto",
        "admin.error@runtracker.ua",
        "FatalSecret999!",
    ]

    for val in sensitive_values:
        assert val not in log_output, f"CRITICAL LEAK: Sensitive value '{val}' was found in log output!"

    # Перевірка наявності маскованих та відредагованих еквівалентів
    assert "n***o@testdomain.com" in log_output
    assert "+380***4455" in log_output
    assert "a***r@runtracker.ua" in log_output
    assert "[REDACTED]" in log_output
