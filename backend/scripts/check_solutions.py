"""Прогон всех эталонных решений по их тестам (нужен живой Piston).

Для каждой задачи проверяет:
- эталон solution.c проходит все тесты;
- заготовка template.c компилируется (чтобы ученик не начинал с ошибки компиляции),
  кроме задач «исправь ошибку» (template_must_compile=false);
- заготовка без изменений НЕ проходит все тесты.

Запуск: docker compose exec -e PYTHONPATH=. backend python scripts/check_solutions.py
Код выхода 0 — всё хорошо, 1 — есть проблемы.
"""
import asyncio
import sys

from app.config import settings
from app.content.loader import list_lesson_slugs, list_tasks
from app.runner.checker import first_diff
from app.runner.piston import PistonRunner


async def check_task(runner: PistonRunner, task) -> list[str]:
    problems = []
    if task.solution is None:
        problems.append("нет solution.c")
    else:
        for i, test in enumerate(task.tests, start=1):
            r = await runner.run(task.solution, test.input)
            if r.status != "ok":
                problems.append(f"тест {i}: эталон упал ({r.status}) {r.message or r.compile_output[:200]}")
            elif diff := first_diff(test.output, r.stdout):
                problems.append(f"тест {i}: строка {diff.line}: ожидалось {diff.expected!r}, эталон вывел {diff.got!r}")

    template_run = await runner.run(task.template, "")
    compiles = template_run.status != "compile_error"
    if task.template_must_compile and not compiles:
        problems.append(f"заготовка не компилируется: {template_run.compile_output[:200]}")
    if not task.template_must_compile and compiles:
        problems.append("заготовка должна быть с ошибкой компиляции (template_must_compile=false), а она компилируется")

    # Заготовка не должна сразу проходить все тесты — иначе задачу можно «решить», ничего не написав
    if compiles:
        for test in task.tests:
            r = await runner.run(task.template, test.input)
            if r.status != "ok" or first_diff(test.output, r.stdout):
                break
        else:
            problems.append("заготовка без изменений проходит все тесты")
    return problems


async def main() -> int:
    runner = PistonRunner(settings.piston_url)
    total = bad = 0
    for lesson in list_lesson_slugs(include_hidden=True):
        for task in list_tasks(lesson):
            total += 1
            problems = await check_task(runner, task)
            print(f"{'OK ' if not problems else 'BAD'} {task.full_slug} ({len(task.tests)} тестов)")
            for p in problems:
                print(f"     - {p}")
            bad += bool(problems)
    print(f"\nЗадач: {total}, с проблемами: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
