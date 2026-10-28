"""Общие настройки тестов.

Тесты работают с отдельной базой <имя>_test, чтобы не трогать данные разработки.
Адрес подменяется ДО импорта app, потому что app.db создаёт подключение при импорте.
"""
import os

from sqlalchemy.engine import make_url

_dev_url = make_url(os.environ["DATABASE_URL"])
_test_url = _dev_url.set(database=f"{_dev_url.database}_test")
os.environ["DATABASE_URL"] = _test_url.render_as_string(hide_password=False)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app.db import engine  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


def _create_test_database() -> None:
    admin = create_engine(_dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": _test_url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{_test_url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    _create_test_database()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_state():
    """После каждого теста — пустые таблицы и сброшенные счётчики лимитов."""
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    limiter.reset()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
