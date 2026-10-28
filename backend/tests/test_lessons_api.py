import pytest

from app.config import settings
from tests.content_helpers import make_lesson, make_task


@pytest.fixture(autouse=True)
def content(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "content_dir", tmp_path)
    make_lesson(tmp_path, "01-intro", "Введение", order=1)
    make_task(tmp_path, "01-intro", "01-sum", order=1)
    make_task(tmp_path, "01-intro", "02-more", order=2)
    make_lesson(tmp_path, "02-loops", "Циклы", order=2)
    make_task(tmp_path, "02-loops", "01-count")
    make_lesson(tmp_path, "00-demo", "Демо", order=0, hidden=True)
    return tmp_path


@pytest.fixture
def user(client):
    client.post("/api/auth/register", json={"email": "lessons@example.com", "password": "secret123"})
    return client


def solve(client, lesson: str, task: str):
    """Сразу пометить задачу решённой — через поддельный запуск."""
    from app.main import app
    from app.runner.base import RunResult
    from app.runner.deps import get_runner

    class AlwaysRight:
        async def run(self, code, stdin):
            a, b = map(int, stdin.split())
            return RunResult(status="ok", stdout=f"{a + b}\n")

    app.dependency_overrides[get_runner] = lambda: AlwaysRight()
    try:
        assert client.post(f"/api/tasks/{lesson}/{task}/check", json={"code": "x"}).json()["solved"]
    finally:
        app.dependency_overrides.clear()


def test_requires_login(client):
    assert client.get("/api/lessons").status_code == 401
    assert client.get("/api/lessons/01-intro").status_code == 401
    assert client.get("/api/progress").status_code == 401


def test_list_is_ordered_and_hides_hidden(user):
    body = user.get("/api/lessons").json()
    assert [l["slug"] for l in body] == ["01-intro", "02-loops"]
    first = body[0]
    assert first["title"] == "Введение" and first["source"] == "Лекция 1"
    assert first["completed"] is False and first["tasks_total"] == 2 and first["tasks_solved"] == 0


def test_lesson_page(user):
    body = user.get("/api/lessons/01-intro").json()
    assert body["body"] == "Теория урока 01-intro"
    assert [t["slug"] for t in body["tasks"]] == ["01-sum", "02-more"]
    assert all(t["status"] is None for t in body["tasks"])
    assert body["prev"] is None and body["next"]["slug"] == "02-loops"

    last = user.get("/api/lessons/02-loops").json()
    assert last["prev"]["slug"] == "01-intro" and last["next"] is None


def test_hidden_lesson_opens_by_link_without_neighbours(user):
    body = user.get("/api/lessons/00-demo").json()
    assert body["title"] == "Демо" and body["prev"] is None and body["next"] is None


def test_unknown_lesson(user):
    assert user.get("/api/lessons/nope").status_code == 404
    assert user.get("/api/lessons/..").status_code == 404
    assert user.post("/api/lessons/nope/complete").status_code == 404


def test_mark_and_unmark_completed(user):
    assert user.post("/api/lessons/01-intro/complete").status_code == 204
    assert user.post("/api/lessons/01-intro/complete").status_code == 204  # повторно — без ошибки
    assert user.get("/api/lessons/01-intro").json()["completed"] is True
    assert user.get("/api/progress").json()["lessons_completed"] == 1

    assert user.delete("/api/lessons/01-intro/complete").status_code == 204
    assert user.get("/api/lessons/01-intro").json()["completed"] is False


def test_solved_tasks_counted(user):
    solve(user, "01-intro", "01-sum")
    assert user.get("/api/lessons").json()[0]["tasks_solved"] == 1
    statuses = {t["slug"]: t["status"] for t in user.get("/api/lessons/01-intro").json()["tasks"]}
    assert statuses == {"01-sum": "solved", "02-more": None}
    assert user.get("/api/progress").json() == {
        "lessons_total": 2, "lessons_completed": 0, "tasks_total": 3, "tasks_solved": 1,
    }


def test_task_knows_next_task(user):
    assert user.get("/api/tasks/01-intro/01-sum").json()["next_task"] == "02-more"
    assert user.get("/api/tasks/01-intro/02-more").json()["next_task"] is None
