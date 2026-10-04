"""
Модуль безпечної конфігурації сервісу трекера (Safe Configuration Loader).

Лабораторна робота №3: Завдання 3 (Secrets Leak Prevention).

Призначення:
Забезпечення безпечного управління конфігураційними параметрами та секретами додатку
відповідно до методології Twelve-Factor App (розділ III: Config - зберігання конфігурації
в середовищі оточення).

Ключові заходи безпеки:
1. Повна відсутність хардкоджених секретів (No hardcoded secrets) у кодовій базі.
2. Зчитування ключів доступу, токенів та паролів виключно через змінні середовища
   (Environment Variables) або локальний файл .env (який додано до .gitignore).
3. Валідація наявності обов'язкових ключів під час ініціалізації сервісу.
"""

import os
from typing import Optional


class TrackerConfig:
    """
    Клас управління конфігураційними даними трекера без ризику витоку секретів у Git.
    """

    def __init__(self):
        # Зчитування ключа API трекера зі змінної оточення RUNTRACKER_API_KEY
        self.api_key: Optional[str] = os.environ.get("RUNTRACKER_API_KEY")

        # Режим роботи додатку (development, staging, production)
        self.environment: str = os.environ.get("RUNTRACKER_ENV", "development")

        # Рівень журналювання
        self.log_level: str = os.environ.get("RUNTRACKER_LOG_LEVEL", "INFO")

    def get_api_key(self) -> str:
        """
        Повертає валідований API-ключ або генерує помилку у разі його відсутності.
        """
        if not self.api_key:
            raise ValueError(
                "Критична помилка конфігурації: Змінна середовища RUNTRACKER_API_KEY не задана!\n"
                "Створіть локальний файл .env на основі .env.example та встановіть ключ."
            )
        return self.api_key

    def is_production(self) -> bool:
        """Перевірка, чи запущено сервіс у бойовому середовищі."""
        return self.environment.lower() == "production"


# Глобальний екземпляр конфігурації за замовчуванням
tracker_config = TrackerConfig()
