"""3-Автоматизована верифікація механізмів стійкості (Resilience Testing)."""
from unittest.mock import patch
import httpx
import pytest

from app.services.weather_client import (
    FALLBACK_WEATHER,
    MAX_RETRIES,
    get_weather_with_resilience,
)


def test_weather_success_without_fallback():
    """Позитивна перевірка:

    при доступності зовнішнього сервісу fallback не активується.
    """
    mock_response_data = {
        "current_weather": {
            "temperature": 16.5,
            "windspeed": 4.2,
            "weathercode": 1,
        }
    }

    # Підміняємо реальний виклик httpx.get фіктивною успішною відповіддю 200 OK
    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=200,
            json=mock_response_data,
            request=httpx.Request("GET", "https://api.test-weather.com"),
        )

        result = get_weather_with_resilience("https://api.test-weather.com")

        # Перевірка результату
        assert result["is_fallback"] is False
        assert result["current_weather"]["temperature"] == 16.5
        # Перевірка: виконано рівно 1 успішний виклик без зайвих повторів
        assert mock_get.call_count == 1


def test_weather_resilience_fallback_on_timeout():
    """Resilience тест:

    при таймауті зовнішньої залежності відпрацьовує ліміт повторів (Retry)
    та повертається контрольований Fallback (Graceful Degradation).
    """
    with patch("httpx.get") as mock_get:
        # Штучно симулюємо відмову (Fault Injection: TimeoutException)
        mock_get.side_effect = httpx.TimeoutException("Connection timed out")

        result = get_weather_with_resilience("https://api.test-weather.com")

        # 1. Перевірка контрольованої деградації (Graceful Degradation)
        assert result["is_fallback"] is True
        assert result["temperature"] == FALLBACK_WEATHER["temperature"]
        assert "note" in result

        # 2. Перевірка захисту від Retry Storm (рівно MAX_RETRIES спроб)
        assert mock_get.call_count == MAX_RETRIES