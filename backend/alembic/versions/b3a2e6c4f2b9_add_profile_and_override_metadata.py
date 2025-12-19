"""Add profiles table and manual override metadata

Revision ID: b3a2e6c4f2b9
Revises: a34e1f321ed7
Create Date: 2025-12-10 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b3a2e6c4f2b9'
down_revision: Union[str, None] = 'a34e1f321ed7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('people', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pets', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('activities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_profiles_id'), 'profiles', ['id'], unique=False)
    op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=True)

    # Add manual override metadata to tasks
    op.add_column('tasks', sa.Column('manual_override_reason', sa.Text(), nullable=True))
    op.add_column('tasks', sa.Column('manual_override_source', sa.String(length=255), nullable=True))
    op.add_column('tasks', sa.Column('manual_override_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'manual_override_at')
    op.drop_column('tasks', 'manual_override_source')
    op.drop_column('tasks', 'manual_override_reason')
    op.drop_index(op.f('ix_profiles_user_id'), table_name='profiles')
    op.drop_index(op.f('ix_profiles_id'), table_name='profiles')
    op.drop_table('profiles')




