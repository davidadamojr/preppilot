"""
LLM-powered step parser using OpenAI for semantic normalization.

This parser uses GPT-4 to extract structured data from recipe steps with
superior accuracy for:
- Semantic action normalization ("dice" -> "chop", "rinse" -> "wash")
- Ingredient normalization ("tart green apple" -> "apple")
- Equipment and phase detection
- Passive step identification

Falls back to HeuristicStepParser on errors.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from backend.clients.openai_client import OpenAIClient, OpenAIClientError
from backend.engine.parsing.cache import get_step_cache
from backend.engine.parsing.heuristic import HeuristicStepParser
from backend.engine.parsing.models import Equipment, ParsedPrepStep, Phase

logger = logging.getLogger(__name__)


# System prompt for the LLM
SYSTEM_PROMPT = """You are a culinary assistant that analyzes recipe preparation steps.
Extract structured information to help optimize cooking schedules.

IMPORTANT: Normalize action types and ingredients to canonical forms:

Action Type Normalization:
- Cutting actions (dice, mince, cube, julienne, slice, shred) -> "chop"
- Washing actions (rinse, clean) -> "wash"
- Mixing actions (whisk, beat, fold, stir, combine) -> "mix"
- Frying actions (sauté, pan-fry, stir-fry, sear, brown) -> "fry"
- Roasting actions (bake, roast) -> "roast"
- Keep simmer, boil, rest, serve, preheat, grate, peel, season as-is

Ingredient Normalization:
- Remove adjectives like "fresh", "tart", "medium", "large", "raw"
- Simplify compound ingredients ("boneless skinless chicken breast" -> "chicken breast")
- Keep essential descriptors ("red cabbage" -> "red cabbage", "white rice" -> "rice")

Equipment Categories:
- "oven": bake, roast, broil, preheat oven
- "stovetop": simmer, boil, fry, sauté, sear, heat pan
- "prep_area": chop, mix, season, form, peel, grate
- "hands_free": rest, marinate, let sit, chill, refrigerate

Phase Categories:
- "prep": washing, chopping, mixing, seasoning before cooking
- "cooking": any heat application (stovetop, oven)
- "finishing": serving, plating, garnishing, final additions

Respond with a JSON object containing a "parsed_steps" array."""


def _build_user_prompt(steps: List[str], context: Dict) -> str:
    """Build the user prompt for the LLM."""
    recipe_name = context.get("recipe_name", "Unknown Recipe")
    total_time = context.get("recipe_total_time", 30)
    num_steps = len(steps)

    steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))

    return f"""Recipe: {recipe_name}
Total prep time: {total_time} minutes

IMPORTANT: You MUST return exactly {num_steps} parsed steps - one for each input step below.
Do NOT skip, combine, or merge steps. Each input step should have exactly one corresponding output.

Parse each step and extract:
- action_type: Primary action NORMALIZED (chop, wash, mix, roast, simmer, etc.)
  - For descriptive/explanatory text that isn't actionable, use "descriptive"
- ingredient: Main ingredient NORMALIZED (remove adjectives like "fresh", "tart"), or null if none
- duration_minutes: Estimated time for this step (use 0 for descriptive text)
- equipment: "oven" | "stovetop" | "prep_area" | "hands_free"
- is_passive: true if no active attention needed (simmer, rest, bake)
- can_batch: true if combinable with similar steps across recipes
- phase: "prep" | "cooking" | "finishing"

Steps ({num_steps} total):
{steps_text}

Return JSON with exactly {num_steps} items in parsed_steps:
{{
  "parsed_steps": [
    {{"step_index": 0, "action_type": "...", "ingredient": "...", "duration_minutes": N, "equipment": "...", "is_passive": bool, "can_batch": bool, "phase": "..."}}
  ]
}}"""


class LLMStepParser:
    """
    LLM-powered step parser with caching and heuristic fallback.

    Uses OpenAI GPT-4 for semantic normalization of recipe steps.
    Caches results to minimize API calls and costs.
    Falls back to HeuristicStepParser on any error.
    """

    def __init__(self):
        """Initialize the LLM parser with client and fallback."""
        self._client = OpenAIClient()
        self._cache = get_step_cache()
        self._fallback = HeuristicStepParser()

    def parse_step(self, step: str, context: Dict) -> ParsedPrepStep:
        """
        Parse a single recipe step into structured data.

        For single steps, delegates to parse_steps for consistency.

        Args:
            step: The raw step text.
            context: Additional context with recipe_name, recipe_total_time, etc.

        Returns:
            ParsedPrepStep with normalized action_type, ingredient, equipment, etc.
        """
        steps = [step]
        parsed = self.parse_steps(steps, context)
        return parsed[0]

    def parse_steps(self, steps: List[str], context: Dict) -> List[ParsedPrepStep]:
        """
        Parse multiple recipe steps into structured data.

        Checks cache first, then calls LLM for uncached steps.
        Falls back to heuristics on any error.

        Args:
            steps: List of raw step texts.
            context: Additional context with:
                - recipe_name: Name of the recipe
                - recipe_total_time: Total prep time in minutes
                - recipe_id: Unique identifier for caching

        Returns:
            List of ParsedPrepStep objects in the same order as input steps.
        """
        recipe_id = context.get("recipe_id", context.get("recipe_name", "unknown"))
        total_steps = len(steps)

        # Check cache for all steps
        cached_results: Dict[int, ParsedPrepStep] = {}
        uncached_indices: List[int] = []
        uncached_steps: List[str] = []

        for i, step in enumerate(steps):
            cached = self._cache.get(recipe_id, step)
            if cached:
                cached_results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_steps.append(step)

        # If all steps are cached, return them
        if not uncached_steps:
            logger.debug(f"All {len(steps)} steps found in cache")
            return [cached_results[i] for i in range(len(steps))]

        # Call LLM for uncached steps
        try:
            llm_results = self._parse_with_llm(uncached_steps, context)

            # Merge cached and LLM results
            for idx, parsed in zip(uncached_indices, llm_results):
                cached_results[idx] = parsed
                # Cache the new result
                self._cache.set(recipe_id, steps[idx], parsed)

            # Return in original order
            return [cached_results[i] for i in range(len(steps))]

        except Exception as e:
            logger.warning(f"LLM parsing failed, falling back to heuristics: {e}")
            return self._parse_with_fallback(steps, context)

    def _parse_with_llm(self, steps: List[str], context: Dict) -> List[ParsedPrepStep]:
        """
        Parse steps using the LLM.

        Args:
            steps: List of uncached step texts.
            context: Recipe context for the prompt.

        Returns:
            List of ParsedPrepStep objects.

        Raises:
            OpenAIClientError: If the API call fails.
            ValueError: If the response format is invalid.
        """
        user_prompt = _build_user_prompt(steps, context)
        total_steps = len(steps)

        response = self._client.parse_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        parsed_steps = response.get("parsed_steps", [])

        # Handle step count mismatch gracefully
        if len(parsed_steps) != len(steps):
            logger.warning(
                f"LLM returned {len(parsed_steps)} steps, expected {len(steps)}. "
                "Using step_index to match where possible, falling back for others."
            )
            return self._match_llm_results_to_steps(parsed_steps, steps, context)

        results = []
        for i, step_data in enumerate(parsed_steps):
            try:
                parsed = self._convert_llm_response(step_data, steps[i])
                results.append(parsed)
            except Exception as e:
                logger.warning(f"Failed to convert LLM response for step {i}: {e}")
                # Use fallback for this step
                fallback_context = {
                    **context,
                    "step_index": i,
                    "total_steps": total_steps,
                }
                results.append(self._fallback.parse_step(steps[i], fallback_context))

        return results

    def _match_llm_results_to_steps(
        self,
        parsed_steps: List[Dict[str, Any]],
        steps: List[str],
        context: Dict,
    ) -> List[ParsedPrepStep]:
        """
        Match LLM results to input steps when counts don't match.

        Uses step_index from LLM response to map results to the correct steps.
        Falls back to heuristics for any step not covered by LLM results.

        Args:
            parsed_steps: List of parsed step data from LLM.
            steps: Original list of step texts.
            context: Recipe context.

        Returns:
            List of ParsedPrepStep objects matching the input steps order.
        """
        total_steps = len(steps)
        results: Dict[int, ParsedPrepStep] = {}

        # Build a map of step_index to LLM result
        for step_data in parsed_steps:
            idx = step_data.get("step_index")
            if idx is not None and 0 <= idx < total_steps:
                try:
                    parsed = self._convert_llm_response(step_data, steps[idx])
                    results[idx] = parsed
                except Exception as e:
                    logger.warning(f"Failed to convert LLM response for step {idx}: {e}")

        # Fill in any missing steps with heuristic fallback
        for i in range(total_steps):
            if i not in results:
                fallback_context = {
                    **context,
                    "step_index": i,
                    "total_steps": total_steps,
                }
                results[i] = self._fallback.parse_step(steps[i], fallback_context)

        return [results[i] for i in range(total_steps)]

    def _convert_llm_response(self, data: Dict[str, Any], raw_step: str) -> ParsedPrepStep:
        """
        Convert LLM JSON response to ParsedPrepStep.

        Args:
            data: Parsed JSON data from LLM.
            raw_step: Original step text.

        Returns:
            ParsedPrepStep instance.
        """
        # Map equipment string to enum
        equipment_str = data.get("equipment", "prep_area").lower()
        equipment_map = {
            "oven": Equipment.OVEN,
            "stovetop": Equipment.STOVETOP,
            "prep_area": Equipment.PREP_AREA,
            "hands_free": Equipment.HANDS_FREE,
        }
        equipment = equipment_map.get(equipment_str, Equipment.PREP_AREA)

        # Map phase string to enum
        phase_str = data.get("phase", "prep").lower()
        phase_map = {
            "prep": Phase.PREP,
            "cooking": Phase.COOKING,
            "finishing": Phase.FINISHING,
        }
        phase = phase_map.get(phase_str, Phase.PREP)

        return ParsedPrepStep(
            action_type=data.get("action_type", "other"),
            ingredient=data.get("ingredient") or None,
            can_batch=data.get("can_batch", False),
            equipment=equipment,
            is_passive=data.get("is_passive", False),
            phase=phase,
            duration_minutes=data.get("duration_minutes", 5),
            raw_step=raw_step,
            parse_source="llm",
        )

    def _parse_with_fallback(self, steps: List[str], context: Dict) -> List[ParsedPrepStep]:
        """
        Parse steps using the heuristic fallback.

        Args:
            steps: List of step texts.
            context: Recipe context.

        Returns:
            List of ParsedPrepStep objects from heuristic parser.
        """
        return self._fallback.parse_steps(steps, context)
