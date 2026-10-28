"""Клиент Judge0 на поддельной сети: настоящий сервис и ключ не нужны."""
import asyncio
import base64
import json

import httpx
import pytest

from app.runner.base import RunnerError, RunnerQuotaError
from app.runner.judge0 import Judge0Runner


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def make_runner(handler) -> Judge0Runner:
    return Judge0Runner(
        "https://judge0.test", "test-key", 50, transport=httpx.MockTransport(handler), poll_interval=0
    )


def run(runner: Judge0Runner, code: str = "int main(){}", stdin: str = ""):
    return asyncio.run(runner.run(code, stdin))


def test_ok_sends_base64_and_limits_and_decodes_output():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["params"] = dict(request.url.params)
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={
            "token": "t1", "status": {"id": 3}, "stdout": b64("Привет, 5\n"),
            "stderr": None, "compile_output": None, "message": None, "time": "0.002", "memory": 1024,
        })

    result = run(make_runner(handler), code='printf("%d", 5);', stdin="5")

    assert result.status == "ok"
    assert result.stdout == "Привет, 5\n"
    assert result.time == 0.002 and result.memory == 1024
    assert seen["headers"]["X-RapidAPI-Key"] == "test-key"
    assert seen["headers"]["X-RapidAPI-Host"] == "judge0.test"
    assert seen["params"]["wait"] == "true" and seen["params"]["base64_encoded"] == "true"
    body = seen["body"]
    assert base64.b64decode(body["source_code"]).decode() == 'printf("%d", 5);'
    assert base64.b64decode(body["stdin"]).decode() == "5"
    assert body["language_id"] == 50
    assert body["cpu_time_limit"] == 2 and body["memory_limit"] == 128_000


@pytest.mark.parametrize("status_id, expected", [
    (5, "time_limit"), (6, "compile_error"), (7, "runtime_error"), (11, "runtime_error"), (13, "internal_error"),
])
def test_status_mapping(status_id, expected):
    result = run(make_runner(lambda r: httpx.Response(201, json={"token": "t", "status": {"id": status_id}})))
    assert result.status == expected


def test_compile_error_output():
    handler = lambda r: httpx.Response(201, json={  # noqa: E731
        "token": "t", "status": {"id": 6}, "compile_output": b64("main.c:1: error: expected ';'"),
    })
    result = run(make_runner(handler))
    assert result.status == "compile_error"
    assert "expected ';'" in result.compile_output


def test_polls_while_in_queue():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(201, json={"token": "abc", "status": {"id": 1}})
        if len(calls) < 3:
            return httpx.Response(200, json={"token": "abc", "status": {"id": 2}})
        return httpx.Response(200, json={"token": "abc", "status": {"id": 3}, "stdout": b64("done")})

    result = run(make_runner(handler))
    assert result.stdout == "done"
    assert calls == ["POST", "GET", "GET"]


def test_quota_exceeded():
    with pytest.raises(RunnerQuotaError):
        run(make_runner(lambda r: httpx.Response(429, json={"message": "quota"})))


def test_service_error_and_network_error():
    with pytest.raises(RunnerError):
        run(make_runner(lambda r: httpx.Response(500)))

    def broken(request):
        raise httpx.ConnectError("no network")

    with pytest.raises(RunnerError):
        run(make_runner(broken))
