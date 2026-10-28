"""Зависимость FastAPI «текущий пользователь».

Любой метод, которому нужен вход, пишет `user: User = Depends(get_current_user)`.
Если cookie нет или токен плохой — ответ 401, до кода метода дело не доходит.
"""
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db import get_db
from app.models import User

COOKIE_NAME = "access_token"


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(access_token) if access_token else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Нужно войти")
    return user
