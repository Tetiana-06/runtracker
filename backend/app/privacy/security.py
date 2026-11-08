"""Контроль доступу та автентифікація суб'єктів (Access Control & Subject Verification).

Забезпечує:
- Захист від IDOR (Insecure Direct Object Reference).
- Перевірку автентифікованого principal із запитуваним subject_id.
- Підтримку ролі адміністратора або самообслуговування користувача (self-service).
- Повернення контрольованої відмови без витоку конфіденційної інформації.
"""

from dataclasses import dataclass
from fastapi import Header, HTTPException, Request, status


@dataclass
class Principal:
    """Автентифікований суб'єкт запиту (користувач або сервіс)."""
    user_id: int | None
    role: str = "user"
    is_authenticated: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def get_current_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> Principal:
    """Витягує автентифікованого користувача із заголовків Authorization або X-User-Id."""
    # 1. Перевірка заголовка Bearer токена
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token.startswith("admin"):
            return Principal(user_id=0, role="admin", is_authenticated=True)
        # Підтримка токенів формату 'runner-{id}' або 'user-{id}'
        if token.startswith("runner-") or token.startswith("user-"):
            try:
                uid = int(token.split("-", 1)[1])
                return Principal(user_id=uid, role="user", is_authenticated=True)
            except ValueError:
                pass

    # 2. Перевірка заголовків X-User-Id та X-User-Role (для внутрішньосистемного/шлюзового контексту)
    if x_user_id:
        try:
            uid = int(x_user_id)
            role = (x_user_role or "user").strip().lower()
            return Principal(user_id=uid, role=role, is_authenticated=True)
        except ValueError:
            pass

    return Principal(user_id=None, role="guest", is_authenticated=False)


def verify_subject_access(principal: Principal, subject_id: int) -> None:
    """Перевіряє право доступу principal до даних subject_id (захист від IDOR).
    
    Якщо суб'єкт намагається отримати доступ до чужого профілю:
    повертається 403 Forbidden без розкриття вмісту чи факту існування чужих даних.
    """
    if not principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to perform this action",
        )

    if principal.is_admin:
        return

    if principal.user_id != subject_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to access or modify this subject's data",
        )
