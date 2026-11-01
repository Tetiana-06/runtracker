"""Клієнт для отримання погодних умов перед генерацією плану тренувань.

ЛР7: рефакторинг за Чепіним (Immutable Data + Value Objects).
- RetryPolicy     — незмінний об'єкт-значення з параметрами стійкості (спроби, пауза, таймаут).
- WeatherSnapshot — незмінний об'єкт-значення з погодними даними та ознакою fallback.
Метод get_weather_with_resilience більше нічого не перезаписує: Cch 16 -> 6.
"""
import copy
import logging
import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional

import httpx

logger = logging.getLogger(__name__)
# неіснуюча для fallback - "https://api.open-meteo.com/v1/invalid_endpoint"
WEATHER_API_URL = "https://api.open-meteo.com/v1/invalid_endpoint"

# Параметри стійкості (Resilience Configuration)
MAX_RETRIES = 2             # Обмеження спроб (захист від Retry Storm)
INITIAL_BACKOFF = 0.2       # Базова пауза 0.2 секунди
TIMEOUT_SECONDS = 1.5       # Допустимий таймаут на один запит


@dataclass(frozen=True)
class RetryPolicy:
    """Value Object: правила повторних спроб. Після створення змінити не можна."""

    max_retries: int = MAX_RETRIES
    initial_backoff: float = INITIAL_BACKOFF
    timeout_seconds: float = TIMEOUT_SECONDS

    def attempts(self) -> range:
        return range(1, self.max_retries + 1)

    def is_last(self, attempt: int) -> bool:
        return attempt >= self.max_retries

    def backoff(self, attempt: int) -> float:
        """Exponential backoff: 0.2 c, 0.4 c, 0.8 c ..."""
        return self.initial_backoff * (2 ** (attempt - 1))


@dataclass(frozen=True)
class WeatherSnapshot:
    """Value Object: погодні дані тільки для читання + ознака аварійного режиму."""

    payload: Mapping[str, Any]
    is_fallback: bool

    def as_dict(self) -> dict:
        """Кожен виклик повертає НОВУ копію — зміни споживача не торкаються оригіналу."""
        return {**copy.deepcopy(dict(self.payload)), "is_fallback": self.is_fallback}


DEFAULT_POLICY = RetryPolicy()

# Безпечні резервні дані за замовчуванням (Fallback) — словник лише для читання
FALLBACK_WEATHER = MappingProxyType({
    "temperature": 18.0,
    "windspeed": 5.0,
    "weathercode": 0,
    "is_fallback": True,
    "note": "Зовнішній погодний сервіс недоступний. Використано оптимальні базові параметри.",
})
FALLBACK_SNAPSHOT = WeatherSnapshot(payload=FALLBACK_WEATHER, is_fallback=True)


def _fetch_once(target_url: str, attempt: int, policy: RetryPolicy) -> Optional[WeatherSnapshot]:
    """Одна спроба запиту. Успіх -> WeatherSnapshot, невдача -> пауза/лог і None."""
    try:
        logger.info("Спроба %d звернення до погодного сервісу...", attempt)
        response = httpx.get(target_url, timeout=policy.timeout_seconds)
        if response.status_code == 200:
            return WeatherSnapshot(payload=MappingProxyType(response.json()), is_fallback=False)
        logger.warning("Зовнішній сервіс повернув HTTP %d", response.status_code)
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        logger.warning("Спроба %d не вдалася: %s", attempt, exc)

    if policy.is_last(attempt):
        logger.error("Усі %d спроби вичерпано. Перехід на аварійний Fallback.", policy.max_retries)
    else:
        time.sleep(policy.backoff(attempt))
    return None


def get_weather_with_resilience(target_url: str = WEATHER_API_URL,
                                policy: RetryPolicy = DEFAULT_POLICY) -> dict:
    """Отримання погоди із застосуванням патернів Retry, Backoff та Fallback."""
    for attempt in policy.attempts():
        snapshot = _fetch_once(target_url, attempt, policy)
        if snapshot:
            return snapshot.as_dict()
    return FALLBACK_SNAPSHOT.as_dict()
