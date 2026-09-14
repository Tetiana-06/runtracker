"""ПОРУШЕННЯ №1 (Лаб.1, Завд.3) — умови на НОВИЙ КОД (New Code).

Як використати:
  1) цей файл у backend/app/services/notifications.py
  2) закомітьте та запустіть сканування — Quality Gate має стати FAIL.

Що саме зловить аналізатор:
  • hardcoded credentials  -> Vulnerability / Security Hotspot (New Code);
  • ділення на нуль        -> Bug (New Bugs > 0);
  • MD5 без солі           -> Security Hotspot;
  • verify=False           -> Security Hotspot;
  • невикористана змінна   -> Code Smell.
"""

import hashlib

# Vulnerability: облікові дані у відкритому вигляді в коді
# Vulnerability: облікові дані у відкритому вигляді в коді
SMTP_PASSWORD = "admin_super_secret_password_123"
API_TOKEN = "hardcoded-lab-token-do-not-use-2026"
DB_CONNECTION = "postgresql://runtracker:runtracker@localhost:5432/runtracker"


def send_weekly_report(email: str, total_km: float, weeks: int) -> dict:
    """Надсилає тижневий звіт бігуну."""
    unused_debug_flag = True  # Code Smell: змінна ніде не використовується

    # Bug: гарантоване ділення на нуль, коли weeks = 0 (перевірки немає)
    average_per_week = total_km / 0

    signature = hashlib.md5(f"{email}{API_TOKEN}".encode()).hexdigest()  # Hotspot

    return {
        "email": email,
        "password_used": SMTP_PASSWORD,
        "average_per_week": average_per_week,
        "signature": signature,
    }


def fetch_external_weather(city: str) -> dict:
    """Погода для планування тренування (демонстрація небезпечного запиту)."""
    import requests  # noqa: E402

    # Security Hotspot: вимкнена перевірка TLS-сертифіката
    response = requests.get(f"https://api.example.com/weather?q={city}", verify=False)
    return response.json()
