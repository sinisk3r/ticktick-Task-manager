"""add_quadrant_calculation_source

Revision ID: 0faa2669a272
Revises: b13720d6c407
Create Date: 2025-12-17 01:40:12.399752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0faa2669a272'
down_revision: Union[str, None] = 'b13720d6c407'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add quadrant_calculation_source column
    op.add_column(
        'tasks',
        sa.Column(
            'quadrant_calculation_source',
            sa.String(50),
            nullable=True,
            comment="How quadrant was calculated: 'llm' | 'rules' | 'manual'"
        )
    )

    # Backfill existing tasks
    op.execute("""
        UPDATE tasks
        SET quadrant_calculation_source = CASE
            WHEN manual_quadrant_override IS NOT NULL THEN 'manual'
            WHEN analyzed_at IS NOT NULL THEN 'llm'
            ELSE 'rules'
        END
    """)


def downgrade() -> None:
    # Remove quadrant_calculation_source column
    op.drop_column('tasks', 'quadrant_calculation_source')
