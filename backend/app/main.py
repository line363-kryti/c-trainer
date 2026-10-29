"""Точка входа FastAPI. Все API-методы живут под /api, остальное — страницы сайта."""
import mimetypes

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.limiter import limiter, rate_limit_handler
from app.routers import auth, lessons, run, tasks, labs

app = FastAPI(title="C-тренажёр", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

@app.middleware("http")
async def revalidate_static(request: Request, call_next):
    """Страницы, стили и скрипты: браузер каждый раз сверяется с сервером (304, если файл не менялся).

    Без этого после обновления сайта браузер может показывать старый CSS/JS из кэша.
    """
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


app.include_router(auth.router)
app.include_router(run.router)
app.include_router(tasks.router)
app.include_router(lessons.router)
app.include_router(labs.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Проверка, что сервер жив и база отвечает."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="База данных недоступна")
    return {"status": "ok", "db": "ok"}


# В slim-образе Python нет системной таблицы типов — шрифты отдавались бы как text/plain
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/ttf", ".ttf")  # иконки Monaco

# Фронтенд подключаем последним, чтобы он не перехватывал адреса /api
app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
