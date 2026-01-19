"""
Prep sequence optimizer.
Batches similar cooking steps across meals to minimize total prep time.
Now supports LLM-powered step parsing for semantic normalization.
"""
from datetime import date
from typing import List, Dict, Optional
from collections import defaultdict

from backend.models.schemas import (
    MealPlan, PrepStep, OptimizedPrepTimeline,
    Recipe, EquipmentType, CookingPhase
)
from backend.engine.parsing import (
    create_step_parser, ParsedPrepStep, Equipment, Phase, StepParser
)


class PrepOptimizer:
    """
    Optimize meal prep sequences by batching similar tasks.

    Uses LLM-powered or heuristic step parsing for semantic normalization,
    allowing better batching of semantically similar steps:
    - "Dice onion" + "Chop garlic" -> batched (both normalized to "chop")
    - "Rinse lettuce" + "Wash cucumber" -> batched (both normalized to "wash")
    """

    def __init__(self, parser: Optional[StepParser] = None):
        """
        Initialize prep optimizer.

        Args:
            parser: Optional step parser. If not provided, creates one based on config.
        """
        self._parser = parser or create_step_parser()

    def _create_prep_steps_from_recipe(
        self,
        recipe: Recipe,
        step_offset: int = 0
    ) -> List[PrepStep]:
        """
        Convert recipe steps to PrepStep objects using the step parser.

        Args:
            recipe: The recipe to parse.
            step_offset: Offset for step numbering (for multi-recipe timelines).

        Returns:
            List of PrepStep objects with parsed metadata.
        """
        context = {
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "recipe_total_time": recipe.prep_time_minutes,
        }

        # Parse all steps at once for better LLM context
        parsed_steps = self._parser.parse_steps(recipe.prep_steps, context)

        prep_steps = []
        step_count = 0
        for parsed in parsed_steps:
            # Skip descriptive/explanatory text (not actionable steps)
            # These are filtered out to keep the timeline focused on actual tasks
            if parsed.action_type == "descriptive":
                continue

            # Skip steps with no duration (likely invalid)
            if parsed.duration_minutes <= 0:
                continue

            # Map Equipment enum to EquipmentType
            equipment = self._map_equipment(parsed.equipment)
            # Map Phase enum to CookingPhase
            phase = self._map_phase(parsed.phase)

            prep_step = PrepStep(
                step_number=step_offset + step_count + 1,
                action=parsed.raw_step,
                ingredient=parsed.ingredient,
                duration_minutes=parsed.duration_minutes,
                can_batch=parsed.can_batch,
                batch_key=parsed.get_batch_key(),
                source_recipes=[recipe.name],
                equipment=equipment,
                is_passive=parsed.is_passive,
                phase=phase,
            )
            prep_steps.append(prep_step)
            step_count += 1

        return prep_steps

    def _map_equipment(self, equipment: Equipment) -> EquipmentType:
        """Map parsing Equipment enum to schema EquipmentType."""
        mapping = {
            Equipment.OVEN: EquipmentType.OVEN,
            Equipment.STOVETOP: EquipmentType.STOVETOP,
            Equipment.PREP_AREA: EquipmentType.PREP_AREA,
            Equipment.HANDS_FREE: EquipmentType.HANDS_FREE,
        }
        return mapping.get(equipment, EquipmentType.PREP_AREA)

    def _map_phase(self, phase: Phase) -> CookingPhase:
        """Map parsing Phase enum to schema CookingPhase."""
        mapping = {
            Phase.PREP: CookingPhase.PREP,
            Phase.COOKING: CookingPhase.COOKING,
            Phase.FINISHING: CookingPhase.FINISHING,
        }
        return mapping.get(phase, CookingPhase.PREP)

    def optimize_meal_prep(self, meal_plan: MealPlan, prep_date: date) -> OptimizedPrepTimeline:
        """
        Optimize prep sequence for meals on a specific date.

        Uses semantic normalization for improved batching of similar steps.

        Args:
            meal_plan: The meal plan to optimize.
            prep_date: The date to generate timeline for.

        Returns:
            OptimizedPrepTimeline with batched steps and time savings.
        """
        meals_for_date = meal_plan.get_meals_by_date(prep_date)

        if not meals_for_date:
            return OptimizedPrepTimeline(
                total_time_minutes=0,
                steps=[],
                batched_savings_minutes=0,
                prep_date=prep_date
            )

        # Collect all steps from all recipes
        all_steps: List[PrepStep] = []
        for meal in meals_for_date:
            recipe_steps = self._create_prep_steps_from_recipe(meal.recipe, len(all_steps))
            all_steps.extend(recipe_steps)

        # Group steps by batch key
        batch_groups: Dict[str, List[PrepStep]] = defaultdict(list)
        non_batch_steps: List[PrepStep] = []

        for step in all_steps:
            if step.can_batch and step.batch_key:
                batch_groups[step.batch_key].append(step)
            else:
                non_batch_steps.append(step)

        # Optimize batched steps
        optimized_steps: List[PrepStep] = []
        time_saved = 0

        for batch_key, batch_steps in batch_groups.items():
            if len(batch_steps) > 1:
                combined_action = self._combine_batch_steps(batch_steps)
                combined_duration = max(s.duration_minutes for s in batch_steps)

                original_time = sum(s.duration_minutes for s in batch_steps)
                time_saved += (original_time - combined_duration)

                # Combine source recipes (preserve order, remove duplicates)
                combined_sources = []
                for step in batch_steps:
                    for recipe_name in step.source_recipes:
                        if recipe_name not in combined_sources:
                            combined_sources.append(recipe_name)

                # Use metadata from first step for equipment/phase
                first_step = batch_steps[0]

                combined_step = PrepStep(
                    step_number=len(optimized_steps) + 1,
                    action=combined_action,
                    ingredient=first_step.ingredient,
                    duration_minutes=combined_duration,
                    can_batch=True,
                    batch_key=batch_key,
                    source_recipes=combined_sources,
                    equipment=first_step.equipment,
                    is_passive=first_step.is_passive,
                    phase=first_step.phase,
                )
                optimized_steps.append(combined_step)
            else:
                batch_steps[0].step_number = len(optimized_steps) + 1
                optimized_steps.append(batch_steps[0])

        # Add non-batchable steps
        for step in non_batch_steps:
            step.step_number = len(optimized_steps) + 1
            optimized_steps.append(step)

        total_time = sum(s.duration_minutes for s in optimized_steps)

        return OptimizedPrepTimeline(
            total_time_minutes=total_time,
            steps=optimized_steps,
            batched_savings_minutes=time_saved,
            prep_date=prep_date
        )

    # Common adverbs that should be skipped when extracting action verbs
    COMMON_ADVERBS = {
        "finely", "roughly", "thinly", "thickly", "quickly", "slowly",
        "gently", "vigorously", "carefully", "lightly", "heavily",
        "generously", "thoroughly", "immediately", "briefly", "well",
    }

    def _combine_batch_steps(self, steps: List[PrepStep]) -> str:
        """
        Combine multiple similar steps into one description.

        Args:
            steps: List of similar steps to combine.

        Returns:
            Combined action description.
        """
        if not steps or len(steps) == 1:
            return steps[0].action if steps else ""

        # Extract action verb from batch_key (format: "action_type_ingredient" or "action_type")
        # This provides the normalized verb rather than raw text parsing
        batch_key = steps[0].batch_key
        if batch_key:
            action_verb = batch_key.split("_")[0]  # Get normalized action type
        else:
            # Fallback: extract verb from action, skipping common adverbs
            action_verb = self._extract_action_verb(steps[0].action)

        ingredients = [s.ingredient for s in steps if s.ingredient]

        if ingredients:
            unique_ingredients = list(dict.fromkeys(ingredients))
            if len(unique_ingredients) == 1:
                return f"{action_verb.capitalize()} all {unique_ingredients[0]} at once (for {len(steps)} recipes)"
            else:
                ing_list = ", ".join(unique_ingredients[:3])
                return f"{action_verb.capitalize()} {ing_list} together"

        return f"{action_verb.capitalize()} ingredients for {len(steps)} recipes together"

    def _extract_action_verb(self, action: str) -> str:
        """
        Extract the main verb from an action string, skipping adverbs.

        Fallback for cases where batch_key is not available.
        """
        words = action.lower().split()
        for word in words:
            clean_word = word.rstrip(".,;:")
            if clean_word not in self.COMMON_ADVERBS and len(clean_word) > 2:
                return clean_word

        return "prepare"  # Ultimate fallback
