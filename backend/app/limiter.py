"""Ограничение частоты запросов (slowapi). Счётчики хранятся в памяти процесса.

Лимит вешается на метод декоратором, например `@limiter.limit("10/minute")`.
По умолчанию считаем по IP; для запуска кода — по пользователю (user_key).
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth.deps import COOKIE_NAME
from app.auth.security import decode_access_token

limiter = Limiter(key_func=get_remote_address)


def user_key(request: Request) -> str:
    """Ключ лимита «по пользователю»: id из токена, а если входа нет — IP."""
    token = request.cookies.get(COOKIE_NAME)
    user_id = decode_access_token(token) if token else None
    return f"user:{user_id}" if user_id is not None else get_remote_address(request)


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Слишком много попыток, подожди минуту"})
