"""  4 - Шлюз перевірки згод (Consent Policy Gate - GDPR Article 7).

Забезпечує:
- Централізовану перевірку актуальності та наявності згоди суб'єкта перед виконанням залежної операції.
- Негайне застосування відкликання згоди (Zero Delay Enforcement).
- Ізоляцію цілей обробки (згода на маркетинг не відкриває аналітику).
- Відсутність побічних ефектів при стані DENY.
"""

import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import UserConsent

logger = logging.getLogger("app.privacy.policy_gate")


class ConsentPolicyGate:
    """Компонент перевірки згод перед виконанням залежних бізнес-операцій."""

    @staticmethod
    def is_consent_active(
        db: Session,
        runner_id: int,
        purpose: str,
        required_policy_version: str | None = None,
    ) -> bool:
        """Перевіряє, чи є актуальна дійсна згода для даного користувача і конкретної мети."""
        consent = (
            db.query(UserConsent)
            .filter(
                UserConsent.runner_id == runner_id,
                UserConsent.purpose == purpose,
            )
            .first()
        )

        if not consent:
            return False

        if not consent.is_granted:
            return False

        if required_policy_version and consent.policy_version != required_policy_version:
            return False

        return True

    @classmethod
    def enforce(
        cls,
        db: Session,
        runner_id: int,
        purpose: str,
        required_policy_version: str | None = None,
    ) -> None:
        """Блокує виконання операції (DENY), якщо згода відсутня або була відкликана.
        
        Викидає HTTPException(403 Forbidden) з чітким описом причини блокування.
        """
        active = cls.is_consent_active(db, runner_id, purpose, required_policy_version)
        if not active:
            logger.warning(
                "Consent Policy Gate DENY: Subject=%d | Purpose=%s | Reason=No active consent",
                runner_id,
                purpose,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation denied by Consent Policy Gate: no active consent for purpose '{purpose}'",
            )

        logger.info(
            "Consent Policy Gate ALLOW: Subject=%d | Purpose=%s",
            runner_id,
            purpose,
        )
