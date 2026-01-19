"""
Meal plan generator for diet-compliant meals.
Generates 3-day meal plans optimized for ingredient reuse and freshness.
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Union
from uuid import UUID

from backend.models.schemas import (
    Recipe, MealPlan, MealSlot, DietType, PrepStatus, EXCLUSION_CATEGORIES,
    COMPOUND_DIET_TYPES
)


class MealGenerator:
    """Generate diet-compliant meal plans."""

    def __init__(self, recipe_source: Union[Path, List[Recipe]] = None):
        """
        Initialize meal generator with recipe database.

        Args:
            recipe_source: Either a Path to recipe JSON file or a list of Recipe objects
        """
        if recipe_source is None:
            recipe_source = Path(__file__).parent.parent / "data" / "low_histamine_recipes.json"

        # Check if recipe_source is a list of recipes or a path
        if isinstance(recipe_source, list):
            self.recipes = recipe_source
        else:
            self.recipes = self._load_recipes(recipe_source)

        self.recipes_by_type: Dict[str, List[Recipe]] = self._index_recipes_by_type()

    def _load_recipes(self, recipe_file: Path) -> List[Recipe]:
        """Load recipes from JSON file."""
        with open(recipe_file, 'r') as f:
            data = json.load(f)

        recipes = []
        for recipe_data in data['recipes']:
            recipes.append(Recipe(**recipe_data))

        return recipes

    def _index_recipes_by_type(self) -> Dict[str, List[Recipe]]:
        """Index recipes by meal type for faster lookup."""
        index = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snack': []
        }

        for recipe in self.recipes:
            if recipe.meal_type in index:
                index[recipe.meal_type].append(recipe)

        return index

    def _expand_exclusions(self, exclusions: List[str]) -> set:
        """
        Expand category exclusions to include all ingredients in that category.

        Args:
            exclusions: List of ingredient names and/or categories

        Returns:
            Set of all excluded ingredient names (expanded from categories)
        """
        expanded = set()

        for exclusion in exclusions:
            exclusion_lower = exclusion.lower().strip()
            # Add the exclusion itself
            expanded.add(exclusion_lower)

            # If it's a category, add all ingredients in that category
            if exclusion_lower in EXCLUSION_CATEGORIES:
                expanded.update(EXCLUSION_CATEGORIES[exclusion_lower])

        return expanded

    def _recipe_contains_exclusions(
        self,
        recipe: Recipe,
        expanded_exclusions: set
    ) -> bool:
        """
        Check if a recipe contains any excluded ingredients.

        Args:
            recipe: Recipe to check
            expanded_exclusions: Set of all excluded ingredient names

        Returns:
            True if recipe contains any exclusions, False otherwise
        """
        if not expanded_exclusions:
            return False

        recipe_ingredients = {ing.name.lower().strip() for ing in recipe.ingredients}

        # Check for any overlap between recipe ingredients and exclusions
        return bool(recipe_ingredients & expanded_exclusions)

    def _filter_by_exclusions(
        self,
        recipes: List[Recipe],
        exclusions: List[str]
    ) -> List[Recipe]:
        """
        Filter out recipes containing excluded ingredients or categories.

        Args:
            recipes: List of recipes to filter
            exclusions: List of excluded ingredients or categories

        Returns:
            Recipes that do not contain any exclusions
        """
        if not exclusions:
            return recipes

        expanded_exclusions = self._expand_exclusions(exclusions)

        return [
            recipe for recipe in recipes
            if not self._recipe_contains_exclusions(recipe, expanded_exclusions)
        ]

    def _filter_by_diet(
        self,
        recipes: List[Recipe],
        diet_type: str,
        exclusions: List[str] = None
    ) -> List[Recipe]:
        """
        Filter recipes compatible with diet type and exclusions.

        Args:
            recipes: List of recipes to filter
            diet_type: Diet type tag to match
            exclusions: Optional list of excluded ingredients/categories

        Returns:
            Filtered recipes matching diet and without exclusions
        """
        # Check if this is a compound diet type
        required_tags = COMPOUND_DIET_TYPES.get(diet_type)

        if required_tags:
            # Compound type: recipe must have ALL required tags
            diet_filtered = [
                r for r in recipes
                if all(tag in r.diet_tags for tag in required_tags)
            ]
        else:
            # Simple type: recipe must have the diet type tag
            diet_filtered = [r for r in recipes if diet_type in r.diet_tags]

        # Then filter by exclusions if provided
        if exclusions:
            return self._filter_by_exclusions(diet_filtered, exclusions)

        return diet_filtered

    def _calculate_ingredient_overlap(self, recipe1: Recipe, recipe2: Recipe) -> float:
        """
        Calculate ingredient overlap between two recipes.
        Returns score 0-1 where higher means more shared ingredients.
        """
        ingredients1 = {ing.name for ing in recipe1.ingredients}
        ingredients2 = {ing.name for ing in recipe2.ingredients}

        if not ingredients1 or not ingredients2:
            return 0.0

        overlap = len(ingredients1 & ingredients2)
        total = len(ingredients1 | ingredients2)

        return overlap / total if total > 0 else 0.0

    def _select_optimized_recipes(
        self,
        meal_type: str,
        diet_type: str,
        count: int,
        prioritize_reuse: bool = True,
        exclusions: List[str] = None,
        exclude_recipe_ids: set = None
    ) -> List[Recipe]:
        """
        Select recipes with optimized ingredient reuse.

        Args:
            meal_type: breakfast, lunch, or dinner
            diet_type: diet compliance tag
            count: number of recipes to select
            prioritize_reuse: whether to optimize for ingredient overlap
            exclusions: Optional list of excluded ingredients/categories
            exclude_recipe_ids: Recipe IDs to exclude (for deduplication across plan)

        Returns:
            List of selected recipes
        """
        candidates = self._filter_by_diet(
            self.recipes_by_type.get(meal_type, []),
            diet_type,
            exclusions
        )

        if not candidates:
            return []

        # Exclude already-selected recipes if possible
        if exclude_recipe_ids:
            filtered_candidates = [c for c in candidates if c.id not in exclude_recipe_ids]
            # Only use filtered list if it has enough recipes; otherwise allow duplicates
            if len(filtered_candidates) >= count:
                candidates = filtered_candidates

        if len(candidates) <= count:
            return candidates[:count]

        if not prioritize_reuse:
            return random.sample(candidates, count)

        # Greedy selection: pick first recipe, then pick subsequent ones
        # that maximize ingredient overlap with already selected
        selected = [random.choice(candidates)]
        candidates = [c for c in candidates if c.id != selected[0].id]

        while len(selected) < count and candidates:
            # Score each candidate by overlap with all selected recipes
            scores = []
            for candidate in candidates:
                # Average overlap with all selected recipes
                # Weight by reusability index
                overlap_scores = [
                    self._calculate_ingredient_overlap(candidate, s)
                    for s in selected
                ]
                avg_overlap = sum(overlap_scores) / len(overlap_scores)

                # Combine overlap with recipe's reusability index
                final_score = (avg_overlap * 0.7) + (candidate.reusability_index * 0.3)
                scores.append((final_score, candidate))

            # Select recipe with highest score
            scores.sort(reverse=True, key=lambda x: x[0])
            best_recipe = scores[0][1]

            selected.append(best_recipe)
            candidates = [c for c in candidates if c.id != best_recipe.id]

        return selected

    def generate_plan(
        self,
        user_id: UUID,
        diet_type: DietType,
        start_date: date = None,
        days: int = 3,
        optimize_for_reuse: bool = True,
        dietary_exclusions: List[str] = None
    ) -> MealPlan:
        """
        Generate a meal plan for specified days.

        Args:
            user_id: User identifier
            diet_type: Diet compliance type
            start_date: Start date of plan (defaults to today)
            days: Number of days to plan (default 3)
            optimize_for_reuse: Whether to optimize for ingredient reuse
            dietary_exclusions: Optional list of excluded ingredients/categories

        Returns:
            Complete meal plan with schedule
        """
        if start_date is None:
            start_date = date.today()

        end_date = start_date + timedelta(days=days - 1)

        # Generate meals for each day
        meals = []

        # Track selected recipes per meal type to avoid duplicates when possible
        selected_by_meal_type = {
            'breakfast': set(),
            'lunch': set(),
            'dinner': set()
        }

        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)

            # Select one recipe per meal type per day
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                recipes = self._select_optimized_recipes(
                    meal_type=meal_type,
                    diet_type=diet_type.value,
                    count=1,
                    prioritize_reuse=optimize_for_reuse,
                    exclusions=dietary_exclusions,
                    exclude_recipe_ids=selected_by_meal_type[meal_type]
                )

                if recipes:
                    selected_recipe = recipes[0]
                    selected_by_meal_type[meal_type].add(selected_recipe.id)

                    meal_slot = MealSlot(
                        date=current_date,
                        meal_type=meal_type,
                        recipe=selected_recipe,
                        prep_status=PrepStatus.PENDING
                    )
                    meals.append(meal_slot)

        # Create meal plan
        plan = MealPlan(
            user_id=user_id,
            diet_type=diet_type,
            start_date=start_date,
            end_date=end_date,
            meals=meals
        )

        return plan

    def get_recipes_by_diet(self, diet_type: str) -> List[Recipe]:
        """Get all recipes compatible with a diet type."""
        return self._filter_by_diet(self.recipes, diet_type)

    def get_recipe_by_id(self, recipe_id: str) -> Recipe | None:
        """Get specific recipe by ID."""
        for recipe in self.recipes:
            if recipe.id == recipe_id:
                return recipe
        return None

    def suggest_simplified_alternatives(
        self,
        recipe: Recipe,
        max_prep_time: int = 20,
        exclusions: List[str] = None
    ) -> List[Recipe]:
        """
        Suggest simpler alternative recipes.

        Args:
            recipe: Original recipe
            max_prep_time: Maximum prep time for alternatives
            exclusions: Optional list of excluded ingredients/categories

        Returns:
            List of simpler alternatives
        """
        # Find recipes of same type, same diet, with shorter prep time
        candidates = [
            r for r in self.recipes_by_type.get(recipe.meal_type, [])
            if r.prep_time_minutes <= max_prep_time
            and any(tag in r.diet_tags for tag in recipe.diet_tags)
            and r.id != recipe.id
        ]

        # Filter by exclusions if provided
        if exclusions:
            candidates = self._filter_by_exclusions(candidates, exclusions)

        # Sort by prep time (shortest first)
        candidates.sort(key=lambda r: r.prep_time_minutes)

        return candidates[:3]
