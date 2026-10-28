"""Свободный запуск кода: свой код + свой ввод -> вывод программы.

Только для вошедших и не чаще 10 раз в минуту на пользователя.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user
from app.limiter import limiter, user_key
from app.models import User
from app.runner.base import RunResult, RunStatus
from app.runner.deps import execute, get_runner

router = APIRouter(prefix="/api", tags=["run"])

MAX_CODE_CHARS = 64 * 1024
MAX_STDIN_CHARS = 16 * 1024


class RunIn(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)
    stdin: str = Field(default="", max_length=MAX_STDIN_CHARS)


class RunOut(BaseModel):
    status: RunStatus
    stdout: str
    stderr: str
    compile_output: str
    time: float | None
    memory: int | None
    message: str


@router.post("/run", response_model=RunOut)
@limiter.limit("10/minute", key_func=user_key)
async def run(
    request: Request,
    data: RunIn,
    user: User = Depends(get_current_user),
    runner=Depends(get_runner),
) -> RunResult:
    return await execute(runner, data.code, data.stdin)
