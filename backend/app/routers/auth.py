"""Регистрация, вход, выход и «кто я».

После регистрации или входа сервер кладёт JWT в httpOnly-cookie:
- httpOnly — JavaScript на странице не может прочитать токен (защита от кражи через XSS);
- SameSite=Lax — браузер не пошлёт cookie с POST-запросом с чужого сайта (защита от CSRF);
- Secure (на хостинге) — cookie уходит только по https.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import COOKIE_NAME, get_current_user
from app.auth.schemas import LoginIn, RegisterIn, UserOut
from app.auth.security import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.config import settings
from app.db import get_db
from app.limiter import limiter
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

WRONG_CREDENTIALS = "Неверный email или пароль"
EMAIL_TAKEN = "Этот email уже зарегистрирован"


def _set_auth_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user_id),
        max_age=settings.jwt_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, response: Response, data: RegisterIn, db: Session = Depends(get_db)) -> User:
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)

    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # два одновременных запроса с одним email
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)

    _set_auth_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
@limiter.limit("10/minute")
def login(request: Request, response: Response, data: LoginIn, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if user is None:
        verify_password(DUMMY_HASH, data.password)  # тратим столько же времени, как с настоящим email
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=WRONG_CREDENTIALS)
    if not verify_password(user.password_hash, data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=WRONG_CREDENTIALS)

    _set_auth_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
