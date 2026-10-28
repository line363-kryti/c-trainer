"""Зависимость FastAPI «запускатель кода» и общий запуск с понятными ошибками.

Какой запускатель — решает RUNNER в .env. В тестах подменяется на поддельный.
"""
from fastapi import HTTPException, status

from app.config import settings
from app.runner.base import Runner, RunnerError, RunnerQuotaError, RunResult
from app.runner.judge0 import Judge0Runner
from app.runner.piston import PistonRunner


def get_runner() -> Runner:
    if settings.runner == "piston":
        return PistonRunner(settings.piston_url)

    if not settings.judge0_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Запуск кода не настроен: нет JUDGE0_KEY в .env",
        )
    return Judge0Runner(settings.judge0_url, settings.judge0_key, settings.judge0_language_id)


async def execute(runner: Runner, code: str, stdin: str) -> RunResult:
    """Запуск с переводом ошибок сервиса в HTTP-ответы 429 / 503."""
    try:
        return await runner.run(code, stdin)
    except RunnerQuotaError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except RunnerError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
