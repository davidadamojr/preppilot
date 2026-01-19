"""
Protocol definition for step parsers.

Defines the interface that all step parsers must implement.
"""

from typing import Dict, List, Protocol

from backend.engine.parsing.models import ParsedPrepStep


class StepParser(Protocol):
    """
    Protocol for step parsing implementations.

    Both HeuristicStepParser and LLMStepParser implement this protocol,
    allowing the optimizer to use either without knowing the implementation.
    """

    def parse_step(self, step: str, context: Dict) -> ParsedPrepStep:
        """
        Parse a single recipe step into structured data.

        Args:
            step: The raw step text (e.g., "Dice the onion finely")
            context: Additional context for parsing:
                - recipe_name: Name of the recipe
                - recipe_total_time: Total prep time in minutes
                - total_steps: Number of steps in recipe
                - step_index: Index of this step in the recipe

        Returns:
            ParsedPrepStep with normalized action_type, ingredient, equipment, etc.
        """
        ...

    def parse_steps(self, steps: List[str], context: Dict) -> List[ParsedPrepStep]:
        """
        Parse multiple recipe steps into structured data.

        This is the preferred method for parsing all steps from a recipe,
        as it allows for batch LLM calls and better context understanding.

        Args:
            steps: List of raw step texts
            context: Additional context for parsing:
                - recipe_name: Name of the recipe
                - recipe_total_time: Total prep time in minutes

        Returns:
            List of ParsedPrepStep objects in the same order as input steps.
        """
        ...
