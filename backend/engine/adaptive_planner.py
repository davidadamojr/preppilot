"""
Adaptive meal planning engine - THE BRAIN.
Intelligently replans meals when preps are missed or delayed.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

from backend.models.schemas import (
    MealPlan, MealSlot, Recipe, PrepStatus, DietType,
    AdaptiveEngineInput, AdaptiveEngineOutput, AdaptationReason,
    FridgeState, FridgeItem
)
from backend.engine.meal_generator import MealGenerator
from backend.engine.freshness_tracker import FreshnessTracker


class AdaptivePlanner:
    """
    The adaptive planning engine that replans meals after missed preps.

    Core principles:
    1. Detect missed/delayed preps
    2. Prioritize perishable ingredients
    3. Generate substitutions or simplified meals
    4. Preserve continuity (favor reuse over regeneration)
    5. Always explain changes transparently
    """

    def __init__(
        self,
        meal_generator: MealGenerator,
        freshness_tracker: FreshnessTracker
    ):
        """
        Initialize adaptive planner.

        Args:
            meal_generator: Meal generator for recipe selection
            freshness_tracker: Freshness tracker for ingredient monitoring
        """
        self.meal_generator = meal_generator
        self.freshness_tracker = freshness_tracker

    def detect_missed_preps(
        self,
        meal_plan: MealPlan,
        current_date: date
    ) -> List[date]:
        """
        Detect missed or overdue prep dates.

        Args:
            meal_plan: Current meal plan
            current_date: Today's date

        Returns:
            List of dates with missed preps
        """
        return meal_plan.get_missed_preps(current_date)

    def analyze_fridge_situation(
        self,
        user_id: UUID,
        current_date: date
    ) -> Dict[str, Any]:
        """
        Analyze current fridge state for planning decisions.

        Args:
            user_id: User identifier
            current_date: Current date

        Returns:
            Dict with fridge analysis
        """
        # Apply decay to get current state
        fridge = self.freshness_tracker.apply_daily_decay(user_id, current_date)

        if fridge is None:
            return {
                "has_ingredients": False,
                "expiring_urgent": [],
                "expiring_soon": [],
                "fresh_items": []
            }

        # Categorize by urgency
        urgent = [item for item in fridge.items if item.days_remaining <= 1]
        soon = [item for item in fridge.items if 1 < item.days_remaining <= 2]
        fresh = [item for item in fridge.items if item.days_remaining > 2]

        return {
            "has_ingredients": len(fridge.items) > 0,
            "expiring_urgent": urgent,
            "expiring_soon": soon,
            "fresh_items": fresh,
            "total_items": len(fridge.items)
        }

    def find_recipes_using_ingredients(
        self,
        target_ingredients: List[str],
        diet_type: str,
        meal_type: Optional[str] = None,
        max_results: int = 3,
        exclusions: List[str] = None
    ) -> List[Recipe]:
        """
        Find recipes that use specific ingredients (prioritize perishables).

        Args:
            target_ingredients: List of ingredient names to prioritize
            diet_type: Diet compliance type
            meal_type: Optional meal type filter
            max_results: Maximum number of recipes to return
            exclusions: Optional list of excluded ingredients/categories

        Returns:
            List of recipes sorted by ingredient match score
        """
        all_recipes = self.meal_generator.get_recipes_by_diet(diet_type)

        # Filter by exclusions if provided
        if exclusions:
            all_recipes = self.meal_generator._filter_by_exclusions(all_recipes, exclusions)

        if meal_type:
            all_recipes = [r for r in all_recipes if r.meal_type == meal_type]

        # Score recipes by how many target ingredients they use
        scored_recipes = []
        for recipe in all_recipes:
            recipe_ingredients = {ing.name.lower() for ing in recipe.ingredients}
            target_set = {ing.lower() for ing in target_ingredients}

            matches = len(recipe_ingredients & target_set)
            if matches > 0:
                scored_recipes.append((matches, recipe))

        # Sort by score (descending)
        scored_recipes.sort(reverse=True, key=lambda x: x[0])

        return [recipe for _, recipe in scored_recipes[:max_results]]

    def generate_simplified_meal(
        self,
        original_meal: MealSlot,
        max_prep_time: int = 20,
        exclusions: List[str] = None
    ) -> Optional[Recipe]:
        """
        Find a simpler alternative to a meal.

        Args:
            original_meal: Original meal slot
            max_prep_time: Maximum prep time for simplified version
            exclusions: Optional list of excluded ingredients/categories

        Returns:
            Simplified recipe or None
        """
        alternatives = self.meal_generator.suggest_simplified_alternatives(
            original_meal.recipe,
            max_prep_time,
            exclusions
        )

        return alternatives[0] if alternatives else None

    def adapt_plan(
        self,
        input_data: AdaptiveEngineInput
    ) -> AdaptiveEngineOutput:
        """
        Main adaptive planning algorithm.
        Replans meals after missed preps, prioritizing freshness and continuity.

        Args:
            input_data: Adaptive engine input with current state

        Returns:
            Adaptive engine output with new plan and explanations
        """
        current_plan = input_data.current_plan
        current_date = input_data.current_date
        user_id = input_data.user_id

        # Initialize outputs
        adaptations: List[AdaptationReason] = []
        grocery_adjustments: List[str] = []
        priority_ingredients: List[str] = []

        # Analyze current fridge situation
        fridge_analysis = self.analyze_fridge_situation(user_id, current_date)

        # Get pending meals (not yet completed)
        pending_meals = current_plan.get_pending_meals()

        # Filter to future meals only
        future_meals = [m for m in pending_meals if m.date >= current_date]

        # If no missed preps and no expiring ingredients, return original plan
        if not input_data.missed_preps and not fridge_analysis["expiring_urgent"]:
            return AdaptiveEngineOutput(
                new_plan=current_plan,
                adaptation_summary=[],
                grocery_adjustments=[],
                priority_ingredients=[],
                estimated_recovery_time_minutes=0
            )

        # ADAPTATION STRATEGY:
        # 1. Identify expiring ingredients that need immediate use
        # 2. Find upcoming meals that can use those ingredients
        # 3. Reorder meals to prioritize perishables
        # 4. Simplify meals if user is behind schedule
        # 5. Generate recovery meals for catch-up

        urgent_ingredients = [item.ingredient_name for item in fridge_analysis["expiring_urgent"]]
        soon_ingredients = [item.ingredient_name for item in fridge_analysis["expiring_soon"]]

        priority_ingredients = urgent_ingredients + soon_ingredients

        # Start building new meal schedule
        new_meals: List[MealSlot] = []
        recovery_time = 0

        # Process future meals
        for i, meal in enumerate(sorted(future_meals, key=lambda m: (m.date, m.meal_type))):
            adapted_meal = meal.model_copy(deep=True)

            # Strategy 1: If we have urgent expiring ingredients, try to use them
            if urgent_ingredients and meal.date == current_date:
                # Try to find a recipe that uses expiring ingredients
                better_recipes = self.find_recipes_using_ingredients(
                    urgent_ingredients,
                    input_data.diet_type.value,
                    meal.meal_type,
                    max_results=1,
                    exclusions=input_data.dietary_exclusions
                )

                if better_recipes:
                    original_name = adapted_meal.recipe.name
                    adapted_meal.recipe = better_recipes[0]

                    adaptations.append(AdaptationReason(
                        type="substitute",
                        affected_date=meal.date,
                        original_meal=original_name,
                        new_meal=adapted_meal.recipe.name,
                        reason=f"Substituted to use expiring ingredients: {', '.join(urgent_ingredients[:2])}"
                    ))

                    # Remove used urgent ingredients from list
                    for ing in adapted_meal.recipe.ingredients:
                        if ing.name in urgent_ingredients:
                            urgent_ingredients.remove(ing.name)

            # Strategy 2: If user is behind (missed preps), simplify upcoming meals
            if input_data.missed_preps and meal.date <= current_date + timedelta(days=1):
                if meal.recipe.prep_time_minutes > 25:
                    simplified = self.generate_simplified_meal(
                        meal,
                        max_prep_time=20,
                        exclusions=input_data.dietary_exclusions
                    )

                    if simplified:
                        original_name = adapted_meal.recipe.name
                        adapted_meal.recipe = simplified
                        recovery_time += simplified.prep_time_minutes

                        adaptations.append(AdaptationReason(
                            type="simplify",
                            affected_date=meal.date,
                            original_meal=original_name,
                            new_meal=adapted_meal.recipe.name,
                            reason=f"Simplified to faster recipe ({simplified.prep_time_minutes} min) for catch-up"
                        ))
                    else:
                        recovery_time += meal.recipe.prep_time_minutes
                else:
                    recovery_time += meal.recipe.prep_time_minutes

            new_meals.append(adapted_meal)

        # Strategy 3: Handle unused expiring ingredients
        if urgent_ingredients:
            # These ingredients are still expiring but not used in plan
            for ingredient in urgent_ingredients[:3]:  # Limit messaging
                grocery_adjustments.append(
                    f"Warning: {ingredient} expiring soon - consider using immediately or it will spoil"
                )

        # Strategy 4: Missed preps explanation
        if input_data.missed_preps:
            missed_count = len(input_data.missed_preps)
            adaptations.insert(0, AdaptationReason(
                type="reorder",
                affected_date=current_date,
                reason=f"Missed {missed_count} prep day(s) - adjusted schedule for recovery"
            ))

        # Create new meal plan
        new_plan = MealPlan(
            id=current_plan.id,
            user_id=current_plan.user_id,
            diet_type=current_plan.diet_type,
            start_date=current_date,
            end_date=current_date + timedelta(days=2),  # 3-day rolling window
            meals=new_meals
        )

        return AdaptiveEngineOutput(
            new_plan=new_plan,
            adaptation_summary=adaptations,
            grocery_adjustments=grocery_adjustments,
            priority_ingredients=priority_ingredients,
            estimated_recovery_time_minutes=recovery_time
        )

    def extend_plan(
        self,
        current_plan: MealPlan,
        user_id: UUID,
        days_to_add: int = 1,
        dietary_exclusions: List[str] = None
    ) -> MealPlan:
        """
        Extend an existing plan by adding more days.

        Args:
            current_plan: Current meal plan
            user_id: User identifier
            days_to_add: Number of days to extend
            dietary_exclusions: Optional list of excluded ingredients/categories

        Returns:
            Extended meal plan
        """
        new_start = current_plan.end_date + timedelta(days=1)

        extension = self.meal_generator.generate_plan(
            user_id=user_id,
            diet_type=current_plan.diet_type,
            start_date=new_start,
            days=days_to_add,
            dietary_exclusions=dietary_exclusions
        )

        # Combine meals
        combined_meals = current_plan.meals + extension.meals

        return MealPlan(
            id=current_plan.id,
            user_id=current_plan.user_id,
            diet_type=current_plan.diet_type,
            start_date=current_plan.start_date,
            end_date=extension.end_date,
            meals=combined_meals
        )
