import json

import pytest

from app.config import settings
from app.content.loader import ContentError, NotFound, list_lesson_slugs, list_tasks, load_task
from tests.content_helpers import make_lesson, make_task


@pytest.fixture(autouse=True)
def content(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "content_dir", tmp_path)
    return tmp_path


def test_load_task(content):
    make_task(content)
    task = load_task("01-intro", "01-sum")
    assert task.full_slug == "01-intro/01-sum"
    assert task.title == "Задача 01-sum"
    assert task.statement.startswith("Сложи")
    assert len(task.tests) == 3 and task.tests[0].output == "5\n"
    assert task.solution == "SUM"


def test_missing_solution_is_allowed(content):
    make_task(content, solution=None)
    assert load_task("01-intro", "01-sum").solution is None


@pytest.mark.parametrize("lesson, task", [
    ("..", "01-sum"), ("01-intro", ".."), ("01-intro", "../01-intro"), ("01-Intro", "01-sum"),
    ("01-intro", "01_sum"), ("", "01-sum"), ("nope", "01-sum"), ("01-intro", "nope"),
])
def test_bad_or_unknown_slugs(content, lesson, task):
    make_task(content)
    with pytest.raises(NotFound):
        load_task(lesson, task)


def test_task_without_tests_is_content_error(content):
    path = make_task(content)
    (path / "task.json").write_text(json.dumps({"title": "x", "order": 1, "tests": []}), encoding="utf-8")
    with pytest.raises(ContentError):
        load_task("01-intro", "01-sum")


def test_broken_json_and_missing_statement(content):
    path = make_task(content)
    (path / "task.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(ContentError):
        load_task("01-intro", "01-sum")

    path = make_task(content, slug="02-x")
    (path / "statement.md").unlink()
    with pytest.raises(ContentError):
        load_task("01-intro", "02-x")


def test_lists_are_sorted_by_order(content):
    make_lesson(content, "b-lesson", order=1)
    make_lesson(content, "a-lesson", order=2)
    make_task(content, "b-lesson", "z-task", order=1)
    make_task(content, "b-lesson", "a-task", order=2)
    assert list_lesson_slugs() == ["b-lesson", "a-lesson"]
    assert [t.slug for t in list_tasks("b-lesson")] == ["z-task", "a-task"]
