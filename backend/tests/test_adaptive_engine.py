"""
Test scenarios for adaptive engine validation.
"""
import pytest
from datetime import date, timedelta
from uuid import uuid4

from backend.models.schemas import DietType, AdaptiveEngineInput, PrepStatus
from backend.engine.meal_generator import MealGenerator
from backend.engine.freshness_tracker import FreshnessTracker
from backend.engine.adaptive_planner import AdaptivePlanner


class TestAdaptiveEngine:
    """Test suite for adaptive meal planning engine."""

    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        meal_generator = MealGenerator()
        freshness_tracker = FreshnessTracker()
        adaptive_planner = AdaptivePlanner(meal_generator, freshness_tracker)

        user_id = uuid4()

        return {
            'meal_generator': meal_generator,
            'freshness_tracker': freshness_tracker,
            'adaptive_planner': adaptive_planner,
            'user_id': user_id
        }

    def test_generate_basic_plan(self, setup):
        """Test basic meal plan generation."""
        meal_generator = setup['meal_generator']
        user_id = setup['user_id']

        plan = meal_generator.generate_plan(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            days=3
        )

        # Should have 3 meals per day (breakfast, lunch, dinner)
        assert len(plan.meals) == 9

        # All meals should be low_histamine compliant
        for meal in plan.meals:
            assert 'low_histamine' in meal.recipe.diet_tags

        # Check date range
        assert (plan.end_date - plan.start_date).days == 2

    def test_shopping_list_generation(self, setup):
        """Test shopping list generation from plan."""
        meal_generator = setup['meal_generator']
        freshness_tracker = setup['freshness_tracker']
        user_id = setup['user_id']

        plan = meal_generator.generate_plan(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            days=3
        )

        shopping_list = freshness_tracker.generate_shopping_list(plan)

        # Should have multiple ingredients
        assert len(shopping_list) > 0

        # Each item should have quantity and freshness
        for name, (qty, freshness) in shopping_list.items():
            assert qty is not None
            assert freshness > 0

    def test_fridge_stocking(self, setup):
        """Test stocking fridge from plan."""
        meal_generator = setup['meal_generator']
        freshness_tracker = setup['freshness_tracker']
        user_id = setup['user_id']

        plan = meal_generator.generate_plan(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            days=3
        )

        fridge = freshness_tracker.stock_fridge_from_plan(
            user_id=user_id,
            meal_plan=plan,
            purchase_date=date.today()
        )

        # Fridge should have items
        assert len(fridge.items) > 0

        # All items should have positive freshness
        for item in fridge.items:
            assert item.days_remaining > 0

    def test_detect_missed_preps(self, setup):
        """Test detection of missed prep days."""
        meal_generator = setup['meal_generator']
        adaptive_planner = setup['adaptive_planner']
        user_id = setup['user_id']

        # Create plan starting 2 days ago
        start_date = date.today() - timedelta(days=2)

        plan = meal_generator.generate_plan(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=start_date,
            days=3
        )

        # Don't mark any meals as done
        # All past dates should be detected as missed
        missed_preps = adaptive_planner.detect_missed_preps(plan, date.today())

        # Should detect 2 missed days
        assert len(missed_preps) >= 2

    def test_adaptive_replanning(self, setup):
        """Test adaptive replanning after missed prep."""
        meal_generator = setup['meal_generator']
        freshness_tracker = setup['freshness_tracker']
        adaptive_planner = setup['adaptive_planner']
        user_id = setup['user_id']

        # Create plan starting yesterday
        start_date = date.today() - timedelta(days=1)

        plan = meal_generator.generate_plan(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=start_date,
            days=3
        )

        # Stock fridge
        fridge = freshness_tracker.stock_fridge_from_plan(
            user_id=user_id,
            meal_plan=plan,
            purchase_date=start_date
        )

        # Mark yesterday's meals as skipped
        for meal in plan.meals:
            if meal.date == start_date:
                meal.prep_status = PrepStatus.SKIPPED

        # Run adaptive planner
        input_data = AdaptiveEngineInput(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            current_plan=plan,
            fridge_state=fridge,
            missed_preps=[start_date],
            current_date=date.today()
        )

        output = adaptive_planner.adapt_plan(input_data)

        # Should produce adaptation summary
        assert len(output.adaptation_summary) > 0

        # New plan should exist
        assert output.new_plan is not None

        # Should have future meals
        future_meals = [m for m in output.new_plan.meals if m.date >= date.today()]
        assert len(future_meals) > 0

    def test_ingredient_prioritization(self, setup):
        """Test prioritization of expiring ingredients."""
        meal_generator = setup['meal_generator']
        freshness_tracker = setup['freshness_tracker']
        adaptive_planner = setup['adaptive_planner']
        user_id = setup['user_id']

        # Create plan
        plan = meal_generator.generate_plan(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            days=3
        )

        # Stock fridge 2 days ago (simulate aging ingredients)
        fridge = freshness_tracker.stock_fridge_from_plan(
            user_id=user_id,
            meal_plan=plan,
            purchase_date=date.today() - timedelta(days=2)
        )

        # Apply decay
        fridge = freshness_tracker.apply_daily_decay(user_id, date.today())

        # Get expiring items
        expiring = freshness_tracker.get_expiring_soon(user_id, days_threshold=2)

        # Should have some expiring items
        assert len(expiring) > 0

        # Run adaptive planner
        input_data = AdaptiveEngineInput(
            user_id=user_id,
            diet_type=DietType.LOW_HISTAMINE,
            current_plan=plan,
            fridge_state=fridge,
            missed_preps=[],
            current_date=date.today()
        )

        output = adaptive_planner.adapt_plan(input_data)

        # Should identify priority ingredients
        assert len(output.priority_ingredients) > 0

    def test_meal_simplification(self, setup):
        """Test meal simplification for catch-up."""
        meal_generator = setup['meal_generator']
        adaptive_planner = setup['adaptive_planner']

        # Get a complex recipe
        recipes = meal_generator.get_recipes_by_diet('low_histamine')
        complex_recipes = [r for r in recipes if r.prep_time_minutes > 30]

        if complex_recipes:
            complex_recipe = complex_recipes[0]

            # Get simplified alternatives
            simplified = meal_generator.suggest_simplified_alternatives(
                complex_recipe,
                max_prep_time=20
            )

            # Should find simpler alternatives
            assert len(simplified) > 0

            # All alternatives should be faster
            for alt in simplified:
                assert alt.prep_time_minutes <= 20
                assert alt.prep_time_minutes < complex_recipe.prep_time_minutes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
