"""Клиент Piston на поддельной сети. Ответы — в формате настоящего Piston (isolate)."""
import asyncio
import json

import httpx
import pytest

from app.runner.base import RunnerError
from app.runner.piston import PistonRunner

OK_COMPILE = {"stdout": "", "stderr": "", "output": "", "code": 0, "signal": None, "status": None}


def run_part(**kw) -> dict:
    base = {"stdout": "", "stderr": "", "output": "", "code": 0, "signal": None, "status": None,
            "message": None, "cpu_time": 3, "wall_time": 15, "memory": 1_200_000}
    return {**base, **kw}


def make_runner(handler) -> PistonRunner:
    return PistonRunner("http://piston.test", transport=httpx.MockTransport(handler))


def run(runner: PistonRunner, code: str = "int main(){}", stdin: str = ""):
    return asyncio.run(runner.run(code, stdin))


def respond(body: dict, status_code: int = 200):
    return lambda request: httpx.Response(status_code, json=body)


def test_ok_sends_code_and_limits():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"compile": OK_COMPILE, "run": run_part(stdout="Привет, 10\n")})

    result = run(make_runner(handler), code="CODE", stdin="5")

    assert result.status == "ok"
    assert result.stdout == "Привет, 10\n"
    assert result.time == 0.003 and result.memory == 1200
    body = seen["body"]
    assert seen["path"] == "/api/v2/execute"
    assert body["language"] == "c" and body["files"] == [{"name": "main.c", "content": "CODE"}]
    assert body["stdin"] == "5"
    assert body["run_cpu_time"] == 2000 and body["run_timeout"] == 5000
    assert body["run_memory_limit"] == 128_000_000


def test_compile_error():
    compile_ = {**OK_COMPILE, "code": 1,
                "output": "main.c.c:1:1: error: expected ';'\nchmod: cannot access 'a.out': No such file or directory\n"}
    result = run(make_runner(respond({"compile": compile_})))
    assert result.status == "compile_error"
    assert result.compile_output == "main.c:1:1: error: expected ';'\n"


def test_warnings_are_kept_when_compiled():
    compile_ = {**OK_COMPILE, "output": "main.c:3: warning: unused variable 'x'"}
    result = run(make_runner(respond({"compile": compile_, "run": run_part(stdout="1")})))
    assert result.status == "ok"
    assert "unused variable" in result.compile_output


@pytest.mark.parametrize("run_fields, status, hint", [
    ({"status": "TO", "signal": "SIGKILL", "code": None}, "time_limit", "лимит времени"),
    ({"status": "SG", "signal": "SIGSEGV", "code": None}, "runtime_error", "SIGSEGV"),
    ({"status": "SG", "signal": "SIGFPE", "code": None}, "runtime_error", "деление на ноль"),
    ({"status": "RE", "code": 3}, "runtime_error", "кодом 3"),
    ({"status": "RE", "code": 139}, "runtime_error", "SIGSEGV"),  # так приходит из bash-обёртки
    ({"status": "RE", "code": 136}, "runtime_error", "деление на ноль"),
    ({"status": "RE", "code": 137}, "runtime_error", "лимит памяти"),
    ({"status": "OL", "signal": "SIGKILL", "code": None}, "runtime_error", "длинный вывод"),
    ({"status": "XX", "code": None}, "internal_error", "песочницы"),
])
def test_run_problems(run_fields, status, hint):
    result = run(make_runner(respond({"compile": OK_COMPILE, "run": run_part(**run_fields)})))
    assert result.status == status
    assert hint in result.message


def test_gcc_not_installed():
    with pytest.raises(RunnerError, match="gcc"):
        run(make_runner(respond({"message": "c-10.2.0 runtime is unknown"}, 400)))


def test_service_down():
    def broken(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(RunnerError, match="piston"):
        run(make_runner(broken))
