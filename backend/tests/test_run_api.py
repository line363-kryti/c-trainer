"""Метод POST /api/run с поддельным запускателем вместо Judge0."""
import pytest

from app.main import app
from app.routers.run import MAX_CODE_CHARS, MAX_STDIN_CHARS
from app.runner.base import RunnerError, RunnerQuotaError, RunResult
from app.runner.deps import get_runner

RUN = "/api/run"
CODE = '#include <stdio.h>\nint main(void) { int a; scanf("%d", &a); printf("%d\\n", a * 2); }'


class FakeRunner:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = []

    async def run(self, code: str, stdin: str) -> RunResult:
        self.calls.append((code, stdin))
        if self.error:
            raise self.error
        return RunResult(status="ok", stdout=str(int(stdin) * 2) + "\n", time=0.01, memory=900)


@pytest.fixture
def fake_runner():
    runner = FakeRunner()
    app.dependency_overrides[get_runner] = lambda: runner
    yield runner
    app.dependency_overrides.clear()


@pytest.fixture
def logged_in(client):
    client.post("/api/auth/register", json={"email": "runner@example.com", "password": "secret123"})
    return client


def test_requires_login(client, fake_runner):
    assert client.post(RUN, json={"code": CODE}).status_code == 401
    assert fake_runner.calls == []


def test_run_ok(logged_in, fake_runner):
    r = logged_in.post(RUN, json={"code": CODE, "stdin": "21"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["stdout"] == "42\n"
    assert fake_runner.calls == [(CODE, "21")]


def test_validation(logged_in, fake_runner):
    assert logged_in.post(RUN, json={"code": ""}).status_code == 422
    assert logged_in.post(RUN, json={"code": "x" * (MAX_CODE_CHARS + 1)}).status_code == 422
    assert logged_in.post(RUN, json={"code": CODE, "stdin": "1" * (MAX_STDIN_CHARS + 1)}).status_code == 422
    assert fake_runner.calls == []


def test_service_errors(logged_in, fake_runner):
    fake_runner.error = RunnerQuotaError("Закончился лимит")
    assert logged_in.post(RUN, json={"code": CODE, "stdin": "1"}).status_code == 429
    fake_runner.error = RunnerError("Недоступен")
    assert logged_in.post(RUN, json={"code": CODE, "stdin": "1"}).status_code == 503


def test_rate_limit_per_user(logged_in, fake_runner):
    for _ in range(10):
        assert logged_in.post(RUN, json={"code": CODE, "stdin": "1"}).status_code == 200
    assert logged_in.post(RUN, json={"code": CODE, "stdin": "1"}).status_code == 429
    assert len(fake_runner.calls) == 10


def test_judge0_without_key_gives_clear_error(logged_in, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "runner", "judge0")
    monkeypatch.setattr(settings, "judge0_key", "")
    r = logged_in.post(RUN, json={"code": CODE})
    assert r.status_code == 503
    assert "JUDGE0_KEY" in r.json()["detail"]
