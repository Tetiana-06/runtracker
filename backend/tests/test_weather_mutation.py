"""ЛР7, Завдання 2: краш-тест неконтрольованої мутації даних погодного клієнта.

Сценарій: погодний сервіс недоступний, тому клієнт повертає аварійні дані (fallback).
Перший споживач (наприклад, модуль адаптації плану під спеку) «підправляє» отриманий
словник під себе. Якщо клієнт віддає спільний змінюваний об'єкт, то правка
просочується в глобальний FALLBACK і всі наступні запити отримують зіпсовані дані.
"""
from unittest.mock import patch

import httpx

from app.services.weather_client import get_weather_with_resilience

URL = "https://api.test-weather.com"


def _call_with_api_down() -> dict:
    with patch("httpx.get", side_effect=httpx.TimeoutException("down")), patch("time.sleep"):
        return get_weather_with_resilience(URL)


def test_fallback_is_not_corrupted_by_caller():
    first = _call_with_api_down()
    # Споживач №1 змінює отриманий результат під свої потреби
    first["temperature"] = 45.0
    first["is_fallback"] = False

    second = _call_with_api_down()

    # Споживач №2 має отримати чисті аварійні дані, а не «спеку 45°C»
    assert second["temperature"] == 18.0
    assert second["is_fallback"] is True
