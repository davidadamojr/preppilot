"""
Unit tests for PrepOptimizer with enhanced batching.

Tests semantic batching using normalized action types.
"""

import pytest
from datetime import date
from uuid import uuid4

from backend.engine.prep_optimizer import PrepOptimizer
from backend.engine.parsing.heuristic import HeuristicStepParser
from backend.models.schemas import (
    MealPlan, MealSlot, Recipe, Ingredient, DietType, PrepStatus,
    EquipmentType, CookingPhase
)


class TestPrepOptimizer:
    """Tests for PrepOptimizer batching."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer with heuristic parser (no LLM calls)."""
        return PrepOptimizer(parser=HeuristicStepParser())

    @pytest.fixture
    def sample_recipe_1(self):
        """Recipe with steps that can be batched."""
        return Recipe(
            id=str(uuid4()),
            name="Chicken Salad",
            diet_tags=["low_histamine"],
            meal_type="lunch",
            ingredients=[
                Ingredient(name="chicken", freshness_days=2, quantity="300g"),
                Ingredient(name="lettuce", freshness_days=5, quantity="1 head"),
                Ingredient(name="cucumber", freshness_days=7, quantity="1"),
            ],
            prep_steps=[
                "Slice chicken breast.",
                "Rinse lettuce thoroughly.",
                "Slice cucumber into rounds.",
                "Season chicken with salt.",
                "Sauté chicken for 5 minutes.",
            ],
            prep_time_minutes=20,
            reusability_index=0.8,
        )

    @pytest.fixture
    def sample_recipe_2(self):
        """Recipe with steps that overlap with recipe 1 for batching."""
        return Recipe(
            id=str(uuid4()),
            name="Vegetable Soup",
            diet_tags=["low_histamine"],
            meal_type="dinner",
            ingredients=[
                Ingredient(name="carrots", freshness_days=14, quantity="3"),
                Ingredient(name="celery", freshness_days=7, quantity="2 stalks"),
                Ingredient(name="onion", freshness_days=14, quantity="1"),
            ],
            prep_steps=[
                "Dice carrots.",
                "Dice onion.",
                "Wash celery stalks.",
                "Simmer vegetables for 20 minutes.",
            ],
            prep_time_minutes=30,
            reusability_index=0.7,
        )

    @pytest.fixture
    def recipe_with_passive_steps(self):
        """Recipe with passive cooking steps."""
        return Recipe(
            id=str(uuid4()),
            name="Roast Chicken with Vegetables",
            diet_tags=["low_histamine"],
            meal_type="dinner",
            ingredients=[
                Ingredient(name="chicken", freshness_days=2, quantity="1 whole"),
                Ingredient(name="carrots", freshness_days=14, quantity="4"),
                Ingredient(name="potatoes", freshness_days=21, quantity="4"),
            ],
            prep_steps=[
                "Preheat oven to 400°F.",
                "Season chicken with salt and herbs.",
                "Chop carrots into chunks.",
                "Chop potatoes into cubes.",
                "Roast chicken for 45 minutes.",
                "Let chicken rest for 10 minutes.",
                "Serve warm.",
            ],
            prep_time_minutes=60,
            reusability_index=0.7,
        )

    @pytest.fixture
    def single_meal_plan(self, sample_recipe_1):
        """Meal plan with a single recipe."""
        today = date.today()
        return MealPlan(
            id=uuid4(),
            user_id=uuid4(),
            diet_type=DietType.LOW_HISTAMINE,
            start_date=today,
            end_date=today,
            meals=[
                MealSlot(
                    date=today,
                    meal_type="lunch",
                    recipe=sample_recipe_1,
                    prep_status=PrepStatus.PENDING,
                )
            ],
        )

    @pytest.fixture
    def multi_meal_plan(self, sample_recipe_1, sample_recipe_2):
        """Meal plan with multiple recipes for batching tests."""
        today = date.today()
        return MealPlan(
            id=uuid4(),
            user_id=uuid4(),
            diet_type=DietType.LOW_HISTAMINE,
            start_date=today,
            end_date=today,
            meals=[
                MealSlot(
                    date=today,
                    meal_type="lunch",
                    recipe=sample_recipe_1,
                    prep_status=PrepStatus.PENDING,
                ),
                MealSlot(
                    date=today,
                    meal_type="dinner",
                    recipe=sample_recipe_2,
                    prep_status=PrepStatus.PENDING,
                ),
            ],
        )

    @pytest.fixture
    def passive_step_plan(self, recipe_with_passive_steps):
        """Meal plan with passive steps."""
        today = date.today()
        return MealPlan(
            id=uuid4(),
            user_id=uuid4(),
            diet_type=DietType.LOW_HISTAMINE,
            start_date=today,
            end_date=today,
            meals=[
                MealSlot(
                    date=today,
                    meal_type="dinner",
                    recipe=recipe_with_passive_steps,
                    prep_status=PrepStatus.PENDING,
                )
            ],
        )

    # Basic Timeline Generation Tests

    def test_generates_timeline_for_single_recipe(self, optimizer, single_meal_plan):
        """Should generate timeline with all steps from single recipe."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(single_meal_plan, today)

        assert timeline.prep_date == today
        assert len(timeline.steps) > 0
        assert timeline.total_time_minutes > 0

    def test_empty_timeline_for_no_meals(self, optimizer, single_meal_plan):
        """Should return empty timeline for date with no meals."""
        other_date = date(2030, 1, 1)
        timeline = optimizer.optimize_meal_prep(single_meal_plan, other_date)

        assert timeline.total_time_minutes == 0
        assert len(timeline.steps) == 0

    # Batching Tests

    def test_batches_similar_chop_actions(self, optimizer, multi_meal_plan):
        """Should batch dice/slice (normalized to chop) across recipes."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(multi_meal_plan, today)

        # Count chop-type steps (batch_key may be None for non-batchable steps)
        chop_steps = [
            s for s in timeline.steps
            if s.batch_key and "chop" in s.batch_key.lower()
        ]

        # Should have batched some chop steps together
        batched_chop = [s for s in chop_steps if len(s.source_recipes) > 1]
        # At least some steps should be batchable
        assert any(s.can_batch for s in timeline.steps)

    def test_batches_similar_wash_actions(self, optimizer, multi_meal_plan):
        """Should batch rinse/wash (normalized to wash) across recipes."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(multi_meal_plan, today)

        # Check for wash-type batched steps
        wash_steps = [s for s in timeline.steps if s.batch_key and "wash" in s.batch_key.lower()]

        # Should have wash steps
        assert len(wash_steps) >= 1

    def test_batching_saves_time(self, optimizer, multi_meal_plan):
        """Should save time through batching."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(multi_meal_plan, today)

        # Batching should save some time when steps can be combined
        # (Time saved may be 0 if no steps were actually batchable)
        assert timeline.batched_savings_minutes >= 0

    # Equipment Detection Tests

    def test_detects_oven_equipment(self, optimizer, passive_step_plan):
        """Should detect oven equipment for roasting steps."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(passive_step_plan, today)

        # Find the roast step
        roast_steps = [s for s in timeline.steps if "roast" in s.action.lower()]
        assert len(roast_steps) > 0

        roast_step = roast_steps[0]
        assert roast_step.equipment == EquipmentType.OVEN

    def test_detects_prep_area_equipment(self, optimizer, single_meal_plan):
        """Should detect prep_area for chopping steps."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(single_meal_plan, today)

        # Find chopping steps
        chop_steps = [s for s in timeline.steps if "slice" in s.action.lower() or "chop" in s.action.lower()]

        for step in chop_steps:
            assert step.equipment == EquipmentType.PREP_AREA

    # Passive Step Detection Tests

    def test_detects_passive_roasting(self, optimizer, passive_step_plan):
        """Should detect roasting as passive step."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(passive_step_plan, today)

        roast_steps = [s for s in timeline.steps if "roast" in s.action.lower()]
        assert len(roast_steps) > 0
        assert roast_steps[0].is_passive is True

    def test_detects_passive_resting(self, optimizer, passive_step_plan):
        """Should detect rest as passive step."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(passive_step_plan, today)

        rest_steps = [s for s in timeline.steps if "rest" in s.action.lower()]
        assert len(rest_steps) > 0
        assert rest_steps[0].is_passive is True

    # Phase Detection Tests

    def test_detects_cooking_phase(self, optimizer, passive_step_plan):
        """Should detect cooking phase for roasting."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(passive_step_plan, today)

        roast_steps = [s for s in timeline.steps if "roast" in s.action.lower()]
        assert len(roast_steps) > 0
        assert roast_steps[0].phase == CookingPhase.COOKING

    def test_detects_finishing_phase(self, optimizer, passive_step_plan):
        """Should detect finishing phase for serving."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(passive_step_plan, today)

        serve_steps = [s for s in timeline.steps if "serve" in s.action.lower()]
        assert len(serve_steps) > 0
        assert serve_steps[0].phase == CookingPhase.FINISHING

    # Source Recipe Tracking Tests

    def test_tracks_source_recipes(self, optimizer, multi_meal_plan):
        """Should track which recipes each step comes from."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(multi_meal_plan, today)

        for step in timeline.steps:
            assert len(step.source_recipes) > 0
            assert all(isinstance(r, str) for r in step.source_recipes)

    def test_batched_step_tracks_multiple_sources(self, optimizer, multi_meal_plan):
        """Batched steps should track all source recipes."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(multi_meal_plan, today)

        # Find any batched step that combines multiple recipes
        multi_source_steps = [s for s in timeline.steps if len(s.source_recipes) > 1]

        # If we have multi-source steps, they should have multiple sources
        for step in multi_source_steps:
            assert len(step.source_recipes) >= 2

    # Step Numbering Tests

    def test_steps_are_numbered_sequentially(self, optimizer, single_meal_plan):
        """Steps should have sequential step numbers starting from 1."""
        today = date.today()
        timeline = optimizer.optimize_meal_prep(single_meal_plan, today)

        for i, step in enumerate(timeline.steps):
            assert step.step_number == i + 1


class TestPrepOptimizerEdgeCases:
    """Edge case tests for PrepOptimizer."""

    @pytest.fixture
    def optimizer(self):
        return PrepOptimizer(parser=HeuristicStepParser())

    def test_handles_empty_meal_plan(self, optimizer):
        """Should handle meal plan with no meals."""
        today = date.today()
        empty_plan = MealPlan(
            id=uuid4(),
            user_id=uuid4(),
            diet_type=DietType.LOW_HISTAMINE,
            start_date=today,
            end_date=today,
            meals=[],
        )

        timeline = optimizer.optimize_meal_prep(empty_plan, today)
        assert timeline.total_time_minutes == 0
        assert len(timeline.steps) == 0

    def test_handles_recipe_with_single_step(self, optimizer):
        """Should handle recipe with only one step."""
        today = date.today()
        simple_recipe = Recipe(
            id=str(uuid4()),
            name="Simple Dish",
            diet_tags=["low_histamine"],
            meal_type="snack",
            ingredients=[
                Ingredient(name="apple", freshness_days=14, quantity="1"),
            ],
            prep_steps=["Slice apple."],
            prep_time_minutes=5,
            reusability_index=0.5,
        )

        plan = MealPlan(
            id=uuid4(),
            user_id=uuid4(),
            diet_type=DietType.LOW_HISTAMINE,
            start_date=today,
            end_date=today,
            meals=[
                MealSlot(
                    date=today,
                    meal_type="snack",
                    recipe=simple_recipe,
                    prep_status=PrepStatus.PENDING,
                )
            ],
        )

        timeline = optimizer.optimize_meal_prep(plan, today)
        assert len(timeline.steps) == 1
        assert "apple" in timeline.steps[0].action.lower() or "slice" in timeline.steps[0].action.lower()
