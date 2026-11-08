"""Тести для Завдання 3: аудит успадкування за Лоренцом-Кідом та демонстрація спадкового краш-тесту."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from docs.lab8.inheritance_hierarchy import (
    AdvancedRunnerDashboardExporter,
    BaseReportExporter,
    HtmlReportExporter,
)


def test_base_report_exporter_direct():
    """Прямий виклик базового експортера з новим аргументом context."""
    exporter = BaseReportExporter()
    out = exporter.build_export("Weekly Digest", {"km": 42.0})
    assert "WEEKLY DIGEST" in out
    assert "km: 42.0" in out


def test_inheritance_fragility_crash_fail():
    """FAIL: точкова зміна в BaseReportExporter ламає весь ланцюжок нащадків."""
    dashboard = AdvancedRunnerDashboardExporter()

    # Спроба виклику призводить до TypeError через невідповідність аргументів у ланцюжку super()
    with pytest.raises(TypeError) as exc_info:
        dashboard.build_dashboard("Олександр", {"distance": 21.1})

    assert "missing 1 required positional argument: 'context'" in str(exc_info.value)
