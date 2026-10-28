"""Чтение уроков и задач из папки content/.

Структура:
    content/lessons/<урок>/meta.json            {"title", "order", "source", "hidden"}
    content/lessons/<урок>/lesson.md            теория и примеры
    content/lessons/<урок>/tasks/<задача>/
        task.json      {"title", "order", "hint", "tests": [{"input", "output"}, ...], "template_must_compile"}
        statement.md   условие
        template.c     заготовка кода
        solution.c     эталонное решение

Файлы читаются при каждом запросе — новый урок появляется на сайте без перезапуска.
Имена папок (slug) проверяются регулярным выражением: адрес вроде «../../etc» не пройдёт,
и через API нельзя прочитать файл за пределами content/.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.config import settings

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")


class NotFound(Exception):
    pass


class ContentError(Exception):
    """Файлы урока или задачи есть, но оформлены с ошибкой."""


class LessonMeta(BaseModel):
    title: str
    order: int
    source: str = ""  # по какой лекции сделан урок
    hidden: bool = False  # не показывать в списке (но по прямой ссылке открывается)


@dataclass
class Lesson:
    slug: str
    title: str
    order: int
    source: str
    hidden: bool
    body: str  # lesson.md


class TestCase(BaseModel):
    __test__ = False  # чтобы pytest не принимал класс за набор тестов

    input: str = ""
    output: str


class TaskMeta(BaseModel):
    title: str
    order: int
    hint: str = ""
    tests: list[TestCase] = Field(min_length=1)
    template_must_compile: bool = True  # false — для задач «исправь ошибку в программе»


@dataclass
class Task:
    lesson_slug: str
    slug: str
    title: str
    order: int
    statement: str
    template: str
    hint: str
    tests: list[TestCase]
    solution: str | None
    template_must_compile: bool = True

    @property
    def full_slug(self) -> str:
        return f"{self.lesson_slug}/{self.slug}"


def _lessons_dir() -> Path:
    return settings.content_dir / "lessons"


def _check_slug(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise NotFound(slug)


def _read_json(path: Path, model: type[BaseModel]):
    try:
        return model.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as e:
        raise ContentError(f"{path}: {e}") from e


def _read_text(path: Path, required: bool = True) -> str | None:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    if required:
        raise ContentError(f"Нет файла {path}")
    return None


def lesson_path(lesson_slug: str) -> Path:
    _check_slug(lesson_slug)
    path = _lessons_dir() / lesson_slug
    if not (path / "meta.json").is_file():
        raise NotFound(lesson_slug)
    return path


def load_lesson_meta(lesson_slug: str) -> LessonMeta:
    return _read_json(lesson_path(lesson_slug) / "meta.json", LessonMeta)


def load_lesson(lesson_slug: str) -> Lesson:
    path = lesson_path(lesson_slug)
    meta = load_lesson_meta(lesson_slug)
    return Lesson(
        slug=lesson_slug,
        title=meta.title,
        order=meta.order,
        source=meta.source,
        hidden=meta.hidden,
        body=_read_text(path / "lesson.md"),
    )


def load_task(lesson_slug: str, task_slug: str) -> Task:
    _check_slug(task_slug)
    path = lesson_path(lesson_slug) / "tasks" / task_slug
    if not (path / "task.json").is_file():
        raise NotFound(f"{lesson_slug}/{task_slug}")

    meta: TaskMeta = _read_json(path / "task.json", TaskMeta)
    return Task(
        lesson_slug=lesson_slug,
        slug=task_slug,
        title=meta.title,
        order=meta.order,
        statement=_read_text(path / "statement.md"),
        template=_read_text(path / "template.c"),
        hint=meta.hint,
        tests=meta.tests,
        solution=_read_text(path / "solution.c", required=False),
        template_must_compile=meta.template_must_compile,
    )


def list_lesson_slugs(include_hidden: bool = False) -> list[str]:
    """Уроки по порядку (поле order). Скрытые — только если include_hidden."""
    if not _lessons_dir().is_dir():
        return []
    metas = {
        p.name: load_lesson_meta(p.name)
        for p in _lessons_dir().iterdir()
        if SLUG_RE.match(p.name) and (p / "meta.json").is_file()
    }
    slugs = [s for s, m in metas.items() if include_hidden or not m.hidden]
    return sorted(slugs, key=lambda s: (metas[s].order, s))


def list_tasks(lesson_slug: str) -> list[Task]:
    tasks_dir = lesson_path(lesson_slug) / "tasks"
    if not tasks_dir.is_dir():
        return []
    tasks = [
        load_task(lesson_slug, p.name)
        for p in tasks_dir.iterdir()
        if SLUG_RE.match(p.name) and (p / "task.json").is_file()
    ]
    return sorted(tasks, key=lambda t: (t.order, t.slug))
