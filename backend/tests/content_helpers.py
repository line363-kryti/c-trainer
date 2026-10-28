"""Создание учебного контента во временной папке для тестов."""
import json
from pathlib import Path

TEMPLATE = "int main(void) { return 0; }\n"
SOLUTION = "SUM"  # для FakeRunner: «правильная» программа


def make_lesson(
    root: Path, slug: str = "01-intro", title: str = "Введение", order: int = 1, hidden: bool = False
) -> Path:
    path = root / "lessons" / slug
    path.mkdir(parents=True, exist_ok=True)
    meta = {"title": title, "order": order, "source": "Лекция 1", "hidden": hidden}
    (path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (path / "lesson.md").write_text(f"Теория урока {slug}", encoding="utf-8")
    return path


def make_task(
    root: Path,
    lesson: str = "01-intro",
    slug: str = "01-sum",
    tests: list | None = None,
    hint: str = "Сложи числа",
    solution: str | None = SOLUTION,
    order: int = 1,
) -> Path:
    if not (root / "lessons" / lesson / "meta.json").exists():
        make_lesson(root, lesson)
    path = root / "lessons" / lesson / "tasks" / slug
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "title": f"Задача {slug}",
        "order": order,
        "hint": hint,
        "tests": tests if tests is not None else [
            {"input": "2 3\n", "output": "5\n"},
            {"input": "-1 1\n", "output": "0\n"},
            {"input": "10 20\n", "output": "30\n"},
        ],
    }
    (path / "task.json").write_text(json.dumps(meta), encoding="utf-8")
    (path / "statement.md").write_text("Сложи **два** числа.", encoding="utf-8")
    (path / "template.c").write_text(TEMPLATE, encoding="utf-8")
    if solution is not None:
        (path / "solution.c").write_text(solution, encoding="utf-8")
    return path
