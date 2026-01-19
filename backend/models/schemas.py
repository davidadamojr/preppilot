"""
Pydantic data models for PrepPilot adaptive engine.
"""
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class UserRole(str, Enum):
    """User roles for access control."""
    USER = "user"
    ADMIN = "admin"


class AuditAction(str, Enum):
    """Actions that can be audited."""
    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"

    # Resource CRUD actions
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Bulk operations
    BULK_CREATE = "bulk_create"
    BULK_DELETE = "bulk_delete"

    # Special actions
    EXPORT = "export"
    EMAIL_SENT = "email_sent"
    ROLE_CHANGE = "role_change"
    STATUS_CHANGE = "status_change"


class DietType(str, Enum):
    """Supported diet types."""
    LOW_HISTAMINE = "low_histamine"
    LOW_HISTAMINE_LOW_OXALATE = "low_histamine_low_oxalate"
    FODMAP = "fodmap"
    FRUCTOSE_FREE = "fructose_free"


# Compound diet types that require ALL listed tags to be present
COMPOUND_DIET_TYPES: Dict[str, List[str]] = {
    "low_histamine_low_oxalate": ["low_histamine", "low_oxalate"],
}


class PrepStatus(str, Enum):
    """Status of a prep task."""
    PENDING = "PENDING"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class DietaryExclusion(str, Enum):
    """Common dietary exclusions and allergens."""
    # Common allergens (FDA top 9)
    PEANUTS = "peanuts"
    TREE_NUTS = "tree_nuts"
    SHELLFISH = "shellfish"
    FISH = "fish"
    EGGS = "eggs"
    MILK = "milk"
    SOY = "soy"
    WHEAT = "wheat"
    SESAME = "sesame"

    # Additional common exclusions
    GLUTEN = "gluten"
    DAIRY = "dairy"
    NIGHTSHADES = "nightshades"
    SEAFOOD = "seafood"
    CELERY = "celery"
    MUSTARD = "mustard"
    SULFITES = "sulfites"
    CORN = "corn"

    # Category exclusions
    ALL_NUTS = "all_nuts"
    ALL_SEAFOOD = "all_seafood"
    RED_MEAT = "red_meat"
    POULTRY = "poultry"
    PORK = "pork"


# Category taxonomy - maps exclusion categories to ingredient patterns
EXCLUSION_CATEGORIES: Dict[str, List[str]] = {
    "tree_nuts": ["almonds", "cashews", "walnuts", "pecans", "pistachios", "hazelnuts", "macadamia", "pine_nuts", "brazil_nuts"],
    "shellfish": ["shrimp", "crab", "lobster", "crayfish", "prawns", "mussels", "clams", "oysters", "scallops"],
    "fish": ["salmon", "tuna", "cod", "halibut", "trout", "tilapia", "mackerel", "sardines", "anchovies"],
    "seafood": ["salmon", "tuna", "cod", "halibut", "trout", "tilapia", "mackerel", "sardines", "anchovies",
                "shrimp", "crab", "lobster", "crayfish", "prawns", "mussels", "clams", "oysters", "scallops"],
    "all_seafood": ["salmon", "tuna", "cod", "halibut", "trout", "tilapia", "mackerel", "sardines", "anchovies",
                    "shrimp", "crab", "lobster", "crayfish", "prawns", "mussels", "clams", "oysters", "scallops"],
    "nightshades": ["tomato", "tomatoes", "pepper", "peppers", "bell_pepper", "eggplant", "aubergine", "paprika", "cayenne", "chili"],
    "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "sour_cream", "cheddar", "mozzarella", "parmesan", "feta"],
    "gluten": ["wheat", "barley", "rye", "spelt", "wheat_flour", "bread_crumbs", "pasta"],
    "all_nuts": ["peanuts", "almonds", "cashews", "walnuts", "pecans", "pistachios", "hazelnuts", "macadamia", "pine_nuts", "brazil_nuts"],
    "red_meat": ["beef", "lamb", "pork", "veal", "venison", "bison"],
    "poultry": ["chicken", "turkey", "duck", "chicken_breast", "chicken_thighs"],
    "pork": ["pork", "bacon", "ham", "pork_chops", "sausage"],
}


class Ingredient(BaseModel):
    """Ingredient with freshness tracking."""
    name: str = Field(..., description="Name of the ingredient")
    freshness_days: int = Field(..., ge=1, description="Days until ingredient expires")
    quantity: str = Field(..., description="Quantity needed (e.g., '500g', '2 cups')")
    category: Optional[str] = Field(None, description="Category (protein, vegetable, herb, etc.)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "chicken breast",
                    "freshness_days": 3,
                    "quantity": "500g",
                    "category": "protein"
                }
            ]
        }
    }

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Ingredient name cannot be empty')
        return v.strip().lower()


class Recipe(BaseModel):
    """Recipe with diet compliance and prep metadata."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique recipe ID")
    name: str = Field(..., description="Recipe name")
    diet_tags: List[str] = Field(..., description="Compatible diet types")
    meal_type: str = Field(..., description="breakfast, lunch, dinner, or snack")
    ingredients: List[Ingredient] = Field(..., description="List of ingredients")
    prep_steps: List[str] = Field(..., description="Ordered preparation steps")
    prep_time_minutes: int = Field(..., ge=1, description="Total prep time in minutes")
    reusability_index: float = Field(..., ge=0.0, le=1.0, description="How well ingredients can be reused (0-1)")
    servings: int = Field(default=2, ge=1, description="Number of servings")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Grilled Chicken Salad",
                    "diet_tags": ["low_histamine", "gluten_free"],
                    "meal_type": "lunch",
                    "ingredients": [
                        {"name": "chicken breast", "freshness_days": 3, "quantity": "200g", "category": "protein"}
                    ],
                    "prep_steps": ["Season chicken", "Grill for 6-8 minutes per side", "Slice and serve"],
                    "prep_time_minutes": 25,
                    "reusability_index": 0.7,
                    "servings": 2
                }
            ]
        }
    }

    @field_validator('diet_tags')
    @classmethod
    def diet_tags_must_not_be_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('Recipe must have at least one diet tag')
        return v


class FridgeItem(BaseModel):
    """Item in fridge with current freshness state."""
    ingredient_name: str
    quantity: str
    days_remaining: int = Field(..., ge=0, description="Days until expiration")
    added_date: date
    original_freshness_days: int

    @property
    def freshness_percentage(self) -> float:
        """Calculate freshness as percentage (0-100)."""
        if self.original_freshness_days == 0:
            return 0.0
        return (self.days_remaining / self.original_freshness_days) * 100


class FridgeState(BaseModel):
    """Current state of ingredient inventory."""
    user_id: UUID
    items: List[FridgeItem] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    def get_item(self, ingredient_name: str) -> Optional[FridgeItem]:
        """Get item by ingredient name."""
        for item in self.items:
            if item.ingredient_name.lower() == ingredient_name.lower():
                return item
        return None

    def add_item(self, item: FridgeItem) -> None:
        """Add or update item in fridge."""
        existing = self.get_item(item.ingredient_name)
        if existing:
            self.items.remove(existing)
        self.items.append(item)

    def get_expiring_soon(self, days_threshold: int = 2) -> List[FridgeItem]:
        """Get items expiring within threshold days."""
        return [item for item in self.items if 0 < item.days_remaining <= days_threshold]


class MealSlot(BaseModel):
    """A meal slot in the schedule."""
    date: date
    meal_type: str  # breakfast, lunch, dinner
    recipe: Recipe
    prep_status: PrepStatus = PrepStatus.PENDING
    prep_completed_at: Optional[datetime] = None


class MealPlan(BaseModel):
    """A complete meal plan with schedule."""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    diet_type: DietType
    start_date: date
    end_date: date
    meals: List[MealSlot] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    def get_meals_by_date(self, target_date: date) -> List[MealSlot]:
        """Get all meals for a specific date."""
        return [meal for meal in self.meals if meal.date == target_date]

    def get_pending_meals(self) -> List[MealSlot]:
        """Get all pending meals."""
        return [meal for meal in self.meals if meal.prep_status == PrepStatus.PENDING]

    def get_missed_preps(self, current_date: date) -> List[date]:
        """Get dates with skipped or overdue preps."""
        missed = []
        for meal in self.meals:
            if meal.date < current_date and meal.prep_status != PrepStatus.DONE:
                if meal.date not in missed:
                    missed.append(meal.date)
        return sorted(missed)


class AdaptiveEngineInput(BaseModel):
    """Input to the adaptive replanning engine."""
    user_id: UUID
    diet_type: DietType
    current_plan: MealPlan
    fridge_state: FridgeState
    missed_preps: List[date]
    current_date: date = Field(default_factory=date.today)
    dietary_exclusions: List[str] = Field(
        default_factory=list,
        description="List of excluded ingredients or categories"
    )
    user_constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional constraints like max_prep_time, energy_level"
    )


class AdaptationReason(BaseModel):
    """Explanation for a single adaptation decision."""
    type: str = Field(..., description="Type of adaptation: reorder, substitute, simplify, skip")
    affected_date: date
    original_meal: Optional[str] = None
    new_meal: Optional[str] = None
    reason: str = Field(..., description="Human-readable explanation")


class AdaptiveEngineOutput(BaseModel):
    """Output from the adaptive replanning engine."""
    new_plan: MealPlan
    adaptation_summary: List[AdaptationReason]
    grocery_adjustments: List[str] = Field(
        default_factory=list,
        description="Changes to shopping list"
    )
    priority_ingredients: List[str] = Field(
        default_factory=list,
        description="Ingredients that need immediate attention"
    )
    estimated_recovery_time_minutes: int = Field(
        default=0,
        description="Total time needed to catch up"
    )


class EquipmentType(str, Enum):
    """Equipment categories for scheduling and conflict detection."""

    OVEN = "oven"
    STOVETOP = "stovetop"
    PREP_AREA = "prep_area"
    HANDS_FREE = "hands_free"


class CookingPhase(str, Enum):
    """Cooking phases for timeline organization."""

    PREP = "prep"
    COOKING = "cooking"
    FINISHING = "finishing"


class PrepStep(BaseModel):
    """A single preparation step with context."""
    step_number: int
    action: str
    ingredient: Optional[str] = None
    duration_minutes: int
    can_batch: bool = Field(
        default=False,
        description="Whether this step can be batched with others"
    )
    batch_key: Optional[str] = Field(
        default=None,
        description="Key for grouping batchable steps"
    )
    source_recipes: List[str] = Field(
        default_factory=list,
        description="Names of recipes this step originates from"
    )
    equipment: Optional[EquipmentType] = Field(
        default=None,
        description="Equipment required: oven, stovetop, prep_area, or hands_free"
    )
    is_passive: bool = Field(
        default=False,
        description="True if step doesn't require active attention (simmer, rest, bake)"
    )
    phase: Optional[CookingPhase] = Field(
        default=None,
        description="Cooking phase: prep, cooking, or finishing"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "step_number": 1,
                    "action": "Chop vegetables",
                    "ingredient": "carrots",
                    "duration_minutes": 5,
                    "can_batch": True,
                    "batch_key": "chop",
                    "source_recipes": ["Fresh Herb Chicken Bowl with Rice"],
                    "equipment": "prep_area",
                    "is_passive": False,
                    "phase": "prep"
                }
            ]
        }
    }


class OptimizedPrepTimeline(BaseModel):
    """Optimized preparation timeline with batched steps."""
    total_time_minutes: int
    steps: List[PrepStep]
    batched_savings_minutes: int = Field(
        default=0,
        description="Time saved through batching"
    )
    prep_date: date

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_time_minutes": 45,
                    "steps": [
                        {"step_number": 1, "action": "Chop all vegetables", "duration_minutes": 10, "can_batch": True, "batch_key": "chop"},
                        {"step_number": 2, "action": "Season chicken", "ingredient": "chicken breast", "duration_minutes": 5, "can_batch": False},
                        {"step_number": 3, "action": "Grill chicken", "ingredient": "chicken breast", "duration_minutes": 15, "can_batch": False}
                    ],
                    "batched_savings_minutes": 8,
                    "prep_date": "2025-12-23"
                }
            ]
        }
    }
