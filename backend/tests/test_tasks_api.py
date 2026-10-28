"""API задач с поддельным запускателем.

FakeRunner «выполняет» код по ключевому слову в нём:
SUM — правильная сумма, WRONG — сумма + 1, BROKEN — ошибка компиляции, CRASH — падение.
"""
import pytest
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import Submission, TaskProgress
from app.runner.base import RunResult
from app.runner.deps import get_runner
from tests.content_helpers import TEMPLATE, make_task

TASK = "/api/tasks/01-intro/01-sum"


class FakeRunner:
    def __init__(self):
        self.calls = 0

    async def run(self, code: str, stdin: str) -> RunResult:
        self.calls += 1
        if "BROKEN" in code:
            return RunResult(status="compile_error", compile_output="main.c:1: error: expected ';'")
        if "CRASH" in code:
            return RunResult(status="runtime_error", message="SIGSEGV")
        a, b = map(int, stdin.split())
        answer = a + b + (1 if "WRONG" in code else 0)
        return RunResult(status="ok", stdout=f"{answer}\n", time=0.01, memory=900)


@pytest.fixture(autouse=True)
def content(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "content_dir", tmp_path)
    make_task(tmp_path)
    return tmp_path


@pytest.fixture
def fake_runner():
    runner = FakeRunner()
    app.dependency_overrides[get_runner] = lambda: runner
    yield runner
    app.dependency_overrides.clear()


@pytest.fixture
def user(client):
    client.post("/api/auth/register", json={"email": "tasks@example.com", "password": "secret123"})
    return client


def progress():
    with SessionLocal() as db:
        return db.scalar(select(TaskProgress))


def submissions():
    with SessionLocal() as db:
        return list(db.scalars(select(Submission)))


def test_requires_login(client, fake_runner):
    assert client.get(TASK).status_code == 401
    assert client.post(f"{TASK}/check", json={"code": "SUM"}).status_code == 401


def test_get_new_task(user):
    body = user.get(TASK).json()
    assert body["title"] == "Задача 01-sum" and body["lesson_title"] == "Введение"
    assert body["code"] == TEMPLATE  # ещё ничего не сохраняли — отдаём заготовку
    assert body["status"] is None and body["attempts"] == 0
    assert body["has_hint"] and body["has_solution"] and body["tests_count"] == 3
    assert "solution" not in body and "tests" not in body  # эталон и тесты не утекают в условие


def test_unknown_and_malicious_task(user):
    assert user.get("/api/tasks/01-intro/nope").status_code == 404
    assert user.get("/api/tasks/01-intro/..%2F..%2Fetc").status_code == 404


def test_save_code(user):
    assert user.put(f"{TASK}/code", json={"code": "int x;"}).status_code == 204
    assert user.get(TASK).json()["code"] == "int x;"
    assert progress().status == "in_progress"


def test_run_saves_code(user, fake_runner):
    r = user.post(f"{TASK}/run", json={"code": "SUM", "stdin": "4 5"})
    assert r.status_code == 200 and r.json()["stdout"] == "9\n"
    assert progress().last_code == "SUM"


def test_check_all_passed_marks_solved(user, fake_runner):
    r = user.post(f"{TASK}/check", json={"code": "SUM"}).json()
    assert r["solved"] and r["passed"] == r["total"] == 3
    assert all(t["passed"] for t in r["results"])
    assert [t["index"] for t in r["results"]] == [1, 2, 3]

    p = progress()
    assert p.status == "solved" and p.solved_at is not None and p.attempts == 1
    assert [(s.passed, s.total) for s in submissions()] == [(3, 3)]


def test_check_wrong_answer_shows_diff(user, fake_runner):
    r = user.post(f"{TASK}/check", json={"code": "WRONG"}).json()
    assert not r["solved"] and r["passed"] == 0
    first = r["results"][0]
    assert first["status"] == "ok" and not first["passed"]
    assert first["diff"] == {"line": 1, "expected": "5", "got": "6"}
    assert first["input"] == "2 3\n" and first["expected"] == "5\n" and first["got"] == "6\n"
    assert progress().status == "in_progress"


def test_check_compile_error_runs_only_once(user, fake_runner):
    r = user.post(f"{TASK}/check", json={"code": "BROKEN"}).json()
    assert r["compile_error"] == "main.c:1: error: expected ';'"
    assert r["results"] == [] and r["passed"] == 0
    assert fake_runner.calls == 1  # остальные тесты не гоняли
    assert progress().attempts == 1


def test_check_runtime_error(user, fake_runner):
    r = user.post(f"{TASK}/check", json={"code": "CRASH"}).json()
    assert r["results"][0]["status"] == "runtime_error" and r["results"][0]["message"] == "SIGSEGV"
    assert r["results"][0]["diff"] is None


def test_solved_stays_solved_after_wrong_attempt(user, fake_runner):
    user.post(f"{TASK}/check", json={"code": "SUM"})
    user.post(f"{TASK}/check", json={"code": "WRONG"})
    p = progress()
    assert p.status == "solved" and p.attempts == 2 and p.last_code == "WRONG"
    assert user.get(TASK).json()["status"] == "solved"


def test_check_rate_limit(user, fake_runner):
    for _ in range(5):
        assert user.post(f"{TASK}/check", json={"code": "SUM"}).status_code == 200
    assert user.post(f"{TASK}/check", json={"code": "SUM"}).status_code == 429


def test_hint_and_solution(user):
    assert user.get(f"{TASK}/hint").json() == {"hint": "Сложи числа"}
    assert user.get(f"{TASK}/solution").json() == {"code": "SUM"}


def test_no_hint_no_solution(user, content):
    make_task(content, slug="02-bare", hint="", solution=None)
    assert user.get("/api/tasks/01-intro/02-bare/hint").status_code == 404
    assert user.get("/api/tasks/01-intro/02-bare/solution").status_code == 404
    body = user.get("/api/tasks/01-intro/02-bare").json()
    assert not body["has_hint"] and not body["has_solution"]


def test_progress_is_per_user(client, fake_runner):
    client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret123"})
    client.put(f"{TASK}/code", json={"code": "MINE"})
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"email": "b@example.com", "password": "secret123"})
    assert client.get(TASK).json()["code"] == TEMPLATE
