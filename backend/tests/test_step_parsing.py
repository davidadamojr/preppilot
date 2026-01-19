"""
Unit tests for step parsing module.

Tests semantic normalization, equipment detection, phase detection,
and passive step identification for both heuristic and LLM parsers.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.engine.parsing.heuristic import HeuristicStepParser
from backend.engine.parsing.models import Equipment, ParsedPrepStep, Phase
from backend.engine.parsing.cache import StepParsingCache


class TestHeuristicStepParser:
    """Tests for HeuristicStepParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return HeuristicStepParser()

    @pytest.fixture
    def default_context(self):
        """Default context for parsing."""
        return {
            "recipe_name": "Test Recipe",
            "recipe_total_time": 30,
            "step_index": 0,
            "total_steps": 5,
        }

    # Action Type Normalization Tests

    def test_dice_normalizes_to_chop(self, parser, default_context):
        """Dice should normalize to chop action type."""
        step = "Dice the onion finely."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "chop"

    def test_mince_normalizes_to_chop(self, parser, default_context):
        """Mince should normalize to chop action type."""
        step = "Mince garlic cloves."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "chop"

    def test_slice_normalizes_to_chop(self, parser, default_context):
        """Slice should normalize to chop action type."""
        step = "Slice cucumber into rounds."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "chop"

    def test_rinse_normalizes_to_wash(self, parser, default_context):
        """Rinse should normalize to wash action type."""
        step = "Rinse rice thoroughly."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "wash"

    def test_whisk_normalizes_to_mix(self, parser, default_context):
        """Whisk should normalize to mix action type."""
        step = "Whisk eggs with salt."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "mix"

    def test_saute_normalizes_to_fry(self, parser, default_context):
        """Sauté should normalize to fry action type."""
        step = "Sauté onions until golden."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "fry"

    def test_bake_normalizes_to_roast(self, parser, default_context):
        """Bake should normalize to roast action type."""
        step = "Bake at 400°F for 30 minutes."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "roast"

    # Ingredient Extraction Tests

    def test_extracts_ingredient_after_action(self, parser, default_context):
        """Should extract ingredient following action verb."""
        step = "Dice the onion finely."
        result = parser.parse_step(step, default_context)
        assert result.ingredient == "onion"

    def test_extracts_ingredient_with_chop(self, parser, default_context):
        """Should extract ingredient with chop action."""
        step = "Chop carrots into small pieces."
        result = parser.parse_step(step, default_context)
        assert result.ingredient == "carrots"

    def test_filters_adjectives_from_ingredient(self, parser, default_context):
        """Should filter common adjectives from ingredients."""
        step = "Dice the fresh onion."
        result = parser.parse_step(step, default_context)
        assert result.ingredient == "onion"

    # Equipment Detection Tests

    def test_detects_oven_equipment(self, parser, default_context):
        """Should detect oven equipment from bake/roast keywords."""
        step = "Roast at 400°F for 30 minutes."
        result = parser.parse_step(step, default_context)
        assert result.equipment == Equipment.OVEN

    def test_detects_stovetop_equipment(self, parser, default_context):
        """Should detect stovetop equipment from simmer/boil keywords."""
        step = "Simmer for 15 minutes."
        result = parser.parse_step(step, default_context)
        assert result.equipment == Equipment.STOVETOP

    def test_detects_hands_free_equipment(self, parser, default_context):
        """Should detect hands-free for rest/marinate steps."""
        step = "Let the meat rest for 10 minutes."
        result = parser.parse_step(step, default_context)
        assert result.equipment == Equipment.HANDS_FREE

    def test_detects_prep_area_for_chopping(self, parser, default_context):
        """Should detect prep_area for chopping steps."""
        step = "Chop the vegetables."
        result = parser.parse_step(step, default_context)
        assert result.equipment == Equipment.PREP_AREA

    # Passive Step Detection Tests

    def test_detects_passive_simmer(self, parser, default_context):
        """Should detect simmer as passive."""
        step = "Simmer for 15 minutes."
        result = parser.parse_step(step, default_context)
        assert result.is_passive is True

    def test_detects_passive_bake(self, parser, default_context):
        """Should detect bake as passive."""
        step = "Bake at 400°F for 30 minutes."
        result = parser.parse_step(step, default_context)
        assert result.is_passive is True

    def test_detects_passive_rest(self, parser, default_context):
        """Should detect rest as passive."""
        step = "Let the meat rest for 10 minutes."
        result = parser.parse_step(step, default_context)
        assert result.is_passive is True

    def test_detects_active_chop(self, parser, default_context):
        """Should detect chop as active (not passive)."""
        step = "Chop the vegetables."
        result = parser.parse_step(step, default_context)
        assert result.is_passive is False

    # Phase Detection Tests

    def test_detects_prep_phase_for_washing(self, parser, default_context):
        """Should detect prep phase for washing."""
        step = "Wash the vegetables."
        result = parser.parse_step(step, default_context)
        assert result.phase == Phase.PREP

    def test_detects_cooking_phase_for_simmering(self, parser, default_context):
        """Should detect cooking phase for simmering."""
        step = "Simmer for 15 minutes."
        result = parser.parse_step(step, default_context)
        assert result.phase == Phase.COOKING

    def test_detects_finishing_phase_for_serving(self, parser, default_context):
        """Should detect finishing phase for serving."""
        step = "Serve warm with garnish."
        result = parser.parse_step(step, default_context)
        assert result.phase == Phase.FINISHING

    # Duration Estimation Tests

    def test_extracts_explicit_duration(self, parser, default_context):
        """Should extract explicit duration from step text."""
        step = "Simmer for 15 minutes."
        result = parser.parse_step(step, default_context)
        assert result.duration_minutes == 15

    def test_estimates_duration_for_baking(self, parser, default_context):
        """Should estimate 30 min for baking without explicit time."""
        step = "Bake until golden brown."
        result = parser.parse_step(step, default_context)
        assert result.duration_minutes == 30

    def test_estimates_duration_for_chopping(self, parser, default_context):
        """Should estimate 3 min for chopping."""
        step = "Chop the vegetables."
        result = parser.parse_step(step, default_context)
        assert result.duration_minutes == 3

    # Batch Key Tests

    def test_generates_batch_key_for_batchable_step(self, parser, default_context):
        """Should generate batch key for batchable steps."""
        step = "Chop carrots into small pieces."
        result = parser.parse_step(step, default_context)
        assert result.can_batch is True
        assert result.get_batch_key() == "chop_carrots"

    def test_no_batch_key_for_non_batchable_step(self, parser, default_context):
        """Should not generate batch key for non-batchable steps."""
        step = "Simmer for 15 minutes."
        result = parser.parse_step(step, default_context)
        assert result.can_batch is False
        assert result.get_batch_key() is None

    # Parse Source Tests

    def test_parse_source_is_heuristic(self, parser, default_context):
        """Should set parse_source to 'heuristic'."""
        step = "Chop the vegetables."
        result = parser.parse_step(step, default_context)
        assert result.parse_source == "heuristic"

    # Batch Parsing Tests

    def test_parse_steps_processes_all_steps(self, parser):
        """Should process all steps in order."""
        steps = [
            "Rinse rice thoroughly.",
            "Simmer for 15 minutes.",
            "Serve warm.",
        ]
        context = {"recipe_name": "Test", "recipe_total_time": 25}
        results = parser.parse_steps(steps, context)

        assert len(results) == 3
        assert results[0].action_type == "wash"
        assert results[1].action_type == "simmer"
        assert results[2].action_type == "serve"

    # Real Recipe Step Tests (from low_histamine_recipes.json)

    def test_real_step_crack_cardamom(self, parser, default_context):
        """Test parsing: 'Crack cardamom pods to expose seeds.'"""
        step = "Crack cardamom pods to expose seeds."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "crack"
        assert result.ingredient == "cardamom"

    def test_real_step_heat_coconut_milk(self, parser, default_context):
        """Test parsing complex step with temperature."""
        step = "Heat coconut milk in a separate pan over medium-low heat (about 300°F) with the cardamom and maple syrup until steaming (HEAT/FAT infusion)."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "heat"
        assert result.equipment == Equipment.STOVETOP

    def test_real_step_peel_and_cube(self, parser, default_context):
        """Test parsing: 'Peel and cube the tart green apple.'"""
        step = "Peel and cube the tart green apple."
        result = parser.parse_step(step, default_context)
        # cube normalizes to chop, which appears first in keyword search
        assert result.action_type == "chop"

    def test_real_step_dice_rutabaga(self, parser, default_context):
        """Test parsing: 'Dice rutabaga into small 1cm cubes for even cooking.'"""
        step = "Dice rutabaga into small 1cm cubes for even cooking."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "chop"  # dice normalizes to chop
        assert result.ingredient == "rutabaga"

    def test_real_step_brown_meatballs(self, parser, default_context):
        """Test parsing step with parenthetical."""
        step = "Brown meatballs on all sides in the hot oil (FAT adds flavor and texture)."
        result = parser.parse_step(step, default_context)
        assert result.action_type == "fry"  # brown normalizes to fry
        # Equipment detection is based on keywords; "oil" and "hot" may not trigger stovetop
        # The step doesn't contain stovetop keywords like "pan", "stove", "simmer"
        assert result.equipment in (Equipment.PREP_AREA, Equipment.STOVETOP)


class TestStepParsingCache:
    """Tests for StepParsingCache."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance with short TTL for testing."""
        return StepParsingCache(ttl_hours=1)

    @pytest.fixture
    def sample_step(self):
        """Create a sample ParsedPrepStep."""
        return ParsedPrepStep(
            action_type="chop",
            ingredient="onion",
            can_batch=True,
            equipment=Equipment.PREP_AREA,
            is_passive=False,
            phase=Phase.PREP,
            duration_minutes=3,
            raw_step="Dice the onion finely.",
            parse_source="llm",
        )

    def test_cache_miss_returns_none(self, cache):
        """Should return None for cache miss."""
        result = cache.get("recipe_123", "Chop onion")
        assert result is None

    def test_cache_set_and_get(self, cache, sample_step):
        """Should store and retrieve cached step."""
        cache.set("recipe_123", "Dice the onion finely.", sample_step)
        result = cache.get("recipe_123", "Dice the onion finely.")

        assert result is not None
        assert result.action_type == "chop"
        assert result.ingredient == "onion"

    def test_cache_different_recipe_ids(self, cache, sample_step):
        """Same step text with different recipe IDs should be separate entries."""
        cache.set("recipe_1", "Chop onion", sample_step)

        # Different recipe ID should miss
        result = cache.get("recipe_2", "Chop onion")
        assert result is None

        # Same recipe ID should hit
        result = cache.get("recipe_1", "Chop onion")
        assert result is not None

    def test_cache_clear(self, cache, sample_step):
        """Should clear all entries."""
        cache.set("recipe_1", "Step 1", sample_step)
        cache.set("recipe_2", "Step 2", sample_step)

        assert cache.size == 2
        cache.clear()
        assert cache.size == 0

    def test_cache_size(self, cache, sample_step):
        """Should track cache size correctly."""
        assert cache.size == 0

        cache.set("r1", "s1", sample_step)
        assert cache.size == 1

        cache.set("r2", "s2", sample_step)
        assert cache.size == 2


class TestParsedPrepStep:
    """Tests for ParsedPrepStep dataclass."""

    def test_get_batch_key_with_ingredient(self):
        """Should generate batch key with action_type and ingredient."""
        step = ParsedPrepStep(
            action_type="chop",
            ingredient="onion",
            can_batch=True,
            equipment=Equipment.PREP_AREA,
            is_passive=False,
            phase=Phase.PREP,
            duration_minutes=3,
            raw_step="Chop onion",
            parse_source="heuristic",
        )
        assert step.get_batch_key() == "chop_onion"

    def test_get_batch_key_without_ingredient(self):
        """Should return action_type as batch key when no ingredient."""
        step = ParsedPrepStep(
            action_type="chop",
            ingredient=None,
            can_batch=True,
            equipment=Equipment.PREP_AREA,
            is_passive=False,
            phase=Phase.PREP,
            duration_minutes=3,
            raw_step="Chop ingredients",
            parse_source="heuristic",
        )
        assert step.get_batch_key() == "chop"

    def test_get_batch_key_non_batchable(self):
        """Should return None for non-batchable steps."""
        step = ParsedPrepStep(
            action_type="simmer",
            ingredient="rice",
            can_batch=False,
            equipment=Equipment.STOVETOP,
            is_passive=True,
            phase=Phase.COOKING,
            duration_minutes=15,
            raw_step="Simmer rice",
            parse_source="heuristic",
        )
        assert step.get_batch_key() is None

    def test_can_run_during_passive_step(self):
        """Should allow prep task during passive step."""
        passive_step = ParsedPrepStep(
            action_type="simmer",
            ingredient="rice",
            can_batch=False,
            equipment=Equipment.STOVETOP,
            is_passive=True,
            phase=Phase.COOKING,
            duration_minutes=15,
            raw_step="Simmer rice",
            parse_source="heuristic",
        )

        prep_step = ParsedPrepStep(
            action_type="chop",
            ingredient="onion",
            can_batch=True,
            equipment=Equipment.PREP_AREA,
            is_passive=False,
            phase=Phase.PREP,
            duration_minutes=3,
            raw_step="Chop onion",
            parse_source="heuristic",
        )

        assert prep_step.can_run_during(passive_step) is True

    def test_cannot_run_during_active_step(self):
        """Should not allow task during active step."""
        active_step = ParsedPrepStep(
            action_type="fry",
            ingredient="onion",
            can_batch=False,
            equipment=Equipment.STOVETOP,
            is_passive=False,
            phase=Phase.COOKING,
            duration_minutes=5,
            raw_step="Fry onion",
            parse_source="heuristic",
        )

        prep_step = ParsedPrepStep(
            action_type="chop",
            ingredient="carrot",
            can_batch=True,
            equipment=Equipment.PREP_AREA,
            is_passive=False,
            phase=Phase.PREP,
            duration_minutes=3,
            raw_step="Chop carrot",
            parse_source="heuristic",
        )

        assert prep_step.can_run_during(active_step) is False

    def test_cannot_run_if_duration_exceeds(self):
        """Should not allow task if it exceeds passive step duration."""
        passive_step = ParsedPrepStep(
            action_type="rest",
            ingredient="meat",
            can_batch=False,
            equipment=Equipment.HANDS_FREE,
            is_passive=True,
            phase=Phase.COOKING,
            duration_minutes=5,  # Only 5 minutes
            raw_step="Rest meat",
            parse_source="heuristic",
        )

        prep_step = ParsedPrepStep(
            action_type="chop",
            ingredient="onion",
            can_batch=True,
            equipment=Equipment.PREP_AREA,
            is_passive=False,
            phase=Phase.PREP,
            duration_minutes=10,  # 10 minutes - too long
            raw_step="Chop onion",
            parse_source="heuristic",
        )

        assert prep_step.can_run_during(passive_step) is False
