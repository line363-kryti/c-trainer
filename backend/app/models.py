"""Таблицы базы данных.

Уроки и задачи в базе НЕ хранятся — они лежат в папке content/.
База хранит только пользователей и их прогресс, ссылаясь на уроки и задачи по slug
(например, lesson_slug = "01-intro", task_slug = "01-intro/02-sum").
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # только хэш, сам пароль не храним
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LessonProgress(Base):
    """Строка есть — урок пройден."""

    __tablename__ = "lesson_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lesson_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaskProgress(Base):
    """Состояние задачи у пользователя. Строки нет — задачу ещё не открывали."""

    __tablename__ = "task_progress"
    __table_args__ = (CheckConstraint("status IN ('in_progress', 'solved')", name="task_status"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    task_slug: Mapped[str] = mapped_column(String(150), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), server_default="in_progress")
    last_code: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Submission(Base):
    """История нажатий «Проверить»: какой код отправлен и сколько тестов прошло."""

    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_user_task", "user_id", "task_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_slug: Mapped[str] = mapped_column(String(150))
    code: Mapped[str] = mapped_column(Text)
    passed: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LabProgress(Base):
    """Отдельный прогресс лабораторных, не влияет на счётчики уроков."""
    __tablename__ = "lab_progress"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lab_slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    code: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, default="{}")
