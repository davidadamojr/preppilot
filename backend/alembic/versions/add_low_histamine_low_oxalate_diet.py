"""add_low_histamine_low_oxalate_diet

Revision ID: add_low_histamine_low_oxalate
Revises: add_audit_logs_table
Create Date: 2025-12-29

Adds LOW_HISTAMINE_LOW_OXALATE value to the diettype enum for users
who need both low histamine and low oxalate diet restrictions.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_low_histamine_low_oxalate'
down_revision: Union[str, None] = 'add_audit_logs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add LOW_HISTAMINE_LOW_OXALATE to diettype enum."""
    op.execute("ALTER TYPE diettype ADD VALUE IF NOT EXISTS 'LOW_HISTAMINE_LOW_OXALATE'")


def downgrade() -> None:
    """Remove LOW_HISTAMINE_LOW_OXALATE from diettype enum.

    Note: PostgreSQL doesn't support removing enum values directly.
    This would require recreating the enum type and updating all columns.
    For safety, we leave the enum value in place on downgrade.
    """
    pass
