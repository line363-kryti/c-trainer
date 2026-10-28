"""Общий вид результата запуска — не зависит от того, какой сервис запускает код.

Если когда-нибудь заменим Judge0 на Piston или свой сервер, поменяется только
класс-«запускатель», а методы API и проверка задач останутся как есть.
"""
from dataclasses import dataclass
from typing import Literal, Protocol

RunStatus = Literal["ok", "compile_error", "runtime_error", "time_limit", "internal_error"]

# Лимиты на один запуск
CPU_TIME_LIMIT_S = 2
WALL_TIME_LIMIT_S = 5
MEMORY_LIMIT_KB = 128_000
MAX_OUTPUT_CHARS = 64 * 1024  # длиннее вывод обрезаем, чтобы не гонять мегабайты


@dataclass
class RunResult:
    status: RunStatus
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time: float | None = None  # секунды
    memory: int | None = None  # КБ
    message: str = ""  # пояснение от сервиса (например, номер сигнала при падении)


class RunnerError(Exception):
    """Сервис запуска недоступен или ответил ошибкой."""


class RunnerQuotaError(RunnerError):
    """Закончился лимит запусков у сервиса (например, бесплатный тариф на день)."""


class Runner(Protocol):
    async def run(self, code: str, stdin: str) -> RunResult: ...
