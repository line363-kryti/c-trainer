"""Настройки приложения. Берутся из переменных окружения или файла .env."""
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта: backend/app/config.py -> на два уровня выше папки app
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    database_url: str

    # Вход: секрет подписи токена (без него сервер не стартует), срок жизни входа,
    # secure-cookie (true на хостинге с https, false локально на http)
    jwt_secret: str = Field(min_length=32)
    jwt_ttl_hours: int = 24 * 7
    cookie_secure: bool = False

    # Сервис запуска кода: piston (свой, в docker-compose) или judge0 (через RapidAPI)
    runner: Literal["piston", "judge0"] = "piston"
    piston_url: str = "http://piston:2000"

    # Judge0: language_id — номер языка C (список: GET /languages)
    judge0_url: str = "https://judge0-ce.p.rapidapi.com"
    judge0_key: str = ""
    judge0_language_id: int = 50

    content_dir: Path = ROOT_DIR / "content"
    frontend_dir: Path = ROOT_DIR / "frontend"


settings = Settings()
