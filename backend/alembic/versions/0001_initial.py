"""Первые таблицы: пользователи, прогресс по урокам и задачам, история проверок

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "lesson_progress",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lesson_slug", sa.String(100), primary_key=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "task_progress",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("task_slug", sa.String(150), primary_key=True),
        sa.Column("status", sa.String(20), server_default="in_progress", nullable=False),
        sa.Column("last_code", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('in_progress', 'solved')", name="task_status"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_slug", sa.String(150), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("passed", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_submissions_user_task", "submissions", ["user_id", "task_slug"])


def downgrade() -> None:
    op.drop_index("ix_submissions_user_task", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("task_progress")
    op.drop_table("lesson_progress")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
