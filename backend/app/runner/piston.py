"""Клиент Piston — своего движка запуска кода (контейнер piston в docker-compose).

Один запуск = один запрос POST /api/v2/execute: Piston компилирует main.c через gcc
и, если компиляция прошла, запускает программу внутри песочницы isolate
с лимитами по времени, памяти и числу процессов, без доступа к сети.
"""
import httpx

from app.runner.base import (
    CPU_TIME_LIMIT_S,
    MAX_OUTPUT_CHARS,
    MEMORY_LIMIT_KB,
    WALL_TIME_LIMIT_S,
    RunResult,
    RunnerError,
)

LANGUAGE = "c"
VERSION = "10.2.0"  # версия gcc, установленная в Piston

# Понятные пояснения к сигналам, которыми ОС останавливает упавшую программу
SIGNAL_HINTS = {
    "SIGSEGV": "Обращение к чужой памяти (SIGSEGV): выход за границы массива или разыменование NULL",
    "SIGFPE": "Арифметическая ошибка (SIGFPE): например, деление на ноль",
    "SIGABRT": "Программа аварийно остановлена (SIGABRT): например, сработал assert",
    "SIGKILL": "Программу принудительно остановили (SIGKILL): скорее всего, превышен лимит памяти",
}

# Программу запускает bash-обёртка Piston, и падение по сигналу N приходит как код 128 + N
EXIT_CODE_SIGNALS = {134: "SIGABRT", 136: "SIGFPE", 137: "SIGKILL", 139: "SIGSEGV"}


def _cut(text: str | None) -> str:
    return (text or "")[:MAX_OUTPUT_CHARS]


def _compile_output(compile_: dict) -> str:
    # Piston дописывает к файлу расширение, и gcc пишет «main.c.c» — возвращаем привычное имя.
    # Строку от chmod (скрипт Piston после неудачной компиляции) убираем: к коду она не относится
    text = _cut(compile_.get("output")).replace("main.c.c", "main.c")
    return "\n".join(line for line in text.split("\n") if not line.startswith("chmod: cannot access"))


def to_result(data: dict) -> RunResult:
    compile_ = data.get("compile")
    if compile_ and compile_.get("code") != 0:
        return RunResult(
            status="compile_error",
            compile_output=_compile_output(compile_),
            message="Компиляция не уложилась во время" if compile_.get("status") == "TO" else "",
        )

    run = data.get("run") or {}
    status = run.get("status")
    signal = run.get("signal") or EXIT_CODE_SIGNALS.get(run.get("code"))

    if status == "TO":
        result_status, message = "time_limit", "Превышен лимит времени"
    elif status == "XX":
        result_status, message = "internal_error", "Внутренняя ошибка песочницы"
    elif status in ("OL", "EL"):
        result_status, message = "runtime_error", "Слишком длинный вывод"
    elif status in ("RE", "SG") or signal or run.get("code") != 0:
        result_status = "runtime_error"
        message = SIGNAL_HINTS.get(signal) or (
            f"Программа завершилась с кодом {run.get('code')}" if run.get("code") else (run.get("message") or "")
        )
    else:
        result_status, message = "ok", ""

    cpu_ms = run.get("cpu_time")
    memory = run.get("memory")  # Piston отдаёт «КБ × 1000»
    return RunResult(
        status=result_status,
        stdout=_cut(run.get("stdout")),
        stderr=_cut(run.get("stderr")),
        compile_output=_compile_output(compile_) if compile_ else "",  # предупреждения gcc
        time=cpu_ms / 1000 if cpu_ms is not None else None,
        memory=memory // 1000 if memory is not None else None,
        message=message,
    )


class PistonRunner:
    def __init__(self, url: str, transport: httpx.AsyncBaseTransport | None = None):
        self._url = url
        self._transport = transport  # подмена сети в тестах

    async def run(self, code: str, stdin: str) -> RunResult:
        payload = {
            "language": LANGUAGE,
            "version": VERSION,
            "files": [{"name": "main.c", "content": code}],
            "stdin": stdin,
            "run_timeout": WALL_TIME_LIMIT_S * 1000,
            "run_cpu_time": CPU_TIME_LIMIT_S * 1000,
            "run_memory_limit": MEMORY_LIMIT_KB * 1000,  # в байтах
        }
        try:
            async with httpx.AsyncClient(base_url=self._url, timeout=30, transport=self._transport) as client:
                response = await client.post("/api/v2/execute", json=payload)
        except httpx.HTTPError as e:
            raise RunnerError("Сервис запуска недоступен: запущен ли контейнер piston?") from e

        if response.status_code == 400 and "unknown" in response.text:
            raise RunnerError("В Piston не установлен компилятор gcc (см. README)")
        if response.status_code >= 400:
            raise RunnerError(f"Сервис запуска ответил ошибкой {response.status_code}")
        return to_result(response.json())
