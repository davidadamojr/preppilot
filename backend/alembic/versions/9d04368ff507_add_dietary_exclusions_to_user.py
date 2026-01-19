"""add_dietary_exclusions_to_user

Revision ID: 9d04368ff507
Revises: 0001_initial
Create Date: 2025-11-24 21:38:54.401181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d04368ff507'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dietary_exclusions column to users table."""
    op.add_column(
        'users',
        sa.Column('dietary_exclusions', sa.JSON(), server_default='[]', nullable=False)
    )


def downgrade() -> None:
    """Remove dietary_exclusions column from users table."""
    op.drop_column('users', 'dietary_exclusions')
