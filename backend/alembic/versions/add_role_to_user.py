"""add_role_to_user

Revision ID: add_role_to_user
Revises: 9d04368ff507
Create Date: 2025-12-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_role_to_user'
down_revision: Union[str, None] = '9d04368ff507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column to users table with RBAC support."""
    # Create the enum type first (using uppercase to match SQLAlchemy default behavior)
    role_enum = sa.Enum('USER', 'ADMIN', name='userrole')
    role_enum.create(op.get_bind(), checkfirst=True)

    # Add role column with default 'USER' for existing users
    op.add_column(
        'users',
        sa.Column('role', role_enum, server_default='USER', nullable=False)
    )


def downgrade() -> None:
    """Remove role column from users table."""
    op.drop_column('users', 'role')

    # Drop the enum type
    role_enum = sa.Enum('USER', 'ADMIN', name='userrole')
    role_enum.drop(op.get_bind(), checkfirst=True)
