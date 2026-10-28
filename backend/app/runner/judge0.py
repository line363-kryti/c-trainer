"""Клиент Judge0 CE (через RapidAPI).

Как работает один запуск:
1. POST /submissions с кодом, вводом и лимитами; wait=true — сервис отвечает,
   когда программа уже скомпилирована и выполнена.
2. Если сервис не успел и вернул «в очереди», опрашиваем GET /submissions/{token}.
3. Код и вывод передаём в base64, чтобы не сломались русские буквы и спецсимволы.
"""
import asyncio
import base64
from urllib.parse import urlparse

import httpx

from app.runner.base import (
    CPU_TIME_LIMIT_S,
    MAX_OUTPUT_CHARS,
    MEMORY_LIMIT_KB,
    WALL_TIME_LIMIT_S,
    RunResult,
    RunnerError,
    RunnerQuotaError,
)

FIELDS = "token,status,stdout,stderr,compile_output,message,time,memory"
PENDING = {1, 2}  # 1 — в очереди, 2 — выполняется

# Номера статусов Judge0 -> наши статусы. 7–12 — разные падения программы (SIGSEGV, SIGFPE и т.п.)
STATUS_MAP = {3: "ok", 4: "ok", 5: "time_limit", 6: "compile_error", 13: "internal_error", 14: "internal_error"}
STATUS_MAP.update({code: "runtime_error" for code in range(7, 13)})


def _b64encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _b64decode(value: str | None) -> str:
    if not value:
        return ""
    text = base64.b64decode(value).decode("utf-8", errors="replace")
    return text[:MAX_OUTPUT_CHARS]


def to_result(data: dict) -> RunResult:
    status_id = (data.get("status") or {}).get("id")
    return RunResult(
        status=STATUS_MAP.get(status_id, "internal_error"),
        stdout=_b64decode(data.get("stdout")),
        stderr=_b64decode(data.get("stderr")),
        compile_output=_b64decode(data.get("compile_output")),
        time=float(data["time"]) if data.get("time") is not None else None,
        memory=data.get("memory"),
        message=_b64decode(data.get("message")),
    )


class Judge0Runner:
    def __init__(
        self,
        url: str,
        key: str,
        language_id: int,
        transport: httpx.AsyncBaseTransport | None = None,  # подмена сети в тестах
        poll_interval: float = 0.5,
        max_polls: int = 20,
    ):
        self._url = url
        self._headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": urlparse(url).hostname or ""}
        self._language_id = language_id
        self._transport = transport
        self._poll_interval = poll_interval
        self._max_polls = max_polls

    async def run(self, code: str, stdin: str) -> RunResult:
        payload = {
            "source_code": _b64encode(code),
            "stdin": _b64encode(stdin),
            "language_id": self._language_id,
            "cpu_time_limit": CPU_TIME_LIMIT_S,
            "wall_time_limit": WALL_TIME_LIMIT_S,
            "memory_limit": MEMORY_LIMIT_KB,
        }
        params = {"base64_encoded": "true", "fields": FIELDS}

        async with httpx.AsyncClient(
            base_url=self._url, headers=self._headers, timeout=30, transport=self._transport
        ) as client:
            data = await self._request(client, "POST", "/submissions", params={**params, "wait": "true"}, json=payload)
            for _ in range(self._max_polls):
                if (data.get("status") or {}).get("id") not in PENDING:
                    break
                await asyncio.sleep(self._poll_interval)
                data = await self._request(client, "GET", f"/submissions/{data['token']}", params=params)
            else:
                raise RunnerError("Сервис запуска слишком долго не отвечает")

        return to_result(data)

    @staticmethod
    async def _request(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> dict:
        try:
            response = await client.request(method, path, **kwargs)
        except httpx.HTTPError as e:
            raise RunnerError("Сервис запуска недоступен") from e
        if response.status_code == 429:
            raise RunnerQuotaError("Закончился лимит запусков у сервиса, попробуй позже")
        if response.status_code >= 400:
            # тело ответа не показываем пользователю: там могут быть служебные детали
            raise RunnerError(f"Сервис запуска ответил ошибкой {response.status_code}")
        return response.json()
