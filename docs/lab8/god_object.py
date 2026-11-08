"""Модуль монолітної бізнес-логіки: приклад антипатерну God Object (клас-мутант).

Демонструє:
- Високе зачеплення (CBO > 15): прямі залежності від БД, мережі, моделей, форматування, розрахунків.
- Брак внутрішньої згуртованості (LCOM -> 1 / LCOM4 > 1): непов'язані обов'язки в одному класі.
"""

from datetime import datetime
import json
import logging
import math
import re
from typing import Any

logger = logging.getLogger("app.god_object")


class ExternalLegacyWeatherClient:
    """Сторонній погодний клієнт (до зміни сигнатури)."""
    def fetch_weather(self, url: str) -> dict[str, Any]:
        return {
            "temperature": 18.5,
            "wind_speed": 12.0,
            "humidity": 65,
            "precipitation": 0.0,
        }


class ChangedModernWeatherClient:
    """Оновлений сторонній клієнт: постачальник змінив формат відповіді (temp_c замість temperature)."""
    def fetch_weather(self, url: str) -> dict[str, Any]:
        return {
            "temp_c": 22.0,  # Ключ 'temperature' зник!
            "wind_kmh": 15.0,
        }


class RunnerActivityGodService:
    """КЛАС-МУТАНТ (God Object): бере на себе всі можливі обов'язки системи.
    
    Обов'язки:
    1. Розрахунок спортивних метрик забігу (темп, пульсові зони, VO2 max).
    2. Прямий виклик зовнішніх погодних API та розрахунок коефіцієнта спеки.
    3. Оцінка зносу кросівок та перевірка потреби списання.
    4. Генерація та відправка сповіщень користувачу.
    5. Форматування JSON-звітів та прямий запис у журнал аудиту.
    """

    def __init__(self, weather_url: str = "https://api.open-meteo.com/v1/forecast"):
        self.weather_url = weather_url
        self.weather_client = ExternalLegacyWeatherClient()
        self.last_run_data: dict[str, Any] = {}
        self.calculated_metrics: dict[str, Any] = {}
        self.weather_cache: dict[str, Any] = {}
        self.notification_log: list[str] = []
        self.audit_log: list[dict[str, Any]] = []

    # 1. Спортивні обчислення
    def calculate_run_performance(self, distance_km: float, duration_sec: int, avg_hr: int) -> dict[str, Any]:
        pace_sec_km = duration_sec / distance_km if distance_km > 0 else 0
        pace_min = int(pace_sec_km // 60)
        pace_sec = int(pace_sec_km % 60)

        hr_zone = "aerobic"
        if avg_hr > 170:
            hr_zone = "anaerobic"
        elif avg_hr < 130:
            hr_zone = "recovery"

        speed_kmh = (distance_km / duration_sec) * 3600 if duration_sec > 0 else 0
        vo2_est = 15.0 * (speed_kmh / 3.6)

        self.calculated_metrics = {
            "pace": f"{pace_min}:{pace_sec:02d}",
            "speed_kmh": round(speed_kmh, 2),
            "hr_zone": hr_zone,
            "vo2_est": round(vo2_est, 1),
        }
        return self.calculated_metrics

    # 2. Жорстко зачеплена погодна логіка (епіцентр Shotgun Surgery)
    def fetch_weather_and_adapt_pace(self) -> float:
        # Прямий виклик конкретного методу конкретного класу з конкретним ключем
        data = self.weather_client.fetch_weather(self.weather_url)
        temp = data["temperature"]
        self.weather_cache = data

        adjustment_factor = 1.0
        if temp > 25.0:
            adjustment_factor = 1.08
        elif temp < 0.0:
            adjustment_factor = 1.05
        return adjustment_factor

    # 3. Екіпірування
    def evaluate_shoe_wear(self, shoe_mileage: float, max_mileage: float = 800.0) -> dict[str, Any]:
        wear_pct = (shoe_mileage / max_mileage) * 100 if max_mileage > 0 else 100
        should_retire = wear_pct >= 100.0
        return {
            "wear_pct": round(wear_pct, 1),
            "should_retire": should_retire,
            "status": "REPLACE_URGENT" if should_retire else "OK",
        }

    # 4. Сповіщення
    def notify_runner(self, runner_email: str, message: str) -> bool:
        if "@" not in runner_email:
            return False
        clean_email = runner_email.strip().lower()
        log_entry = f"SENT to {clean_email}: {message}"
        self.notification_log.append(log_entry)
        logger.info(log_entry)
        return True

    # 5. Комплексний бізнес-процес обробки забігу (God-метод)
    def process_full_activity(
        self,
        runner_id: int,
        runner_email: str,
        distance_km: float,
        duration_sec: int,
        avg_hr: int,
        shoe_mileage: float,
    ) -> dict[str, Any]:
        perf = self.calculate_run_performance(distance_km, duration_sec, avg_hr)
        weather_factor = self.fetch_weather_and_adapt_pace()
        shoe_status = self.evaluate_shoe_wear(shoe_mileage)

        adapted_speed = perf["speed_kmh"] / weather_factor
        self.notify_runner(runner_email, f"Забіг {distance_km} км збережено. Темп: {perf['pace']}")

        activity_report = {
            "runner_id": runner_id,
            "performance": perf,
            "weather_factor": weather_factor,
            "adapted_speed": round(adapted_speed, 2),
            "shoe_status": shoe_status,
            "processed_at": datetime.utcnow().isoformat(),
        }
        self.audit_log.append(activity_report)
        return activity_report
