"""add_performance_indexes

Revision ID: add_performance_indexes
Revises: add_role_to_user
Create Date: 2025-12-20

Adds composite indexes for common query patterns to improve performance:
- MealSlot: (meal_plan_id, date) for efficient meal queries by plan and date
- FridgeItem: (user_id, days_remaining) for expiring items queries
- Recipe: GIN index on diet_tags for efficient JSON array containment queries
- MealPlan: (user_id, created_at) for listing user's plans ordered by creation
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = 'add_role_to_user'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite and GIN indexes for query performance."""
    # MealSlot: composite index for querying meals by plan and date
    # Common query: "get all meals for a plan on a specific date"
    op.create_index(
        'ix_meal_slots_meal_plan_id_date',
        'meal_slots',
        ['meal_plan_id', 'date'],
        unique=False
    )

    # FridgeItem: composite index for expiring items queries
    # Common query: "get expiring items for a user" (sorted by days_remaining)
    op.create_index(
        'ix_fridge_items_user_id_days_remaining',
        'fridge_items',
        ['user_id', 'days_remaining'],
        unique=False
    )

    # Recipe: GIN index on diet_tags for efficient JSON array containment queries
    # Common query: "find recipes with specific diet tag" using @> operator
    # PostgreSQL-specific: uses GIN index for JSONB containment
    # Note: diet_tags is JSON type, so we cast to jsonb for GIN index support
    op.execute(
        'CREATE INDEX ix_recipes_diet_tags_gin ON recipes USING GIN ((diet_tags::jsonb))'
    )

    # MealPlan: composite index for listing user's plans by creation date
    # Common query: "get user's plans ordered by created_at DESC"
    op.create_index(
        'ix_meal_plans_user_id_created_at',
        'meal_plans',
        ['user_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """Remove the performance indexes."""
    op.drop_index('ix_meal_plans_user_id_created_at', table_name='meal_plans')
    op.execute('DROP INDEX IF EXISTS ix_recipes_diet_tags_gin')
    op.drop_index('ix_fridge_items_user_id_days_remaining', table_name='fridge_items')
    op.drop_index('ix_meal_slots_meal_plan_id_date', table_name='meal_slots')
