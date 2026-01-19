"""
Adaptive planning service that wraps the adaptive engine with database persistence.
"""
from datetime import date
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from backend.db.models import User, MealPlan, MealSlot, Recipe as DBRecipe
from backend.models.schemas import (
    AdaptiveEngineInput, AdaptiveEngineOutput, FridgeState,
    PrepStatus, AdaptationReason
)
from backend.engine.adaptive_planner import AdaptivePlanner
from backend.services.meal_service import db_meal_plan_to_schema, db_recipe_to_schema
from backend.services.fridge_service import FridgeService


class AdaptiveService:
    """
    Service for adaptive meal plan replanning.

    Handles plan adaptations when users miss preps or have expiring ingredients.
    Wraps the adaptive planner engine with database persistence.
    """

    def __init__(self, db: Session):
        """
        Initialize the adaptive service.

        Args:
            db: SQLAlchemy database session for persistence operations.
        """
        self.db = db
        self.fridge_service = FridgeService(db)

    def adapt_plan(
        self,
        user: User,
        plan_id: UUID,
        current_date: date,
    ) -> AdaptiveEngineOutput:
        """
        Adapt a meal plan based on missed preps and fridge state.

        Args:
            user: User who owns the plan
            plan_id: UUID of the plan to adapt
            current_date: Current date for adaptation

        Returns:
            AdaptiveEngineOutput with new plan and adaptation summary
        """
        # Load the current plan
        db_plan = (
            self.db.query(MealPlan)
            .filter(MealPlan.id == plan_id, MealPlan.user_id == user.id)
            .first()
        )

        if not db_plan:
            raise ValueError(f"Plan {plan_id} not found for user")

        # Convert to schema
        current_plan = db_meal_plan_to_schema(db_plan, self.db)

        # Get fridge state
        fridge_state = self.fridge_service.get_fridge_state(user)

        # Identify missed preps
        missed_preps = current_plan.get_missed_preps(current_date)

        # If no missed preps, return current plan
        if not missed_preps:
            return AdaptiveEngineOutput(
                new_plan=current_plan,
                adaptation_summary=[
                    AdaptationReason(
                        type="no_change",
                        affected_date=current_date,
                        reason="No missed preps detected. Plan is on track.",
                    )
                ],
                grocery_adjustments=[],
                priority_ingredients=[],
                estimated_recovery_time_minutes=0,
            )

        # Load all recipes for adaptation
        db_recipes = (
            self.db.query(DBRecipe)
            .filter(DBRecipe.diet_tags.contains([user.diet_type.value]))
            .all()
        )
        recipes = [db_recipe_to_schema(r) for r in db_recipes]

        # Get user's dietary exclusions
        dietary_exclusions = user.dietary_exclusions if hasattr(user, 'dietary_exclusions') and user.dietary_exclusions else []

        # Create adaptive engine input
        engine_input = AdaptiveEngineInput(
            user_id=user.id,
            diet_type=user.diet_type,
            current_plan=current_plan,
            fridge_state=fridge_state,
            missed_preps=missed_preps,
            current_date=current_date,
            dietary_exclusions=dietary_exclusions,
        )

        # Initialize meal generator and freshness tracker
        from backend.engine.meal_generator import MealGenerator
        from backend.engine.freshness_tracker import FreshnessTracker

        meal_generator = MealGenerator(recipes)
        freshness_tracker = FreshnessTracker()

        # Run adaptive planner
        planner = AdaptivePlanner(meal_generator, freshness_tracker)
        output = planner.adapt_plan(engine_input)

        # Persist the adapted plan to database
        self._update_db_plan(db_plan, output.new_plan, db_recipes)

        return output

    def _update_db_plan(
        self,
        db_plan: MealPlan,
        adapted_plan: "SchemaMealPlan",
        db_recipes: List[DBRecipe],
    ):
        """
        Update the database meal plan with adapted plan.

        Args:
            db_plan: Existing database plan
            adapted_plan: New adapted plan schema
            db_recipes: List of available database recipes
        """
        # Remove existing meal slots for dates that changed
        changed_dates = {meal.date for meal in adapted_plan.meals}

        # Delete old slots for changed dates
        self.db.query(MealSlot).filter(
            MealSlot.meal_plan_id == db_plan.id,
            MealSlot.date.in_(changed_dates),
            MealSlot.prep_status != PrepStatus.DONE,  # Don't delete completed meals
        ).delete(synchronize_session=False)

        # Add new meal slots
        for schema_meal in adapted_plan.meals:
            # Skip if this meal is already marked done
            existing_done = (
                self.db.query(MealSlot)
                .filter(
                    MealSlot.meal_plan_id == db_plan.id,
                    MealSlot.date == schema_meal.date,
                    MealSlot.meal_type == schema_meal.meal_type,
                    MealSlot.prep_status == PrepStatus.DONE,
                )
                .first()
            )

            if existing_done:
                continue

            # Find matching recipe in database
            db_recipe = next(
                (r for r in db_recipes if r.name == schema_meal.recipe.name),
                None
            )

            if db_recipe:
                new_slot = MealSlot(
                    meal_plan_id=db_plan.id,
                    recipe_id=db_recipe.id,
                    date=schema_meal.date,
                    meal_type=schema_meal.meal_type,
                    prep_status=schema_meal.prep_status,
                    prep_completed_at=schema_meal.prep_completed_at,
                )
                self.db.add(new_slot)

        # Update plan dates if needed
        db_plan.start_date = adapted_plan.start_date
        db_plan.end_date = adapted_plan.end_date

        self.db.commit()
        self.db.refresh(db_plan)

    def get_catch_up_suggestions(
        self,
        user: User,
        plan_id: UUID,
        current_date: date,
    ) -> dict:
        """
        Get catch-up suggestions without modifying the plan.

        Args:
            user: User who owns the plan
            plan_id: UUID of the plan
            current_date: Current date

        Returns:
            Dictionary with suggestions and priority ingredients
        """
        # Load the current plan
        db_plan = (
            self.db.query(MealPlan)
            .filter(MealPlan.id == plan_id, MealPlan.user_id == user.id)
            .first()
        )

        if not db_plan:
            raise ValueError(f"Plan {plan_id} not found for user")

        current_plan = db_meal_plan_to_schema(db_plan, self.db)
        fridge_state = self.fridge_service.get_fridge_state(user)

        # Get expiring items
        expiring_items = self.fridge_service.get_expiring_items(user, days_threshold=2)

        # Get missed preps
        missed_preps = current_plan.get_missed_preps(current_date)

        return {
            "missed_preps": missed_preps,
            "expiring_items": [
                {
                    "name": item.ingredient_name,
                    "days_remaining": item.days_remaining,
                    "quantity": item.quantity,
                }
                for item in expiring_items
            ],
            "pending_meals": [
                {
                    "date": str(meal.date),
                    "meal_type": meal.meal_type,
                    "recipe": meal.recipe.name,
                }
                for meal in current_plan.get_pending_meals()
                if meal.date >= current_date
            ],
            "needs_adaptation": len(missed_preps) > 0,
        }
