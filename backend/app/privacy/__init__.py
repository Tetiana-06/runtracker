"""Модуль Privacy Engineering та реалізації вимог GDPR (Лабораторна робота №4)."""

from app.privacy.logging_config import PrivacyLoggingMiddleware, setup_privacy_logging
from app.privacy.policy_gate import ConsentPolicyGate
from app.privacy.sanitizer import mask_email, mask_phone, sanitize_dict, sanitize_text, sanitize_value

__all__ = [
    "PrivacyLoggingMiddleware",
    "setup_privacy_logging",
    "ConsentPolicyGate",
    "mask_email",
    "mask_phone",
    "sanitize_text",
    "sanitize_dict",
    "sanitize_value",
]
