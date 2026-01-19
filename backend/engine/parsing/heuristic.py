"""
Heuristic-based step parser using keyword matching.

This parser extracts action types, ingredients, equipment, and phase
from recipe steps using rule-based keyword matching. It serves as:
1. The default parser when LLM parsing is disabled
2. A fallback when LLM parsing fails

While less accurate than LLM parsing for semantic normalization,
it's fast, free, and works offline.
"""

import re
from typing import Dict, List

from backend.engine.parsing.models import Equipment, ParsedPrepStep, Phase


class HeuristicStepParser:
    """
    Rule-based step parser using keyword matching.

    Extracts structured data from recipe steps by matching keywords
    against predefined action types, equipment indicators, and phase markers.
    """

    # Action type normalization: maps keywords to canonical action types
    # Derived from comprehensive analysis of low_histamine_recipes.json
    ACTION_KEYWORDS = {
        # Cutting actions -> "chop"
        "chop": [
            "chop", "dice", "mince", "slice", "cut", "julienne", "cube",
            "shred", "quarter", "halve", "wedge", "matchstick"
        ],
        # Washing actions -> "wash"
        "wash": ["wash", "rinse", "clean", "drain"],
        # Peeling actions -> "peel"
        "peel": ["peel", "core", "trim", "remove skin"],
        # Heating oven -> "preheat"
        "preheat": ["preheat oven", "preheat"],
        # Boiling actions -> "boil"
        "boil": ["boil water", "bring to boil", "boil", "bring to a boil"],
        # Seasoning actions -> "season"
        "season": ["season", "salt ", "heavily salt", "generously salt"],
        # Grating actions -> "grate"
        "grate": ["grate", "zest", "grate finely", "grate directly"],
        # Mixing actions -> "mix"
        "mix": [
            "mix", "whisk", "combine", "stir", "fold", "beat", "toss",
            "work", "massage", "blend", "puree", "process", "pulse"
        ],
        # Toasting actions -> "toast"
        "toast": ["toast"],
        # Spiralizing actions -> "spiralize"
        "spiralize": ["spiralize"],
        # Roasting/baking actions -> "roast"
        "roast": ["roast", "bake"],
        # Simmering actions -> "simmer"
        "simmer": ["simmer", "poach", "braise", "stew"],
        # Frying actions -> "fry"
        "fry": [
            "fry", "sauté", "saute", "pan-fry", "stir-fry", "sear",
            "brown", "char", "blister", "pan-sear"
        ],
        # Marinating actions -> "marinate"
        "marinate": ["marinate", "marinade"],
        # Resting actions -> "rest"
        "rest": [
            "rest", "let sit", "let stand", "cool", "chill", "refrigerate",
            "cool down", "leave at room temperature"
        ],
        # Serving actions -> "serve"
        "serve": ["serve", "plate", "garnish", "top with", "arrange", "ladle"],
        # Heating actions -> "heat"
        "heat": ["heat oil", "heat ", "warm", "bring up slowly", "increase heat"],
        # Cooking actions -> "cook"
        "cook": ["cook", "steam"],
        # Cracking actions -> "crack"
        "crack": ["crack"],
        # Scoring actions -> "score"
        "score": ["score", "prick"],
        # Flipping actions -> "flip"
        "flip": ["flip", "turn", "toss"],
        # Removing actions -> "remove"
        "remove": ["remove from", "take out", "drain"],
        # Adding actions -> "add"
        "add": ["add", "pour", "drop", "thread onto", "place"],
        # Forming actions -> "form"
        "form": ["form", "shape", "roll", "mold"],
        # Spreading actions -> "spread"
        "spread": ["spread", "lay", "arrange"],
        # Dredging actions -> "dredge"
        "dredge": ["dredge", "coat", "dip"],
        # Covering actions -> "cover"
        "cover": ["cover"],
        # Reducing actions -> "reduce"
        "reduce": ["reduce heat", "reduce"],
        # Sprinkling actions -> "sprinkle"
        "sprinkle": ["sprinkle", "scatter", "dust"],
        # Creating actions -> "create"
        "create": ["create", "make"],
        # Deglaze actions -> "deglaze"
        "deglaze": ["deglaze", "scrape up"],
        # Returning actions -> "return"
        "return": ["return"],
        # Mashing actions -> "mash"
        "mash": ["mash", "pound", "crush"],
        # Rendering actions -> "render"
        "render": ["render"],
        # Juicing actions -> "juice"
        "juice": ["juice"],
        # Stuffing actions -> "stuff"
        "stuff": ["stuff", "fill"],
        # Rubbing actions -> "rub"
        "rub": ["rub"],
        # Pushing actions -> "push"
        "push": ["push to the side", "push"],
        # Scraping actions -> "scrape"
        "scrape": ["scrape"],
        # Tucking actions -> "tuck"
        "tuck": ["tuck"],
        # Threading actions -> "thread"
        "thread": ["thread"],
        # Finishing actions -> "finish"
        "finish": ["finish with", "finish"],
    }

    # Keywords that indicate passive steps (no active attention needed)
    PASSIVE_KEYWORDS = [
        # Long cooking without stirring
        "simmer", "bake", "roast", "braise", "stew",
        # Resting/waiting
        "rest", "marinate", "let sit", "let stand", "let batter rest",
        "cool", "chill", "refrigerate",
        # Preheating
        "preheat",
        # Covered cooking
        "cover and cook", "cover and steam",
        # Poaching
        "let sit for", "leave at room temperature",
        # Overnight/freezing
        "freeze overnight", "overnight",
        # Time-based passive indicators
        "for 15 minutes", "for 20 minutes", "for 30 minutes",
        "for 40 minutes", "for 45 minutes", "for 1 hour",
        "for 90 minutes", "undisturbed",
    ]

    # Equipment detection keywords
    OVEN_KEYWORDS = [
        "oven", "bake", "roast", "broil", "preheat", "baking sheet",
        "baking dish", "roasting", "425°F", "400°F", "350°F", "325°F"
    ]
    STOVETOP_KEYWORDS = [
        "simmer", "boil", "sauté", "saute", "fry", "pan", "stove",
        "heat", "burner", "skillet", "pot", "wok", "saucepan",
        "medium heat", "high heat", "low heat", "medium-high",
        "cook", "render", "sear", "brown",  # Active cooking keywords
        "375°F", "325°F", "450°F", "500°F"
    ]
    HANDS_FREE_KEYWORDS = [
        "rest", "marinate", "chill", "refrigerate", "cool",
        "let sit", "let stand", "leave at room temperature",
        "let batter rest", "freeze"
    ]

    # Phase detection keywords
    COOKING_KEYWORDS = [
        "cook", "bake", "roast", "simmer", "boil", "fry", "sauté",
        "saute", "heat", "sear", "brown", "render", "braise", "stew",
        "char", "grill", "steam", "poach"
    ]
    FINISHING_KEYWORDS = [
        "serve", "plate", "garnish", "top with", "drizzle",
        "sprinkle over", "finish with", "arrange"
    ]

    # Patterns indicating descriptive/explanatory text (not actionable steps)
    # These are sentences that describe what happens or explain cooking theory,
    # but don't provide actionable instructions.
    DESCRIPTIVE_STARTERS = [
        "the heat will",
        "the apples will",
        "the apple will",
        "the chicken fat will",
        "the raw apple",
        "the cooked apple",
        "the roasted apple",
        "the grated apple",
        "the tart apple",
        "the gentle acidity",
        "the apple acid",
        "the apples act",
        "the apple acts",
    ]

    # Quick actions that take minimal time (1-2 minutes)
    QUICK_ACTION_KEYWORDS = [
        "place", "arrange", "lay", "set", "put", "position",
        "pour", "drizzle", "add", "drop", "tuck", "thread",
        "crack", "flip", "turn", "transfer", "remove from",
        "take out", "push to the side", "push aside",
        "return to", "stir in", "fold in", "sprinkle",
    ]

    # Words to filter out when extracting ingredients
    FILTER_WORDS = {
        # Articles and pronouns
        "the", "a", "an", "it", "them", "they",
        # Quantity modifiers
        "half", "all", "remaining", "some", "more", "extra",
        # Freshness/quality descriptors
        "raw", "fresh", "tart", "crisp", "hot", "cold", "warm",
        # Color descriptors
        "green", "red", "yellow", "white", "purple",
        # Size/texture descriptors
        "small", "medium", "large", "thick", "thin", "fine", "finely",
        "thinly", "roughly", "generous", "generously", "heavy", "heavily",
        # Prepositions and conjunctions
        "into", "until", "with", "and", "or", "for", "to", "in", "on",
        "at", "over", "from", "onto", "through",
        # Cooking descriptors
        "immediately", "well", "briefly", "quickly", "slowly",
        "undisturbed", "constantly", "vigorously",
        # Measurement units
        "cup", "cups", "tbsp", "tsp", "teaspoon", "tablespoon",
        "inch", "inches", "cm", "minutes", "minute", "hour", "hours",
        "seconds", "degree", "degrees",
        # Cooking states
        "cooked", "poached", "emulsified", "diced", "chopped", "sliced",
        # Common parsing artifacts
        "s", "d", "lets", "let", "about", "just", "side", "sides",
        "first", "then", "back", "per", "each",
    }

    def parse_step(self, step: str, context: Dict) -> ParsedPrepStep:
        """
        Parse a single recipe step into structured data.

        Args:
            step: The raw step text.
            context: Additional context with:
                - recipe_name: Name of the recipe
                - recipe_total_time: Total prep time in minutes
                - total_steps: Number of steps in recipe
                - step_index: Index of this step in the recipe

        Returns:
            ParsedPrepStep with extracted action_type, ingredient, equipment, etc.
        """
        step_lower = step.lower()

        # Check if this is descriptive/explanatory text (not actionable)
        if self._is_descriptive_text(step_lower):
            return ParsedPrepStep(
                action_type="descriptive",
                ingredient="",
                can_batch=False,
                equipment=Equipment.HANDS_FREE,
                is_passive=True,
                phase=Phase.FINISHING,
                duration_minutes=0,
                raw_step=step,
                parse_source="heuristic",
            )

        action_type = self._extract_action_type(step_lower)
        ingredient = self._extract_ingredient(step_lower, action_type)
        equipment = self._detect_equipment(step_lower)
        is_passive = self._is_passive(step_lower)
        phase = self._detect_phase(
            step_lower,
            context.get("step_index", 0),
            context.get("total_steps", 1)
        )
        duration = self._estimate_duration(
            step_lower,
            context.get("recipe_total_time", 30),
            context.get("total_steps", 1),
        )
        can_batch = self._can_batch(action_type, ingredient)

        return ParsedPrepStep(
            action_type=action_type,
            ingredient=ingredient,
            can_batch=can_batch,
            equipment=equipment,
            is_passive=is_passive,
            phase=phase,
            duration_minutes=duration,
            raw_step=step,
            parse_source="heuristic",
        )

    def _is_descriptive_text(self, step_lower: str) -> bool:
        """
        Check if a step is descriptive/explanatory text rather than an action.

        Descriptive text explains what happens or provides cooking theory,
        but doesn't give actionable instructions.
        """
        # Check for known descriptive starter patterns
        for starter in self.DESCRIPTIVE_STARTERS:
            if step_lower.startswith(starter):
                return True

        # Check for sentences that start with "The" and describe outcomes
        # Pattern: "The X will/provides/acts as..." or "The X is..."
        if step_lower.startswith("the "):
            descriptive_verbs = [
                " will ", " provides ", " provide ", " acts as ",
                " act as ", " serves as ", " is key", " is the ",
                " gives ", " brings ", " creates ", " softens ",
                " dissolves ", " mimics ",
            ]
            for verb in descriptive_verbs:
                if verb in step_lower:
                    return True

        return False

    def parse_steps(self, steps: List[str], context: Dict) -> List[ParsedPrepStep]:
        """
        Parse multiple recipe steps into structured data.

        Args:
            steps: List of raw step texts.
            context: Additional context with:
                - recipe_name: Name of the recipe
                - recipe_total_time: Total prep time in minutes

        Returns:
            List of ParsedPrepStep objects in the same order as input steps.
        """
        total_steps = len(steps)
        parsed_steps = []

        for i, step in enumerate(steps):
            step_context = {
                **context,
                "step_index": i,
                "total_steps": total_steps,
            }
            parsed_steps.append(self.parse_step(step, step_context))

        return parsed_steps

    def _extract_action_type(self, step_lower: str) -> str:
        """Extract and normalize the action type from a step."""
        # Check for compound actions first (e.g., "peel and cube")
        for action_type, keywords in self.ACTION_KEYWORDS.items():
            for keyword in keywords:
                # Match whole word or at word boundaries
                if keyword in step_lower:
                    return action_type

        return "other"

    def _extract_ingredient(self, step_lower: str, action_type: str) -> str:
        """
        Extract the main ingredient from a step.

        Uses action type to find the ingredient that follows the action verb.
        """
        # Get the keywords for this action type
        keywords = self.ACTION_KEYWORDS.get(action_type, [])

        for keyword in keywords:
            if keyword in step_lower:
                parts = step_lower.split(keyword, 1)
                if len(parts) > 1:
                    ingredient_part = parts[1].strip()
                    # Remove parenthetical content
                    ingredient_part = re.sub(r'\([^)]*\)', '', ingredient_part)

                    words = ingredient_part.split()
                    if words:
                        # Try to find a valid ingredient word
                        for word in words:
                            clean_word = word.rstrip(".,;:")
                            if not clean_word:
                                continue
                            if clean_word[0].isdigit():
                                continue
                            if clean_word in self.FILTER_WORDS:
                                continue
                            if len(clean_word) <= 1:
                                continue
                            return clean_word
        return ""

    def _detect_equipment(self, step_lower: str) -> Equipment:
        """Detect which equipment category a step uses."""
        # Check for oven keywords first (explicit equipment)
        if any(kw in step_lower for kw in self.OVEN_KEYWORDS):
            return Equipment.OVEN

        # Check for stovetop keywords (active cooking) BEFORE hands-free
        # This prevents "cook lamb" from being classified as PREP_AREA
        if any(kw in step_lower for kw in self.STOVETOP_KEYWORDS):
            return Equipment.STOVETOP

        # Check hands-free last (passive steps like rest, marinate)
        if any(kw in step_lower for kw in self.HANDS_FREE_KEYWORDS):
            return Equipment.HANDS_FREE

        # Default to prep area (chopping, mixing, etc.)
        return Equipment.PREP_AREA

    def _is_passive(self, step_lower: str) -> bool:
        """Check if a step is passive (no active attention needed)."""
        return any(kw in step_lower for kw in self.PASSIVE_KEYWORDS)

    def _detect_phase(self, step_lower: str, step_index: int, total_steps: int) -> Phase:
        """Detect which cooking phase a step belongs to."""
        # Check for finishing keywords first
        if any(kw in step_lower for kw in self.FINISHING_KEYWORDS):
            return Phase.FINISHING

        # Check for cooking keywords
        if any(kw in step_lower for kw in self.COOKING_KEYWORDS):
            return Phase.COOKING

        # Use position-based heuristic for remaining steps
        if total_steps > 0:
            position_ratio = step_index / total_steps
            if position_ratio < 0.4:
                return Phase.PREP
            elif position_ratio < 0.85:
                return Phase.COOKING
            else:
                return Phase.FINISHING

        return Phase.PREP

    def _estimate_duration(self, step_lower: str, recipe_total_time: int, total_steps: int) -> int:
        """Estimate the duration of a step in minutes."""
        # Look for explicit time mentions
        time_match = re.search(r"(\d+)\s*(?:min|minute)", step_lower)
        if time_match:
            return int(time_match.group(1))

        # Check for hour mentions
        hour_match = re.search(r"(\d+)\s*(?:hour)", step_lower)
        if hour_match:
            return int(hour_match.group(1)) * 60

        # Time estimates by action type
        # Long passive cooking
        if any(kw in step_lower for kw in ["bake", "roast"]):
            return 30
        if "slow" in step_lower or "slowly" in step_lower:
            return 15
        if "braise" in step_lower:
            return 20

        # Medium-length cooking
        if "simmer" in step_lower:
            return 15
        if "cook" in step_lower:
            return 10
        if "render" in step_lower:
            return 10

        # Quick cooking
        if any(kw in step_lower for kw in ["sear", "brown", "char", "fry"]):
            return 5
        if "sauté" in step_lower or "saute" in step_lower:
            return 5

        # Prep work
        if any(kw in step_lower for kw in ["chop", "dice", "mince", "slice", "cube"]):
            return 3
        if any(kw in step_lower for kw in ["wash", "rinse"]):
            return 2
        if any(kw in step_lower for kw in ["peel", "core", "trim"]):
            return 2
        if any(kw in step_lower for kw in ["mix", "whisk", "stir", "toss", "combine"]):
            return 2
        if any(kw in step_lower for kw in ["grate", "zest", "julienne"]):
            return 2
        if any(kw in step_lower for kw in ["season", "salt"]):
            return 1

        # Quick actions (30 sec - 1 min, round up to 1)
        # These are placement, transfer, and simple arrangement actions
        cooking_keywords = ["cook", "sear", "fry", "bake", "roast", "simmer", "brown"]
        if any(kw in step_lower for kw in self.QUICK_ACTION_KEYWORDS):
            # Only count as quick if no cooking is involved
            if not any(cook_kw in step_lower for cook_kw in cooking_keywords):
                return 1

        # Waiting/resting
        if any(kw in step_lower for kw in ["rest", "let sit", "marinate"]):
            return 10

        # Preheating
        if "preheat" in step_lower:
            return 5

        # Serving/plating
        if any(kw in step_lower for kw in ["serve", "plate", "garnish"]):
            return 2

        # Default: divide recipe time by steps
        return max(2, recipe_total_time // max(1, total_steps))

    def _can_batch(self, action_type: str, ingredient: str) -> bool:
        """Check if a step can be batched with similar steps."""
        # Actions that can typically be batched
        batchable_actions = {
            "chop", "wash", "peel", "season", "grate", "mix",
            "toast", "form", "boil"
        }
        return action_type in batchable_actions and bool(ingredient)
