"""Прогресс лабораторных."""
from alembic import op
import sqlalchemy as sa
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None
def upgrade():
    op.create_table('lab_progress',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('lab_slug', sa.String(100), primary_key=True),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('state', sa.Text(), nullable=False))
def downgrade():
    op.drop_table('lab_progress')
