"""
Data models for step parsing.

Contains the ParsedPrepStep dataclass which holds normalized step data
for improved batching.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional


class Equipment(str, Enum):
    """Equipment categories for scheduling and conflict detection."""

    OVEN = "oven"
    STOVETOP = "stovetop"
    PREP_AREA = "prep_area"
    HANDS_FREE = "hands_free"


class Phase(str, Enum):
    """Cooking phases for timeline organization."""

    PREP = "prep"
    COOKING = "cooking"
    FINISHING = "finishing"


@dataclass
class ParsedPrepStep:
    """
    Structured representation of a recipe step for optimization.

    Contains normalized values for improved batching:
    - action_type: Normalized action (e.g., "dice" -> "chop")
    - ingredient: Normalized ingredient (e.g., "tart green apple" -> "apple")
    - equipment: Where the step happens (oven, stovetop, prep_area, hands_free)
    - is_passive: Whether the step requires attention (simmer, rest = passive)
    - phase: prep, cooking, or finishing
    - duration_minutes: Estimated time for the step
    - can_batch: Whether this step can be combined with similar steps
    - parse_source: Whether this was parsed by LLM or heuristics

    Example:
        >>> step = ParsedPrepStep(
        ...     action_type="chop",
        ...     ingredient="apple",
        ...     equipment=Equipment.PREP_AREA,
        ...     is_passive=False,
        ...     phase=Phase.PREP,
        ...     duration_minutes=3,
        ...     can_batch=True,
        ...     raw_step="Peel and cube the tart green apple.",
        ...     parse_source="llm"
        ... )
    """

    # Normalized values for improved batching
    action_type: str  # Normalized: "dice" -> "chop", "rinse" -> "wash"
    ingredient: Optional[str]  # Normalized: "tart green apple" -> "apple"
    can_batch: bool  # True if combinable with similar steps

    # Step metadata
    equipment: Equipment  # Where the step happens
    is_passive: bool  # True = no attention needed (simmer, rest)
    phase: Phase  # prep, cooking, or finishing
    duration_minutes: int  # Estimated time

    # Metadata
    raw_step: str  # Original text
    parse_source: Literal["llm", "heuristic"]

    def get_batch_key(self) -> Optional[str]:
        """
        Generate a key for grouping similar steps.

        Returns:
            Batch key in format "action_type_ingredient" or None if not batchable.
        """
        if not self.can_batch:
            return None
        if self.ingredient:
            return f"{self.action_type}_{self.ingredient}"
        return self.action_type
