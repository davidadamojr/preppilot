"""
Freshness tracking system for ingredients.
Monitors ingredient decay and provides alerts for expiring items.
"""
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Tuple, Any
from uuid import UUID

from backend.models.schemas import (
    FridgeState, FridgeItem, Ingredient, MealPlan, PrepStatus
)
from backend.engine.quantity_utils import combine_quantities


class FreshnessTracker:
    """Track ingredient freshness and decay over time."""

    def __init__(self):
        """Initialize freshness tracker."""
        self.fridge_states: Dict[UUID, FridgeState] = {}

    def create_fridge_state(self, user_id: UUID) -> FridgeState:
        """
        Create a new fridge state for a user.

        Args:
            user_id: User identifier

        Returns:
            New empty fridge state
        """
        fridge = FridgeState(user_id=user_id, items=[])
        self.fridge_states[user_id] = fridge
        return fridge

    def get_fridge_state(self, user_id: UUID) -> FridgeState | None:
        """Get current fridge state for user."""
        return self.fridge_states.get(user_id)

    def generate_shopping_list(self, meal_plan: MealPlan) -> Dict[str, Tuple[str, int]]:
        """
        Generate a shopping list from a meal plan.
        Combines quantities for duplicate ingredients.

        Args:
            meal_plan: Meal plan to generate shopping list from

        Returns:
            Dict mapping ingredient name to (combined_quantity, freshness_days)
        """
        # Aggregate all ingredients from meal plan
        # Key: ingredient name -> value: (total_quantity, min_freshness_days)
        shopping_list: Dict[str, Tuple[str, int]] = {}

        for meal_slot in meal_plan.meals:
            for ingredient in meal_slot.recipe.ingredients:
                name = ingredient.name.lower()

                if name in shopping_list:
                    # Combine quantities
                    existing_qty, existing_freshness = shopping_list[name]
                    combined_qty = combine_quantities(existing_qty, ingredient.quantity)

                    # Use the shorter freshness window (most conservative)
                    min_freshness = min(existing_freshness, ingredient.freshness_days)

                    shopping_list[name] = (combined_qty, min_freshness)
                else:
                    shopping_list[name] = (ingredient.quantity, ingredient.freshness_days)

        return shopping_list

    def stock_fridge_from_shopping(
        self,
        user_id: UUID,
        shopping_list: Dict[str, Tuple[str, int]],
        purchase_date: date = None
    ) -> FridgeState:
        """
        Stock fridge after user completes shopping.
        This should be called AFTER user has actually purchased ingredients.

        Args:
            user_id: User identifier
            shopping_list: Dict of ingredient_name -> (quantity, freshness_days)
            purchase_date: Date ingredients were purchased (defaults to today)

        Returns:
            Updated fridge state
        """
        if purchase_date is None:
            purchase_date = date.today()

        fridge = self.get_fridge_state(user_id)
        if fridge is None:
            fridge = self.create_fridge_state(user_id)

        # Add each ingredient to fridge
        for ingredient_name, (quantity, freshness_days) in shopping_list.items():
            fridge_item = FridgeItem(
                ingredient_name=ingredient_name,
                quantity=quantity,
                days_remaining=freshness_days,
                added_date=purchase_date,
                original_freshness_days=freshness_days
            )
            fridge.add_item(fridge_item)

        fridge.last_updated = datetime.now(timezone.utc)
        return fridge

    def stock_fridge_from_plan(
        self,
        user_id: UUID,
        meal_plan: MealPlan,
        purchase_date: date = None
    ) -> FridgeState:
        """
        Convenience method: Generate shopping list from plan and stock fridge.
        Use this when user has shopped for and received all ingredients in the plan.

        Args:
            user_id: User identifier
            meal_plan: Meal plan containing ingredients
            purchase_date: Date ingredients were purchased (defaults to today)

        Returns:
            Updated fridge state
        """
        shopping_list = self.generate_shopping_list(meal_plan)
        return self.stock_fridge_from_shopping(user_id, shopping_list, purchase_date)

    def apply_daily_decay(self, user_id: UUID, current_date: date = None) -> FridgeState:
        """
        Apply daily freshness decay to all items.

        Args:
            user_id: User identifier
            current_date: Current date for decay calculation

        Returns:
            Updated fridge state
        """
        if current_date is None:
            current_date = date.today()

        fridge = self.get_fridge_state(user_id)
        if fridge is None:
            return None

        for item in fridge.items:
            days_since_added = (current_date - item.added_date).days
            item.days_remaining = max(0, item.original_freshness_days - days_since_added)

        # Remove expired items (days_remaining <= 0)
        fridge.items = [item for item in fridge.items if item.days_remaining > 0]

        fridge.last_updated = datetime.now(timezone.utc)
        return fridge

    def remove_used_ingredients(
        self,
        user_id: UUID,
        ingredients: List[Ingredient]
    ) -> FridgeState:
        """
        Remove ingredients that have been used in cooking.

        Args:
            user_id: User identifier
            ingredients: List of ingredients to remove

        Returns:
            Updated fridge state
        """
        fridge = self.get_fridge_state(user_id)
        if fridge is None:
            return None

        for ingredient in ingredients:
            item = fridge.get_item(ingredient.name)
            if item:
                fridge.items.remove(item)

        fridge.last_updated = datetime.now(timezone.utc)
        return fridge

    def mark_meal_prepared(
        self,
        user_id: UUID,
        meal_plan: MealPlan,
        meal_date: date,
        meal_type: str
    ) -> Tuple[FridgeState, bool]:
        """
        Mark a meal as prepared and remove its ingredients from fridge.

        Args:
            user_id: User identifier
            meal_plan: Meal plan containing the meal
            meal_date: Date of the meal
            meal_type: Type of meal (breakfast, lunch, dinner)

        Returns:
            Tuple of (updated fridge state, success boolean)
        """
        # Find the meal
        target_meal = None
        for meal_slot in meal_plan.meals:
            if meal_slot.date == meal_date and meal_slot.meal_type == meal_type:
                target_meal = meal_slot
                break

        if target_meal is None:
            return self.get_fridge_state(user_id), False

        # Remove ingredients
        fridge = self.remove_used_ingredients(
            user_id,
            target_meal.recipe.ingredients
        )

        # Update meal status
        target_meal.prep_status = PrepStatus.DONE
        target_meal.prep_completed_at = datetime.now(timezone.utc)

        return fridge, True

    def get_expiring_soon(
        self,
        user_id: UUID,
        days_threshold: int = 2
    ) -> List[FridgeItem]:
        """
        Get ingredients expiring within threshold.

        Args:
            user_id: User identifier
            days_threshold: Number of days to consider "expiring soon"

        Returns:
            List of items expiring soon
        """
        fridge = self.get_fridge_state(user_id)
        if fridge is None:
            return []

        return fridge.get_expiring_soon(days_threshold)

    def get_priority_ingredients(
        self,
        user_id: UUID,
        urgency_days: int = 1
    ) -> List[str]:
        """
        Get list of ingredient names that need immediate use.

        Args:
            user_id: User identifier
            urgency_days: Days threshold for urgency

        Returns:
            List of ingredient names needing immediate attention
        """
        expiring = self.get_expiring_soon(user_id, urgency_days)
        return [item.ingredient_name for item in expiring]

    def check_ingredient_availability(
        self,
        user_id: UUID,
        ingredients: List[Ingredient]
    ) -> Dict[str, bool]:
        """
        Check which ingredients are available in fridge.

        Args:
            user_id: User identifier
            ingredients: List of ingredients to check

        Returns:
            Dict mapping ingredient name to availability (True/False)
        """
        fridge = self.get_fridge_state(user_id)
        if fridge is None:
            return {ing.name: False for ing in ingredients}

        availability = {}
        for ingredient in ingredients:
            item = fridge.get_item(ingredient.name)
            availability[ingredient.name] = item is not None and item.days_remaining > 0

        return availability

    def get_freshness_summary(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get summary of fridge freshness state.

        Args:
            user_id: User identifier

        Returns:
            Dict with freshness statistics
        """
        fridge = self.get_fridge_state(user_id)
        if fridge is None:
            return {
                "total_items": 0,
                "expiring_today": 0,
                "expiring_tomorrow": 0,
                "expiring_within_3_days": 0,
                "fresh_items": 0
            }

        total = len(fridge.items)
        expiring_today = len([i for i in fridge.items if i.days_remaining == 0])
        expiring_tomorrow = len([i for i in fridge.items if i.days_remaining == 1])
        expiring_3_days = len([i for i in fridge.items if 0 < i.days_remaining <= 3])
        fresh = len([i for i in fridge.items if i.days_remaining > 3])

        return {
            "total_items": total,
            "expiring_today": expiring_today,
            "expiring_tomorrow": expiring_tomorrow,
            "expiring_within_3_days": expiring_3_days,
            "fresh_items": fresh,
            "last_updated": fridge.last_updated.isoformat()
        }
