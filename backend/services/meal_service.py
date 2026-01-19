"""
Meal planning service that wraps the engine and provides database persistence.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID
from typing import List, Optional

from backend.db.models import User, Recipe as DBRecipe, MealPlan, MealSlot
from backend.models.schemas import (
    Recipe, MealPlan as SchemaMealPlan, MealSlot as SchemaMealSlot,
    DietType, PrepStatus, Ingredient, COMPOUND_DIET_TYPES
)
from backend.engine.meal_generator import MealGenerator
from backend.errors import NoRecipesAvailableError, InsufficientRecipesError

logger = logging.getLogger(__name__)


def _is_postgresql(db: Session) -> bool:
    """Check if the database is PostgreSQL."""
    dialect_name = db.bind.dialect.name if db.bind else ""
    return dialect_name == "postgresql"


def _filter_recipes_by_diet_tag(db: Session, diet_tag: str) -> List[DBRecipe]:
    """
    Filter recipes by diet tag in a database-agnostic way.

    For compound diet types (e.g., 'low_histamine_low_oxalate'), recipes must
    contain ALL required tags. For simple diet types, recipes must contain
    the single tag.

    Uses PostgreSQL JSONB contains operator when available,
    falls back to fetching all and filtering in Python for SQLite.
    """
    # Check if this is a compound diet type
    required_tags = COMPOUND_DIET_TYPES.get(diet_tag)

    if required_tags:
        # Compound type: recipe must have ALL required tags
        if _is_postgresql(db):
            # PostgreSQL: Chain contains operators for each required tag
            query = db.query(DBRecipe)
            for tag in required_tags:
                query = query.filter(cast(DBRecipe.diet_tags, JSONB).contains([tag]))
            return query.all()
        else:
            # SQLite: Fetch all and filter in Python
            all_recipes = db.query(DBRecipe).all()
            return [
                r for r in all_recipes
                if all(tag in (r.diet_tags or []) for tag in required_tags)
            ]
    else:
        # Simple type: recipe must have the diet type tag
        if _is_postgresql(db):
            # PostgreSQL: Use efficient JSONB contains operator
            return (
                db.query(DBRecipe)
                .filter(cast(DBRecipe.diet_tags, JSONB).contains([diet_tag]))
                .all()
            )
        else:
            # SQLite: Fetch all and filter in Python (JSON is stored as text)
            all_recipes = db.query(DBRecipe).all()
            return [r for r in all_recipes if diet_tag in (r.diet_tags or [])]


def _filter_recipes_by_diet_tag_and_meal_type(
    db: Session, diet_tag: str, meal_type: str
) -> List[DBRecipe]:
    """
    Filter recipes by diet tag and meal type in a database-agnostic way.

    For compound diet types (e.g., 'low_histamine_low_oxalate'), recipes must
    contain ALL required tags. For simple diet types, recipes must contain
    the single tag.
    """
    # Check if this is a compound diet type
    required_tags = COMPOUND_DIET_TYPES.get(diet_tag)

    if required_tags:
        # Compound type: recipe must have ALL required tags
        if _is_postgresql(db):
            query = db.query(DBRecipe).filter(DBRecipe.meal_type == meal_type)
            for tag in required_tags:
                query = query.filter(cast(DBRecipe.diet_tags, JSONB).contains([tag]))
            return query.all()
        else:
            recipes = db.query(DBRecipe).filter(DBRecipe.meal_type == meal_type).all()
            return [
                r for r in recipes
                if all(tag in (r.diet_tags or []) for tag in required_tags)
            ]
    else:
        # Simple type: recipe must have the diet type tag
        if _is_postgresql(db):
            return (
                db.query(DBRecipe)
                .filter(
                    cast(DBRecipe.diet_tags, JSONB).contains([diet_tag]),
                    DBRecipe.meal_type == meal_type,
                )
                .all()
            )
        else:
            recipes = db.query(DBRecipe).filter(DBRecipe.meal_type == meal_type).all()
            return [r for r in recipes if diet_tag in (r.diet_tags or [])]


def db_recipe_to_schema(db_recipe: DBRecipe) -> Recipe:
    """Convert database Recipe to Pydantic schema."""
    return Recipe(
        id=str(db_recipe.id),
        name=db_recipe.name,
        diet_tags=db_recipe.diet_tags,
        meal_type=db_recipe.meal_type,
        ingredients=[Ingredient(**ing) for ing in db_recipe.ingredients],
        prep_steps=db_recipe.prep_steps,
        prep_time_minutes=db_recipe.prep_time_minutes,
        reusability_index=db_recipe.reusability_index,
        servings=db_recipe.servings,
    )


def schema_meal_plan_to_db(schema_plan: SchemaMealPlan, user: User, db: Session) -> MealPlan:
    """Convert Pydantic MealPlan schema to database model."""
    db_plan = MealPlan(
        user_id=user.id,
        diet_type=schema_plan.diet_type,
        start_date=schema_plan.start_date,
        end_date=schema_plan.end_date,
    )

    return db_plan


def db_meal_plan_to_schema(db_plan: MealPlan, db: Session) -> SchemaMealPlan:
    """Convert database MealPlan to Pydantic schema."""
    # Load meals and convert to schema
    meals = []
    for db_slot in db_plan.meals:
        recipe = db_recipe_to_schema(db_slot.recipe)
        meal_slot = SchemaMealSlot(
            date=db_slot.date,
            meal_type=db_slot.meal_type,
            recipe=recipe,
            prep_status=db_slot.prep_status,
            prep_completed_at=db_slot.prep_completed_at,
        )
        meals.append(meal_slot)

    return SchemaMealPlan(
        id=db_plan.id,
        user_id=db_plan.user_id,
        diet_type=db_plan.diet_type,
        start_date=db_plan.start_date,
        end_date=db_plan.end_date,
        meals=meals,
        created_at=db_plan.created_at,
    )


class MealPlanningService:
    """
    Service for meal plan operations.

    Provides methods for generating, retrieving, updating, and deleting meal plans.
    Wraps the meal generation engine and handles database persistence.
    """

    def __init__(self, db: Session):
        """
        Initialize the meal planning service.

        Args:
            db: SQLAlchemy database session for persistence operations.
        """
        self.db = db

    def generate_plan(
        self,
        user: User,
        start_date: date,
        days: int = 3,
        simplified: bool = False,
    ) -> MealPlan:
        """
        Generate a new meal plan for a user.

        Args:
            user: User to generate plan for
            start_date: Start date for the plan
            days: Number of days (default 3)
            simplified: Whether to use simplified recipes

        Returns:
            Created MealPlan database object
        """
        # Load recipes from database (database-agnostic filtering)
        db_recipes = _filter_recipes_by_diet_tag(self.db, user.diet_type.value)

        # Convert to schema recipes
        recipes = [db_recipe_to_schema(r) for r in db_recipes]

        # Get user's dietary exclusions
        dietary_exclusions = user.dietary_exclusions if hasattr(user, 'dietary_exclusions') and user.dietary_exclusions else []

        # Check if we have any recipes before proceeding
        if not recipes:
            logger.warning(
                f"No recipes found for diet type '{user.diet_type.value}' "
                f"(user: {user.id})"
            )
            raise NoRecipesAvailableError(
                diet_type=user.diet_type.value,
                exclusions=dietary_exclusions if dietary_exclusions else None,
            )

        # Generate plan using engine
        generator = MealGenerator(recipes)
        schema_plan = generator.generate_plan(
            user_id=user.id,
            diet_type=user.diet_type,
            start_date=start_date,
            days=days,
            optimize_for_reuse=not simplified,
            dietary_exclusions=dietary_exclusions,
        )

        # Check if the generated plan has any meals
        if not schema_plan.meals:
            logger.warning(
                f"Generated plan has no meals for diet type '{user.diet_type.value}' "
                f"with exclusions {dietary_exclusions} (user: {user.id})"
            )
            raise NoRecipesAvailableError(
                diet_type=user.diet_type.value,
                exclusions=dietary_exclusions if dietary_exclusions else None,
            )

        # Create database plan
        db_plan = MealPlan(
            user_id=user.id,
            diet_type=schema_plan.diet_type,
            start_date=schema_plan.start_date,
            end_date=schema_plan.end_date,
        )
        self.db.add(db_plan)
        self.db.flush()  # Get the ID

        # Create meal slots
        for schema_meal in schema_plan.meals:
            # Find recipe in database by name
            db_recipe = next((r for r in db_recipes if r.name == schema_meal.recipe.name), None)
            if db_recipe:
                db_slot = MealSlot(
                    meal_plan_id=db_plan.id,
                    recipe_id=db_recipe.id,
                    date=schema_meal.date,
                    meal_type=schema_meal.meal_type,
                    prep_status=schema_meal.prep_status,
                )
                self.db.add(db_slot)

        self.db.commit()
        self.db.refresh(db_plan)

        return db_plan

    def get_plan(self, plan_id: UUID, user: User) -> Optional[MealPlan]:
        """
        Get a meal plan by ID for a specific user.

        Args:
            plan_id: Plan UUID
            user: User who owns the plan

        Returns:
            MealPlan or None if not found
        """
        return (
            self.db.query(MealPlan)
            .filter(MealPlan.id == plan_id, MealPlan.user_id == user.id)
            .first()
        )

    def get_user_plans(
        self,
        user: User,
        limit: int = 10,
        skip: int = 0,
    ) -> List[MealPlan]:
        """
        Get all meal plans for a user.

        Args:
            user: User to get plans for
            limit: Maximum number of plans to return
            skip: Number of plans to skip

        Returns:
            List of MealPlan objects
        """
        return (
            self.db.query(MealPlan)
            .filter(MealPlan.user_id == user.id)
            .order_by(MealPlan.created_at.desc())
            .limit(limit)
            .offset(skip)
            .all()
        )

    def count_user_plans(self, user: User) -> int:
        """
        Count the total number of meal plans for a user.

        Args:
            user: User to count plans for

        Returns:
            Total number of meal plans the user has
        """
        return self.db.query(MealPlan).filter(MealPlan.user_id == user.id).count()

    def update_prep_status(
        self,
        plan_id: UUID,
        target_date: date,
        meal_type: str,
        status: PrepStatus,
        user: User,
    ) -> Optional[MealSlot]:
        """
        Update the prep status of a specific meal.

        Args:
            plan_id: Plan UUID
            target_date: Date of the meal
            meal_type: Type of meal (breakfast, lunch, dinner)
            status: New prep status
            user: User who owns the plan

        Returns:
            Updated MealSlot or None if not found
        """
        # Verify plan belongs to user
        plan = self.get_plan(plan_id, user)
        if not plan:
            return None

        # Find and update meal slot
        meal_slot = (
            self.db.query(MealSlot)
            .filter(
                MealSlot.meal_plan_id == plan_id,
                MealSlot.date == target_date,
                MealSlot.meal_type == meal_type,
            )
            .first()
        )

        if meal_slot:
            meal_slot.prep_status = status
            if status == PrepStatus.DONE:
                meal_slot.prep_completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(meal_slot)

        return meal_slot

    def delete_plan(self, plan_id: UUID, user: User) -> bool:
        """
        Delete a meal plan.

        Args:
            plan_id: Plan UUID
            user: User who owns the plan

        Returns:
            True if deleted, False if not found
        """
        plan = self.get_plan(plan_id, user)
        if not plan:
            return False

        self.db.delete(plan)
        self.db.commit()
        return True

    def swap_meal(
        self,
        plan_id: UUID,
        target_date: date,
        meal_type: str,
        new_recipe_id: UUID,
        user: User,
    ) -> Optional[MealSlot]:
        """
        Swap a meal's recipe with a different recipe.

        Args:
            plan_id: Plan UUID
            target_date: Date of the meal to swap
            meal_type: Type of meal (breakfast, lunch, dinner)
            new_recipe_id: UUID of the new recipe
            user: User who owns the plan

        Returns:
            Updated MealSlot or None if not found
        """
        # Verify plan belongs to user
        plan = self.get_plan(plan_id, user)
        if not plan:
            return None

        # Find the meal slot
        meal_slot = (
            self.db.query(MealSlot)
            .filter(
                MealSlot.meal_plan_id == plan_id,
                MealSlot.date == target_date,
                MealSlot.meal_type == meal_type,
            )
            .first()
        )

        if not meal_slot:
            return None

        # Verify the new recipe exists
        new_recipe = self.db.query(DBRecipe).filter(DBRecipe.id == new_recipe_id).first()
        if not new_recipe:
            return None

        # Update the meal slot with the new recipe
        meal_slot.recipe_id = new_recipe_id
        # Reset prep status when swapping
        meal_slot.prep_status = PrepStatus.PENDING
        meal_slot.prep_completed_at = None

        self.db.commit()
        self.db.refresh(meal_slot)

        return meal_slot

    def get_compatible_recipes(
        self,
        user: User,
        meal_type: str,
    ) -> List[DBRecipe]:
        """
        Get recipes compatible with user's diet for a specific meal type.

        Args:
            user: User to get recipes for
            meal_type: Type of meal (breakfast, lunch, dinner)

        Returns:
            List of compatible Recipe database objects
        """
        # Database-agnostic filtering by diet tag and meal type
        recipes = _filter_recipes_by_diet_tag_and_meal_type(
            self.db, user.diet_type.value, meal_type
        )

        # Filter out recipes with user's excluded ingredients
        dietary_exclusions = user.dietary_exclusions if hasattr(user, 'dietary_exclusions') and user.dietary_exclusions else []
        if dietary_exclusions:
            filtered_recipes = []
            for recipe in recipes:
                recipe_ingredients = [ing.get('name', '').lower() for ing in recipe.ingredients]
                has_excluded = any(
                    exclusion.lower() in ingredient
                    for exclusion in dietary_exclusions
                    for ingredient in recipe_ingredients
                )
                if not has_excluded:
                    filtered_recipes.append(recipe)
            return filtered_recipes

        return recipes

    def duplicate_plan(
        self,
        plan_id: UUID,
        new_start_date: date,
        user: User,
    ) -> Optional[MealPlan]:
        """
        Duplicate an existing meal plan to a new date range.

        Creates a copy of the plan with all meal slots, adjusting dates
        relative to the new start date. All prep statuses are reset to PENDING.

        Args:
            plan_id: UUID of the plan to duplicate
            new_start_date: Start date for the duplicated plan
            user: User who owns the plan

        Returns:
            New MealPlan database object, or None if source plan not found
        """
        # Get the source plan
        source_plan = self.get_plan(plan_id, user)
        if not source_plan:
            return None

        # Calculate date offset (difference between old and new start dates)
        date_offset = new_start_date - source_plan.start_date

        # Calculate new end date
        new_end_date = source_plan.end_date + date_offset

        # Create new plan
        new_plan = MealPlan(
            user_id=user.id,
            diet_type=source_plan.diet_type,
            start_date=new_start_date,
            end_date=new_end_date,
        )
        self.db.add(new_plan)
        self.db.flush()  # Get the ID

        # Duplicate all meal slots with adjusted dates
        for source_slot in source_plan.meals:
            new_slot = MealSlot(
                meal_plan_id=new_plan.id,
                recipe_id=source_slot.recipe_id,
                date=source_slot.date + date_offset,
                meal_type=source_slot.meal_type,
                prep_status=PrepStatus.PENDING,  # Reset prep status
                prep_completed_at=None,
            )
            self.db.add(new_slot)

        self.db.commit()
        self.db.refresh(new_plan)

        return new_plan
