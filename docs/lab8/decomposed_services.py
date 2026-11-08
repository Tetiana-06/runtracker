"""Архітектурна декомпозиція God Object (СТАН PASS).

Застосовані техніки:
- Single Responsibility Principle (SRP): 4 окремі вузькоспеціалізовані класи.
- Interface Segregation & Dependency Inversion (DIP): контракти через typing.Protocol.
- Dependency Injection (DI): передача залежностей через конструктор координатора.
"""

from datetime import datetime
from typing import Any, Protocol


class IRunMetricsCalculator(Protocol):
    def calculate_performance(self, distance_km: float, duration_sec: int, avg_hr: int) -> dict[str, Any]:
        ...


class IWeatherProvider(Protocol):
    def get_weather_adaptation_factor(self) -> float:
        ...


class IShoeWearEvaluator(Protocol):
    def evaluate_wear(self, mileage_km: float) -> dict[str, Any]:
        ...


class IRunnerNotifier(Protocol):
    def notify(self, email: str, message: str) -> bool:
        ...


class RunMetricsCalculator:
    """1. Спортивний калькулятор (ізольована відповідальність)."""

    def calculate_performance(self, distance_km: float, duration_sec: int, avg_hr: int) -> dict[str, Any]:
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

        return {
            "pace": f"{pace_min}:{pace_sec:02d}",
            "speed_kmh": round(speed_kmh, 2),
            "hr_zone": hr_zone,
            "vo2_est": round(vo2_est, 1),
        }


class WeatherAdapter:
    """2. Адаптер погодного сервісу: ізолює зміни зовнішнього постачальника."""

    def __init__(self, external_client: Any, target_url: str = "https://api.weather.local"):
        self._client = external_client
        self._url = target_url

    def _extract_temperature(self, data: dict[str, Any]) -> float:
        if "temperature" in data:
            return float(data["temperature"])
        if "temp_c" in data:
            return float(data["temp_c"])
        return 20.0

    def get_weather_adaptation_factor(self) -> float:
        data = self._client.fetch_weather(self._url)
        temp = self._extract_temperature(data)

        if temp > 25.0:
            return 1.08
        if temp < 0.0:
            return 1.05
        return 1.0


class ShoeWearEvaluator:
    """3. Оцінювач зносу екіпірування."""

    def __init__(self, max_mileage: float = 800.0):
        self._max_mileage = max_mileage

    def evaluate_wear(self, mileage_km: float) -> dict[str, Any]:
        wear_pct = (mileage_km / self._max_mileage) * 100 if self._max_mileage > 0 else 100
        should_retire = wear_pct >= 100.0
        return {
            "wear_pct": round(wear_pct, 1),
            "should_retire": should_retire,
            "status": "REPLACE_URGENT" if should_retire else "OK",
        }


class RunnerNotifier:
    """4. Сервіс сповіщень."""

    def __init__(self):
        self.sent_messages: list[str] = []

    def notify(self, email: str, message: str) -> bool:
        if "@" not in email:
            return False
        clean_email = email.strip().lower()
        log_entry = f"NOTIFIED {clean_email}: {message}"
        self.sent_messages.append(log_entry)
        return True


class RunnerActivityCoordinator:
    """Легковажний оркестратор бізнес-процесу (Dependency Inversion)."""

    def __init__(
        self,
        metrics_calculator: IRunMetricsCalculator,
        weather_provider: IWeatherProvider,
        shoe_evaluator: IShoeWearEvaluator,
        notifier: IRunnerNotifier,
    ):
        self._metrics = metrics_calculator
        self._weather = weather_provider
        self._shoe = shoe_evaluator
        self._notifier = notifier

    def process_activity(
        self,
        runner_id: int,
        runner_email: str,
        distance_km: float,
        duration_sec: int,
        avg_hr: int,
        shoe_mileage: float,
    ) -> dict[str, Any]:
        perf = self._metrics.calculate_performance(distance_km, duration_sec, avg_hr)
        weather_factor = self._weather.get_weather_adaptation_factor()
        shoe_status = self._shoe.evaluate_wear(shoe_mileage)

        adapted_speed = perf["speed_kmh"] / weather_factor
        self._notifier.notify(runner_email, f"Забіг {distance_km} км збережено. Темп: {perf['pace']}")

        return {
            "runner_id": runner_id,
            "performance": perf,
            "weather_factor": weather_factor,
            "adapted_speed": round(adapted_speed, 2),
            "shoe_status": shoe_status,
            "processed_at": datetime.utcnow().isoformat(),
        }
