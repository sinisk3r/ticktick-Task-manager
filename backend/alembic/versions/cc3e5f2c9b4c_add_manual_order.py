"""Add manual_order for task ordering

Revision ID: cc3e5f2c9b4c
Revises: b3a2e6c4f2b9
Create Date: 2025-12-10 13:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cc3e5f2c9b4c'
down_revision: Union[str, None] = 'b3a2e6c4f2b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('manual_order', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_tasks_manual_order'), 'tasks', ['manual_order'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_manual_order'), table_name='tasks')
    op.drop_column('tasks', 'manual_order')


