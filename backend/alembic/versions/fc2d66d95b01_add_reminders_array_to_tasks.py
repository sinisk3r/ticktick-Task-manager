"""add_reminders_array_to_tasks

Revision ID: fc2d66d95b01
Revises: d4f8e9a1b2c3
Create Date: 2025-12-24 20:33:44.929513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fc2d66d95b01'
down_revision: Union[str, None] = 'd4f8e9a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add reminders JSONB column with default empty array
    op.add_column('tasks', sa.Column('reminders', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    
    # Migrate existing reminder_time data to reminders array
    # For tasks with both reminder_time and due_date, calculate minutes-before
    op.execute("""
        UPDATE tasks
        SET reminders = CASE
            WHEN reminder_time IS NOT NULL AND due_date IS NOT NULL THEN
                -- Calculate minutes-before, round to nearest integer, ensure non-negative
                -- Cast integer array to JSONB
                CASE
                    WHEN EXTRACT(EPOCH FROM (due_date - reminder_time)) / 60 >= 0 THEN
                        to_jsonb(ARRAY[ROUND(EXTRACT(EPOCH FROM (due_date - reminder_time)) / 60)::INTEGER])
                    ELSE
                        to_jsonb(ARRAY[0]::INTEGER[])
                END
            ELSE
                '[]'::jsonb
        END
    """)


def downgrade() -> None:
    # Remove reminders column
    op.drop_column('tasks', 'reminders')
