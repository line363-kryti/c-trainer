"""Пароли и токены.

Пароль храним только как хэш argon2: из хэша пароль не восстановить,
а проверка — это повторное хэширование введённого пароля и сравнение.
Токен входа — JWT: в нём id пользователя и срок действия, подписанные секретом сервера.
Подделать подпись без JWT_SECRET нельзя.
"""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

ALGORITHM = "HS256"

_hasher = PasswordHasher()

# Хэш-пустышка: при входе с несуществующим email всё равно проверяем пароль,
# чтобы по времени ответа нельзя было понять, зарегистрирован ли такой email.
DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=settings.jwt_ttl_hours)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Возвращает id пользователя или None, если токен подделан, испорчен или истёк."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
