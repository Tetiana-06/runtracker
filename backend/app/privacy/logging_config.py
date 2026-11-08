"""Конфігурація централізованого безпечного логування (Privacy by Design Logging).

Реалізує:
- PrivacyLogFilter: фільтр стандартної бібліотеки logging, що перехоплює всі записи до виведення.
- PrivacyLogFormatter: безпечний форматер, що гарантує санітизацію фінального тексту повідомлення.
- setup_privacy_logging: функція налаштування кореневого та прикладного логерів.
- PrivacyLoggingMiddleware: HTTP Middleware для аудиту подій без витоку тіла запитів (request/response body).
"""

import logging
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.privacy.sanitizer import sanitize_text, sanitize_value


class PrivacyLogFilter(logging.Filter):
    """Централізований фільтр журналу для видалення секретів та маскування PII."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Санітизація аргументів форматування (record.args)
        if record.args:
            if isinstance(record.args, dict):
                record.args = sanitize_value(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(sanitize_value(arg) for arg in record.args)
            elif isinstance(record.args, list):
                record.args = [sanitize_value(arg) for arg in record.args]
        else:
            # Якщо аргументів форматування немає, санітизуємо record.msg безпосередньо
            if isinstance(record.msg, str):
                record.msg = sanitize_text(record.msg)
            else:
                record.msg = sanitize_value(record.msg)

        # Санітизація тексту винятку, якщо він вже відформатований
        if record.exc_text:
            record.exc_text = sanitize_text(record.exc_text)

        return True


class PrivacyLogFormatter(logging.Formatter):
    """Форматер журналу, що застосовує санітизацію до фінального рядка логу."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return sanitize_text(formatted)


def setup_privacy_logging(log_level: int = logging.INFO) -> None:
    """Ініціалізує політику безпечного логування для всіх логерів застосунку."""
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("app")

    privacy_filter = PrivacyLogFilter()
    privacy_formatter = PrivacyLogFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger.setLevel(log_level)
    app_logger.setLevel(log_level)

    # Очищуємо існуючі або додаємо фільтр до наявних хендлерів
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(privacy_formatter)
        console_handler.addFilter(privacy_filter)
        root_logger.addHandler(console_handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(privacy_formatter)
            if not any(isinstance(f, PrivacyLogFilter) for f in handler.filters):
                handler.addFilter(privacy_filter)

    if not any(isinstance(f, PrivacyLogFilter) for f in app_logger.filters):
        app_logger.addFilter(privacy_filter)


class PrivacyLoggingMiddleware(BaseHTTPMiddleware):
    """HTTP-проміжне програмне забезпечення (Middleware).
    
    Фіксує метадані HTTP-запитів без збереження PII та паролів із Request Body:
    - Метод, шлях URL, HTTP-статус, тривалість у мс.
    - Безпечний ідентифікатор суб'єкта (Actor ID).
    - Унікальний Correlation ID (збережений у заголовку X-Correlation-ID).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or f"req-{uuid.uuid4().hex[:10]}"
        request.state.correlation_id = correlation_id

        # Визначення безпечного ідентифікатора actor (без витоку токенів чи паролів)
        actor_id = request.headers.get("X-User-Id")
        if not actor_id:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                raw_token = auth_header.split(" ", 1)[1]
                actor_id = f"token-{raw_token[:6]}***"
            else:
                actor_id = "anonymous"

        request.state.actor_id = actor_id
        logger = logging.getLogger("app.http")

        # Логуємо лише метадані початку запиту, БЕЗ PII та тіла запиту
        logger.info(
            "HTTP IN  | Method=%s | Path=%s | Actor=%s | Correlation-ID=%s",
            request.method,
            request.url.path,
            actor_id,
            correlation_id,
        )

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Логуємо безпечний підсумок відповіді
            logger.info(
                "HTTP OUT | Method=%s | Path=%s | Status=%d | Duration=%.2fms | Correlation-ID=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                correlation_id,
            )
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "HTTP ERR | Method=%s | Path=%s | Duration=%.2fms | Error=%s | Correlation-ID=%s",
                request.method,
                request.url.path,
                duration_ms,
                exc,
                correlation_id,
            )
            raise
