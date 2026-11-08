"""Модуль централізованого санітизування та маскування даних (GDPR Secure Logging).

Забезпечує:
- Часткове маскування PII (email, номери телефонів) для збереження діагностичної цінності.
- Повне редагування секретів ([REDACTED] для паролів, токенів, API-ключів, auth-заголовків).
- Рекурсивну обробку довільних структур даних: звичайний текст, JSON/dict, списки, DTO/Pydantic, винятки.
"""

import re
from typing import Any

# Шаблони для пошуку PII та секретів у довільних текстових рядках.
# Lookbehind запобігає повторному зіставленню вже замаскованих фрагментів з зірочками (*).
RE_EMAIL = re.compile(r"(?<![a-zA-Z0-9*_.+-])([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b")
RE_PHONE = re.compile(r"(?<![0-9*])(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3}[-.\s]?\d{2,4}\b")
RE_SECRET_KV = re.compile(
    r"""(?i)\b(password|password_hash|passwd|secret|token|api_key|apikey|access_token|refresh_token|auth|session_secret)\b\s*[:=]\s*['"]?([^\s,'"]+)['"]?"""
)
RE_BEARER = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/]+=*)")

# Ключі словників, які повинні повністю замінюватися на [REDACTED]
SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "passwd",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "secret",
    "session_secret",
    "authorization",
    "auth",
    "private_key",
    "credit_card",
    "cvv",
}


def mask_email(email: str) -> str:
    """Частково маскує адресу електронної пошти.
    
    Приклад:
    - 'alice.smith@example.com' -> 'a***h@example.com'
    - 'me@domain.com' -> 'm***@domain.com'
    - 'a@domain.com' -> 'a***@domain.com'
    """
    if not email or "@" not in email:
        return email

    # Запобігання повторному маскуванню вже замаскованих адрес
    if "*" in email:
        return email

    parts = email.split("@", 1)
    user_part = parts[0]
    domain_part = parts[1]

    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = f"{user_part[0]}***{user_part[-1]}"

    return f"{masked_user}@{domain_part}"


def mask_phone(phone: str) -> str:
    """Частково маскує номер телефону для діагностики, зберігаючи префікс і останні цифри.
    
    Приклад:
    - '+380501234567' -> '+380***4567'
    - '0501234567' -> '050***4567'
    """
    if "*" in phone:
        return phone

    clean_digits = re.sub(r"[^\d+]", "", phone)
    if len(clean_digits) < 7:
        return "***"

    if clean_digits.startswith("+"):
        prefix = clean_digits[:4]
        suffix = clean_digits[-4:]
    else:
        prefix = clean_digits[:3]
        suffix = clean_digits[-4:]

    return f"{prefix}***{suffix}"


def sanitize_text(text: str) -> str:
    """Санітизує довільний текстовий рядок: маскує email, телефони та замінює секрети на [REDACTED]."""
    if not isinstance(text, str):
        text = str(text)

    # 1. Повне редагування секретних пар ключ-значення (password=..., token=...)
    text = RE_SECRET_KV.sub(r"\1=[REDACTED]", text)

    # 2. Повне редагування Bearer токенів
    text = RE_BEARER.sub("Bearer [REDACTED]", text)

    # 3. Часткове маскування email
    def _replace_email(match: re.Match) -> str:
        return mask_email(match.group(0))

    text = RE_EMAIL.sub(_replace_email, text)

    # 4. Часткове маскування номерів телефонів (якщо довжина цифр >= 9)
    def _replace_phone(match: re.Match) -> str:
        val = match.group(0).strip()
        if "*" in val:
            return val
        digits_count = len(re.sub(r"\D", "", val))
        if digits_count >= 9:
            return mask_phone(val)
        return val

    text = RE_PHONE.sub(_replace_phone, text)

    return text


def _sanitize_iterable(val: Any) -> Any:
    sanitized_items = [sanitize_value(item) for item in val]
    if isinstance(val, set):
        return set(sanitized_items)
    return type(val)(sanitized_items)


def _to_pydantic_dict(val: Any) -> Any:
    if hasattr(val, "model_dump"):
        return val.model_dump()
    if hasattr(val, "dict") and callable(getattr(val, "dict")):
        return val.dict()
    return None


def sanitize_value(val: Any) -> Any:
    """Рекурсивно санітизує об'єкт будь-якого типу: dict, list, Pydantic, Exception, str тощо."""
    if val is None:
        return None

    # Обробка Pydantic DTO
    model_dict = _to_pydantic_dict(val)
    if model_dict is not None:
        return sanitize_dict(model_dict)

    # Обробка винятків
    if isinstance(val, BaseException):
        return sanitize_text(str(val))

    # Словники
    if isinstance(val, dict):
        return sanitize_dict(val)

    # Списки та кортежі
    if isinstance(val, (list, tuple, set)):
        return _sanitize_iterable(val)

    # Рядки
    if isinstance(val, str):
        return sanitize_text(val)

    # Примітивні типи (int, float, bool)
    return val


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Рекурсивно обробляє словник (структурований лог), застосовуючи правила політики безпеки."""
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        key_str = str(key)
        key_lower = key_str.lower()

        # Повне редагування секретів за назвою ключа
        if any(sec in key_lower for sec in SENSITIVE_KEYS):
            sanitized[key_str] = "[REDACTED]"
            continue

        # Маскування полів email
        if "email" in key_lower and isinstance(value, str):
            sanitized[key_str] = mask_email(value)
            continue

        # Маскування полів телефону
        if ("phone" in key_lower or "mobile" in key_lower) and isinstance(value, str):
            sanitized[key_str] = mask_phone(value)
            continue

        # Рекурсивна санітизація інших типів
        sanitized[key_str] = sanitize_value(value)

    return sanitized
