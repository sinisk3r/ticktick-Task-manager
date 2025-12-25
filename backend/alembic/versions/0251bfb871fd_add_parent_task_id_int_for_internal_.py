"""add_parent_task_id_int_for_internal_relationships

Revision ID: 0251bfb871fd
Revises: fc2d66d95b01
Create Date: 2025-12-25 00:45:08.071480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0251bfb871fd'
down_revision: Union[str, None] = 'fc2d66d95b01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_task_id_int column for internal parent-child relationships
    # Keep parent_task_id (String) for TickTick compatibility
    op.add_column('tasks', sa.Column('parent_task_id_int', sa.Integer(), nullable=True))
    
    # Create foreign key constraint to tasks.id
    op.create_foreign_key(
        'tasks_parent_task_id_int_fkey',
        'tasks', 'tasks',
        ['parent_task_id_int'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for efficient queries
    op.create_index('ix_tasks_parent_task_id_int', 'tasks', ['parent_task_id_int'])


def downgrade() -> None:
    # Drop index and foreign key constraint
    op.drop_index('ix_tasks_parent_task_id_int', table_name='tasks')
    op.drop_constraint('tasks_parent_task_id_int_fkey', 'tasks', type_='foreignkey')
    
    # Drop column
    op.drop_column('tasks', 'parent_task_id_int')
