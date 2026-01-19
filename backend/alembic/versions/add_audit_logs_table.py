"""add_audit_logs_table

Revision ID: add_audit_logs_table
Revises: add_performance_indexes
Create Date: 2025-12-21

Adds audit_logs table for tracking user actions and security events.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM


# revision identifiers, used by Alembic.
revision: str = 'add_audit_logs_table'
down_revision: Union[str, None] = 'add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs table and auditaction enum."""
    # Create the enum type via raw SQL to avoid SQLAlchemy's auto-creation issues
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE auditaction AS ENUM (
                'LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'REGISTER',
                'PASSWORD_CHANGE', 'PASSWORD_RESET_REQUEST',
                'CREATE', 'READ', 'UPDATE', 'DELETE',
                'BULK_CREATE', 'BULK_DELETE',
                'EXPORT', 'EMAIL_SENT', 'ROLE_CHANGE', 'STATUS_CHANGE'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Use postgresql.ENUM with create_type=False since we created it above
    audit_action_enum = ENUM(
        'LOGIN', 'LOGOUT', 'LOGIN_FAILED', 'REGISTER',
        'PASSWORD_CHANGE', 'PASSWORD_RESET_REQUEST',
        'CREATE', 'READ', 'UPDATE', 'DELETE',
        'BULK_CREATE', 'BULK_DELETE',
        'EXPORT', 'EMAIL_SENT', 'ROLE_CHANGE', 'STATUS_CHANGE',
        name='auditaction',
        create_type=False
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('action', audit_action_enum, nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False, index=True),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('details', sa.JSON, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()'), index=True),
    )


def downgrade() -> None:
    """Remove audit_logs table and auditaction enum."""
    op.drop_table('audit_logs')

    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS auditaction')
