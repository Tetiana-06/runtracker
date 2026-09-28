"""Клієнт для отримання погодних умов перед генерацією плану тренувань."""
import httpx
import logging
import time


logger = logging.getLogger(__name__)
# неіснуюча для fallback - "https://api.open-meteo.com/v1/invalid_endpoint"
WEATHER_API_URL = "https://api.open-meteo.com/v1/invalid_endpoint"

# Параметри стійкості (Resilience Configuration)
MAX_RETRIES = 2             # Обмеження спроб (захист від Retry Storm)
INITIAL_BACKOFF = 0.2       # Базова пауза 0.2 секунди
TIMEOUT_SECONDS = 1.5       # Допустимий таймаут на один запит

# Безпечні резервні дані за замовчуванням (Fallback)
FALLBACK_WEATHER = {
    "temperature": 18.0,
    "windspeed": 5.0,
    "weathercode": 0,
    "is_fallback": True,
    "note": "Зовнішній погодний сервіс недоступний. Використано оптимальні базові параметри."
}


def get_weather_with_resilience(target_url: str = WEATHER_API_URL) -> dict:
    """Отримання погоди із застосуванням патернів Retry, Backoff та Fallback."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Спроба %d звернення до погодного сервісу...", attempt)
            response = httpx.get(target_url, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200:
                data = response.json()
                data["is_fallback"] = False
                return data
            logger.warning("Зовнішній сервіс повернув HTTP %d", response.status_code)
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.warning("Спроба %d не вдалася: %s", attempt, exc)

        # Exponential backoff перед наступною спробою
        if attempt < MAX_RETRIES:
            sleep_time = INITIAL_BACKOFF * (2 ** (attempt - 1))
            time.sleep(sleep_time)

    # Якщо всі спроби вичерпані — активуємо Fallback (Graceful Degradation)
    logger.error("Усі %d спроби вичерпано. Перехід на аварійний Fallback.", MAX_RETRIES)
    return FALLBACK_WEATHER