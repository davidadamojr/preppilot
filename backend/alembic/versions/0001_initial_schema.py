"""initial_schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-11-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('diet_type', sa.Enum('LOW_HISTAMINE', 'FODMAP', 'FRUCTOSE_FREE', name='diettype'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create recipes table
    op.create_table(
        'recipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('diet_tags', sa.JSON(), nullable=False),
        sa.Column('meal_type', sa.String(50), nullable=False),
        sa.Column('ingredients', sa.JSON(), nullable=False),
        sa.Column('prep_steps', sa.JSON(), nullable=False),
        sa.Column('prep_time_minutes', sa.Integer(), nullable=False),
        sa.Column('reusability_index', sa.Float(), nullable=False),
        sa.Column('servings', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recipes_name', 'recipes', ['name'])
    op.create_index('ix_recipes_meal_type', 'recipes', ['meal_type'])

    # Create meal_plans table
    op.create_table(
        'meal_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diet_type', sa.Enum('LOW_HISTAMINE', 'FODMAP', 'FRUCTOSE_FREE', name='diettype', create_type=False), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_meal_plans_user_id', 'meal_plans', ['user_id'])
    op.create_index('ix_meal_plans_start_date', 'meal_plans', ['start_date'])
    op.create_index('ix_meal_plans_end_date', 'meal_plans', ['end_date'])

    # Create meal_slots table
    op.create_table(
        'meal_slots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('meal_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipe_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('meal_type', sa.String(50), nullable=False),
        sa.Column('prep_status', sa.Enum('PENDING', 'DONE', 'SKIPPED', name='prepstatus'), nullable=False),
        sa.Column('prep_completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['meal_plan_id'], ['meal_plans.id']),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_meal_slots_meal_plan_id', 'meal_slots', ['meal_plan_id'])
    op.create_index('ix_meal_slots_date', 'meal_slots', ['date'])

    # Create fridge_items table
    op.create_table(
        'fridge_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ingredient_name', sa.String(255), nullable=False),
        sa.Column('quantity', sa.String(100), nullable=False),
        sa.Column('days_remaining', sa.Integer(), nullable=False),
        sa.Column('added_date', sa.Date(), nullable=False),
        sa.Column('original_freshness_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fridge_items_user_id', 'fridge_items', ['user_id'])
    op.create_index('ix_fridge_items_ingredient_name', 'fridge_items', ['ingredient_name'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_index('ix_fridge_items_ingredient_name', 'fridge_items')
    op.drop_index('ix_fridge_items_user_id', 'fridge_items')
    op.drop_table('fridge_items')

    op.drop_index('ix_meal_slots_date', 'meal_slots')
    op.drop_index('ix_meal_slots_meal_plan_id', 'meal_slots')
    op.drop_table('meal_slots')

    op.drop_index('ix_meal_plans_end_date', 'meal_plans')
    op.drop_index('ix_meal_plans_start_date', 'meal_plans')
    op.drop_index('ix_meal_plans_user_id', 'meal_plans')
    op.drop_table('meal_plans')

    op.drop_index('ix_recipes_meal_type', 'recipes')
    op.drop_index('ix_recipes_name', 'recipes')
    op.drop_table('recipes')

    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS prepstatus')
    op.execute('DROP TYPE IF EXISTS diettype')
