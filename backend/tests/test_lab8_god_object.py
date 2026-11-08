"""Тести для Завдання 2: демонстрація антипатерну God Object та Shotgun Surgery."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from docs.lab8.god_object import (
    ChangedModernWeatherClient,
    ExternalLegacyWeatherClient,
    RunnerActivityGodService,
)


def test_baseline_god_service_works_with_legacy_client():
    """Базовий стан: моноліт працює, але має величезне зачеплення CBO."""
    god = RunnerActivityGodService()
    result = god.process_full_activity(
        runner_id=1,
        runner_email="runner@example.com",
        distance_km=10.0,
        duration_sec=3000,
        avg_hr=155,
        shoe_mileage=150.0,
    )

    assert result["performance"]["pace"] == "5:00"
    assert result["weather_factor"] == 1.0
    assert result["shoe_status"]["status"] == "OK"
    assert len(god.notification_log) == 1


def test_shotgun_surgery_god_object_failure():
    """FAIL: точкова зміна стороннього клієнта руйнує God Object через відсутність інтерфейсів."""
    god = RunnerActivityGodService()
    # Підміна на оновлений погодний клієнт (зміна контракту постачальника)
    god.weather_client = ChangedModernWeatherClient()

    # Лавиноподібний збій у моноліті: KeyError 'temperature'
    with pytest.raises(KeyError) as exc_info:
        god.process_full_activity(
            runner_id=1,
            runner_email="runner@example.com",
            distance_km=10.0,
            duration_sec=3000,
            avg_hr=155,
            shoe_mileage=150.0,
        )

    assert "temperature" in str(exc_info.value)
