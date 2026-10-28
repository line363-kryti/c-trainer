"""Задачи: условие, автосохранение кода, «Запустить», «Проверить», подсказка, эталон.

Адрес задачи — /api/tasks/<урок>/<задача>, например /api/tasks/01-intro/02-sum.
Всё только для вошедших: прогресс и код хранятся у каждого пользователя свои.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.content.loader import NotFound, Task, TestCase, list_tasks, load_lesson_meta, load_task
from app.db import get_db
from app.limiter import limiter, user_key
from app.models import Submission, TaskProgress, User
from app.routers.run import MAX_CODE_CHARS, MAX_STDIN_CHARS, RunOut
from app.runner.base import RunResult, RunStatus
from app.runner.checker import first_diff
from app.runner.deps import execute, get_runner

router = APIRouter(prefix="/api/tasks/{lesson_slug}/{task_slug}", tags=["tasks"])

PARALLEL_TESTS = 4  # сколько тестов гоняем одновременно


def get_task(lesson_slug: str, task_slug: str) -> Task:
    try:
        return load_task(lesson_slug, task_slug)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")


def _progress(db: Session, user: User, task: Task) -> TaskProgress:
    """Строка прогресса пользователя по задаче; создаётся при первом обращении."""
    progress = db.get(TaskProgress, (user.id, task.full_slug))
    if progress is None:
        progress = TaskProgress(user_id=user.id, task_slug=task.full_slug, status="in_progress", attempts=0)
        db.add(progress)
    return progress


# ---------- схемы ----------

class TaskOut(BaseModel):
    lesson_slug: str
    lesson_title: str
    slug: str
    title: str
    statement: str
    template: str
    code: str  # последний сохранённый код или заготовка
    status: str | None  # None — ещё не открывали, in_progress, solved
    attempts: int
    has_hint: bool
    has_solution: bool
    tests_count: int
    next_task: str | None  # slug следующей задачи этого урока



class CodeIn(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)


class TaskRunIn(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)
    stdin: str = Field(default="", max_length=MAX_STDIN_CHARS)


class CheckIn(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)


class DiffOut(BaseModel):
    line: int
    expected: str | None
    got: str | None


class TestResultOut(BaseModel):
    __test__ = False  # чтобы pytest не принимал класс за набор тестов

    index: int  # номер теста, с 1
    passed: bool
    status: RunStatus
    input: str
    expected: str
    got: str
    stderr: str
    message: str
    time: float | None
    diff: DiffOut | None  # первая отличающаяся строка, если программа отработала, но ответ не тот


class CheckOut(BaseModel):
    passed: int
    total: int
    solved: bool
    compile_error: str | None  # если не скомпилировалось — тесты не запускаются
    results: list[TestResultOut]


# ---------- методы ----------

@router.get("", response_model=TaskOut)
def get(task: Task = Depends(get_task), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    progress = db.get(TaskProgress, (user.id, task.full_slug))
    siblings = [t.slug for t in list_tasks(task.lesson_slug)]
    position = siblings.index(task.slug)
    return TaskOut(
        lesson_slug=task.lesson_slug,
        lesson_title=load_lesson_meta(task.lesson_slug).title,
        slug=task.slug,
        title=task.title,
        statement=task.statement,
        template=task.template,
        code=progress.last_code if progress and progress.last_code is not None else task.template,
        status=progress.status if progress else None,
        attempts=progress.attempts if progress else 0,
        has_hint=bool(task.hint),
        has_solution=task.solution is not None,
        tests_count=len(task.tests),
        next_task=siblings[position + 1] if position + 1 < len(siblings) else None,
    )


@router.put("/code", status_code=status.HTTP_204_NO_CONTENT)
def save_code(
    data: CodeIn, task: Task = Depends(get_task), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    _progress(db, user, task).last_code = data.code
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/run", response_model=RunOut)
@limiter.limit("10/minute", key_func=user_key)
async def run(
    request: Request,
    data: TaskRunIn,
    task: Task = Depends(get_task),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    runner=Depends(get_runner),
) -> RunResult:
    _progress(db, user, task).last_code = data.code
    db.commit()
    return await execute(runner, data.code, data.stdin)


@router.post("/check", response_model=CheckOut)
@limiter.limit("5/minute", key_func=user_key)
async def check(
    request: Request,
    data: CheckIn,
    task: Task = Depends(get_task),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    runner=Depends(get_runner),
) -> CheckOut:
    tests = task.tests

    # Первый тест отдельно: если код не компилируется, остальные гонять незачем
    first = await execute(runner, data.code, tests[0].input)
    if first.status == "compile_error":
        result = CheckOut(passed=0, total=len(tests), solved=False, compile_error=first.compile_output, results=[])
    else:
        semaphore = asyncio.Semaphore(PARALLEL_TESTS)

        async def run_one(stdin: str) -> RunResult:
            async with semaphore:
                return await execute(runner, data.code, stdin)

        rest = await asyncio.gather(*(run_one(t.input) for t in tests[1:]))
        runs = [first, *rest]
        results = [_judge(i, test, outcome) for i, (test, outcome) in enumerate(zip(tests, runs), start=1)]
        passed = sum(r.passed for r in results)
        result = CheckOut(
            passed=passed, total=len(tests), solved=passed == len(tests), compile_error=None, results=results
        )

    _save_check(db, user, task, data.code, result)
    return result


@router.get("/hint")
def hint(task: Task = Depends(get_task), user: User = Depends(get_current_user)) -> dict:
    if not task.hint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="У этой задачи нет подсказки")
    return {"hint": task.hint}


@router.get("/solution")
def solution(task: Task = Depends(get_task), user: User = Depends(get_current_user)) -> dict:
    if task.solution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="У этой задачи нет эталона")
    return {"code": task.solution}


# ---------- вспомогательное ----------

def _judge(index: int, test: TestCase, outcome: RunResult) -> TestResultOut:
    """Тест пройден, если программа отработала без ошибок и вывод совпал с ожидаемым."""
    diff = first_diff(test.output, outcome.stdout) if outcome.status == "ok" else None
    return TestResultOut(
        index=index,
        passed=outcome.status == "ok" and diff is None,
        status=outcome.status,
        input=test.input,
        expected=test.output,
        got=outcome.stdout,
        stderr=outcome.stderr,
        message=outcome.message,
        time=outcome.time,
        diff=DiffOut(line=diff.line, expected=diff.expected, got=diff.got) if diff else None,
    )


def _save_check(db: Session, user: User, task: Task, code: str, result: CheckOut) -> None:
    progress = _progress(db, user, task)
    progress.last_code = code
    progress.attempts += 1
    if result.solved and progress.status != "solved":
        progress.status = "solved"
        progress.solved_at = datetime.now(timezone.utc)
    db.add(Submission(user_id=user.id, task_slug=task.full_slug, code=code, passed=result.passed, total=result.total))
    db.commit()
