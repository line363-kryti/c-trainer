"""Уроки и прогресс: список уроков, страница урока, отметка «пройдено», общая сводка.

Отметка «пройдено» — это строка в lesson_progress (есть строка — урок пройден).
Решённые задачи берутся из task_progress со статусом solved.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.content.loader import Lesson, NotFound, list_lesson_slugs, list_tasks, load_lesson
from app.db import get_db
from app.models import LessonProgress, TaskProgress, User

router = APIRouter(prefix="/api", tags=["lessons"])


def get_lesson(lesson_slug: str) -> Lesson:
    try:
        return load_lesson(lesson_slug)
    except NotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Урок не найден")


def _completed_lessons(db: Session, user: User) -> set[str]:
    return set(db.scalars(select(LessonProgress.lesson_slug).where(LessonProgress.user_id == user.id)))


def _task_statuses(db: Session, user: User) -> dict[str, str]:
    rows = db.execute(select(TaskProgress.task_slug, TaskProgress.status).where(TaskProgress.user_id == user.id))
    return dict(rows.all())


# ---------- схемы ----------

class LessonSummary(BaseModel):
    slug: str
    title: str
    source: str
    completed: bool
    tasks_total: int
    tasks_solved: int


class TaskItem(BaseModel):
    slug: str
    title: str
    status: str | None  # None — не открывали, in_progress, solved


class LessonOut(BaseModel):
    slug: str
    title: str
    source: str
    body: str
    completed: bool
    tasks: list[TaskItem]
    prev: LessonSummary | None
    next: LessonSummary | None


class ProgressOut(BaseModel):
    lessons_total: int
    lessons_completed: int
    tasks_total: int
    tasks_solved: int


# ---------- методы ----------

@router.get("/lessons", response_model=list[LessonSummary])
def lessons(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[LessonSummary]:
    completed, statuses = _completed_lessons(db, user), _task_statuses(db, user)
    return [_summary(load_lesson(slug), completed, statuses) for slug in list_lesson_slugs()]


@router.get("/lessons/{lesson_slug}", response_model=LessonOut)
def lesson(
    lesson: Lesson = Depends(get_lesson), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> LessonOut:
    completed, statuses = _completed_lessons(db, user), _task_statuses(db, user)

    # Соседние уроки — только среди видимых; у скрытого урока соседей нет
    slugs = list_lesson_slugs()
    i = slugs.index(lesson.slug) if lesson.slug in slugs else None
    neighbour = lambda j: _summary(load_lesson(slugs[j]), completed, statuses)  # noqa: E731

    return LessonOut(
        slug=lesson.slug,
        title=lesson.title,
        source=lesson.source,
        body=lesson.body,
        completed=lesson.slug in completed,
        tasks=[TaskItem(slug=t.slug, title=t.title, status=statuses.get(t.full_slug)) for t in list_tasks(lesson.slug)],
        prev=neighbour(i - 1) if i is not None and i > 0 else None,
        next=neighbour(i + 1) if i is not None and i + 1 < len(slugs) else None,
    )


@router.post("/lessons/{lesson_slug}/complete", status_code=status.HTTP_204_NO_CONTENT)
def mark_completed(
    lesson: Lesson = Depends(get_lesson), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    if db.get(LessonProgress, (user.id, lesson.slug)) is None:  # повторное нажатие ничего не ломает
        db.add(LessonProgress(user_id=user.id, lesson_slug=lesson.slug))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/lessons/{lesson_slug}/complete", status_code=status.HTTP_204_NO_CONTENT)
def unmark_completed(
    lesson: Lesson = Depends(get_lesson), user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    row = db.get(LessonProgress, (user.id, lesson.slug))
    if row is not None:
        db.delete(row)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/progress", response_model=ProgressOut)
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProgressOut:
    completed, statuses = _completed_lessons(db, user), _task_statuses(db, user)
    summaries = [_summary(load_lesson(slug), completed, statuses) for slug in list_lesson_slugs()]
    return ProgressOut(
        lessons_total=len(summaries),
        lessons_completed=sum(s.completed for s in summaries),
        tasks_total=sum(s.tasks_total for s in summaries),
        tasks_solved=sum(s.tasks_solved for s in summaries),
    )


def _summary(lesson: Lesson, completed: set[str], statuses: dict[str, str]) -> LessonSummary:
    tasks = list_tasks(lesson.slug)
    return LessonSummary(
        slug=lesson.slug,
        title=lesson.title,
        source=lesson.source,
        completed=lesson.slug in completed,
        tasks_total=len(tasks),
        tasks_solved=sum(statuses.get(t.full_slug) == "solved" for t in tasks),
    )
