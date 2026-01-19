"""
Meal planning API routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import date, timedelta

logger = logging.getLogger(__name__)

from backend.db.database import get_db
from backend.db.models import User
from backend.api.dependencies import get_current_user
from backend.services.meal_service import MealPlanningService, db_meal_plan_to_schema
from backend.services.adaptive_service import AdaptiveService
from backend.services.audit_service import AuditService, get_client_ip, get_user_agent
from backend.models.schemas import (
    AuditAction, PrepStatus, AdaptiveEngineOutput,
    OptimizedPrepTimeline
)
from backend.engine.prep_optimizer import PrepOptimizer
from backend.errors import (
    ErrorCode,
    PlanNotFoundError,
    NoRecipesAvailableError,
    PlanGenerationError,
    PlanAdaptationError,
    PlanLimitExceededError,
)
from backend.config import settings
from backend.features import Feature
from backend.features.service import require_feature

router = APIRouter(prefix="/api/plans", tags=["meal-plans"])


# Request/Response schemas
class CreatePlanRequest(BaseModel):
    """Request to create a new meal plan."""
    start_date: date
    days: int = Field(
        default=settings.plan_default_days,
        ge=1,
        le=settings.plan_max_days,
        description=f"Number of days (1-{settings.plan_max_days})",
    )
    simplified: bool = Field(default=False, description="Use simplified recipes for catch-up")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2025-12-23",
                    "days": 5,
                    "simplified": False
                }
            ]
        }
    }

    @field_validator("start_date")
    @classmethod
    def start_date_not_in_past(cls, v: date) -> date:
        """Validate that start_date is not in the past."""
        today = date.today()
        if v < today:
            raise ValueError(f"start_date cannot be in the past (got {v}, today is {today})")
        # Also limit how far in the future (configurable limit)
        max_future = today + timedelta(days=settings.plan_max_future_days)
        if v > max_future:
            raise ValueError(
                f"start_date cannot be more than {settings.plan_max_future_days} days in the future (got {v})"
            )
        return v


class UpdatePrepStatusRequest(BaseModel):
    """Request to update meal prep status."""
    date: date
    meal_type: str = Field(..., description="breakfast, lunch, or dinner")
    status: PrepStatus

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "date": "2025-12-23",
                    "meal_type": "dinner",
                    "status": "DONE"
                }
            ]
        }
    }


class MealPlanResponse(BaseModel):
    """Meal plan response."""
    id: UUID
    user_id: UUID
    diet_type: str
    start_date: date
    end_date: date
    meals: List[dict]
    created_at: str
    updated_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "660e8400-e29b-41d4-a716-446655440001",
                    "diet_type": "low_histamine",
                    "start_date": "2025-12-23",
                    "end_date": "2025-12-27",
                    "meals": [
                        {
                            "id": "770e8400-e29b-41d4-a716-446655440002",
                            "date": "2025-12-23",
                            "meal_type": "breakfast",
                            "prep_status": "PENDING",
                            "prep_completed_at": None,
                            "recipe": {
                                "id": "880e8400-e29b-41d4-a716-446655440003",
                                "name": "Oatmeal with Blueberries",
                                "meal_type": "breakfast",
                                "prep_time_minutes": 15,
                                "diet_tags": ["low_histamine"]
                            }
                        }
                    ],
                    "created_at": "2025-12-21T10:00:00",
                    "updated_at": "2025-12-21T10:00:00"
                }
            ]
        }
    }

    @staticmethod
    def from_db_plan(db_plan, db: Session):
        """Convert database plan to response."""
        schema_plan = db_meal_plan_to_schema(db_plan, db)
        return MealPlanResponse(
            id=schema_plan.id,
            user_id=schema_plan.user_id,
            diet_type=schema_plan.diet_type.value,
            start_date=schema_plan.start_date,
            end_date=schema_plan.end_date,
            meals=[
                {
                    "id": meal.recipe.id,
                    "date": str(meal.date),
                    "meal_type": meal.meal_type,
                    "prep_status": meal.prep_status.value,
                    "prep_completed_at": meal.prep_completed_at.isoformat() if meal.prep_completed_at else None,
                    "recipe": {
                        "id": meal.recipe.id,
                        "name": meal.recipe.name,
                        "meal_type": meal.recipe.meal_type,
                        "ingredients": [ing.model_dump() for ing in meal.recipe.ingredients],
                        "prep_steps": meal.recipe.prep_steps,
                        "prep_time_minutes": meal.recipe.prep_time_minutes,
                        "reusability_index": meal.recipe.reusability_index,
                        "diet_tags": meal.recipe.diet_tags,
                    },
                }
                for meal in schema_plan.meals
            ],
            created_at=schema_plan.created_at.isoformat(),
            updated_at=db_plan.updated_at.isoformat(),
        )


class AdaptPlanRequest(BaseModel):
    """Request to adapt a meal plan."""
    current_date: date = Field(default_factory=date.today)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_date": "2025-12-23"
                }
            ]
        }
    }


class SwapMealRequest(BaseModel):
    """Request to swap a meal's recipe."""
    date: date
    meal_type: str = Field(..., description="breakfast, lunch, or dinner")
    new_recipe_id: UUID

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "date": "2025-12-23",
                    "meal_type": "dinner",
                    "new_recipe_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }
    }


class DuplicatePlanRequest(BaseModel):
    """Request to duplicate a meal plan to a new date range."""
    start_date: date = Field(..., description="New start date for the duplicated plan")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2025-12-30"
                }
            ]
        }
    }

    @field_validator("start_date")
    @classmethod
    def start_date_not_in_past(cls, v: date) -> date:
        """Validate that start_date is not in the past."""
        today = date.today()
        if v < today:
            raise ValueError(f"start_date cannot be in the past (got {v}, today is {today})")
        # Also limit how far in the future (configurable limit)
        max_future = today + timedelta(days=settings.plan_max_future_days)
        if v > max_future:
            raise ValueError(
                f"start_date cannot be more than {settings.plan_max_future_days} days in the future (got {v})"
            )
        return v


# ============================================================================
# Response Models for Consistent API Responses
# ============================================================================


class ExpiringItemResponse(BaseModel):
    """An item in the fridge that is expiring soon."""
    name: str
    days_remaining: int
    quantity: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "spinach",
                    "days_remaining": 1,
                    "quantity": "200g"
                }
            ]
        }
    }


class PendingMealResponse(BaseModel):
    """A pending meal in the plan."""
    date: str
    meal_type: str
    recipe: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "date": "2025-12-23",
                    "meal_type": "dinner",
                    "recipe": "Grilled Chicken Salad"
                }
            ]
        }
    }


class CatchUpSuggestionsResponse(BaseModel):
    """Response with catch-up suggestions for a plan."""
    missed_preps: List[str]
    expiring_items: List[ExpiringItemResponse]
    pending_meals: List[PendingMealResponse]
    needs_adaptation: bool

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "missed_preps": ["2025-12-22"],
                    "expiring_items": [
                        {"name": "spinach", "days_remaining": 1, "quantity": "200g"}
                    ],
                    "pending_meals": [
                        {"date": "2025-12-23", "meal_type": "dinner", "recipe": "Grilled Chicken Salad"}
                    ],
                    "needs_adaptation": True
                }
            ]
        }
    }


class PrepStatusUpdateResponse(BaseModel):
    """Response after updating meal prep status."""
    message: str
    date: str
    meal_type: str
    status: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Meal status updated to DONE",
                    "date": "2025-12-23",
                    "meal_type": "dinner",
                    "status": "DONE"
                }
            ]
        }
    }


class MealSwapResponse(BaseModel):
    """Response after swapping a meal's recipe."""
    message: str
    date: str
    meal_type: str
    new_recipe_id: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Meal swapped successfully",
                    "date": "2025-12-23",
                    "meal_type": "dinner",
                    "new_recipe_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }
    }


class CompatibleRecipeResponse(BaseModel):
    """A recipe compatible with user's diet for meal swapping."""
    id: str
    name: str
    meal_type: str
    prep_time_minutes: int
    diet_tags: List[str]
    servings: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Grilled Salmon with Herbs",
                    "meal_type": "dinner",
                    "prep_time_minutes": 25,
                    "diet_tags": ["low_histamine", "gluten_free"],
                    "servings": 2
                }
            ]
        }
    }


class CompatibleRecipesResponse(BaseModel):
    """Response with compatible recipes for a meal type."""
    recipes: List[CompatibleRecipeResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recipes": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "Grilled Salmon with Herbs",
                            "meal_type": "dinner",
                            "prep_time_minutes": 25,
                            "diet_tags": ["low_histamine"],
                            "servings": 2
                        },
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440001",
                            "name": "Herb Roasted Chicken",
                            "meal_type": "dinner",
                            "prep_time_minutes": 45,
                            "diet_tags": ["low_histamine", "dairy_free"],
                            "servings": 4
                        }
                    ],
                    "total": 2
                }
            ]
        }
    }


@router.post("", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    request: CreatePlanRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new meal plan.

    Creates a diet-compliant meal plan for the specified number of days.
    """
    service = MealPlanningService(db)

    # Check plan limit (0 = unlimited)
    if settings.max_plans_per_user > 0:
        current_count = service.count_user_plans(current_user)
        if current_count >= settings.max_plans_per_user:
            error = PlanLimitExceededError(current_count, settings.max_plans_per_user)
            raise HTTPException(
                status_code=error.status_code,
                detail={
                    "error_code": error.error_code.value,
                    "message": error.message,
                    "details": error.details,
                },
            )

    try:
        db_plan = service.generate_plan(
            user=current_user,
            start_date=request.start_date,
            days=request.days,
            simplified=request.simplified,
        )

        # Audit log: plan creation
        audit_service = AuditService(db)
        audit_service.log(
            action=AuditAction.CREATE,
            resource_type="plan",
            user_id=current_user.id,
            resource_id=db_plan.id,
            details={
                "start_date": str(request.start_date),
                "days": request.days,
                "simplified": request.simplified,
                "diet_type": current_user.diet_type.value,
            },
            ip_address=get_client_ip(http_request),
            user_agent=get_user_agent(http_request),
        )

        return MealPlanResponse.from_db_plan(db_plan, db)

    except NoRecipesAvailableError as e:
        logger.warning(f"No recipes available for plan generation: {e.details}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error_code": e.error_code.value,
                "message": e.message,
                "details": e.details,
            },
        )
    except SQLAlchemyError as e:
        logger.exception("Database error during meal plan generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
                "message": "Database error occurred while generating meal plan. Please try again.",
                "details": {"error_type": type(e).__name__},
            },
        )
    except Exception as e:
        logger.exception("Failed to generate meal plan")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.PLAN_GENERATION_FAILED.value,
                "message": f"Failed to generate meal plan: {str(e)}",
                "details": {
                    "diet_type": current_user.diet_type.value,
                    "days": request.days,
                    "error_type": type(e).__name__,
                },
            },
        )


@router.get("", response_model=List[MealPlanResponse])
async def get_meal_plans(
    limit: int = settings.pagination_plans_default_limit,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all meal plans for the current user.

    Returns plans ordered by creation date (newest first).
    """
    service = MealPlanningService(db)
    db_plans = service.get_user_plans(current_user, limit=limit, skip=skip)

    return [MealPlanResponse.from_db_plan(plan, db) for plan in db_plans]


@router.get("/{plan_id}", response_model=MealPlanResponse)
async def get_meal_plan(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific meal plan by ID.
    """
    service = MealPlanningService(db)
    db_plan = service.get_plan(plan_id, current_user)

    if not db_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found",
        )

    return MealPlanResponse.from_db_plan(db_plan, db)


@router.patch("/{plan_id}/mark-prep", response_model=PrepStatusUpdateResponse, status_code=status.HTTP_200_OK)
async def mark_prep_status(
    plan_id: UUID,
    request: UpdatePrepStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark a meal as done or skipped.

    Updates the prep status for a specific meal in the plan.
    """
    service = MealPlanningService(db)

    meal_slot = service.update_prep_status(
        plan_id=plan_id,
        target_date=request.date,
        meal_type=request.meal_type,
        status=request.status,
        user=current_user,
    )

    if not meal_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found in plan",
        )

    return PrepStatusUpdateResponse(
        message=f"Meal status updated to {request.status.value}",
        date=str(request.date),
        meal_type=request.meal_type,
        status=request.status.value,
    )


@router.post("/{plan_id}/adapt", response_model=AdaptiveEngineOutput)
async def adapt_meal_plan(
    plan_id: UUID,
    request: AdaptPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature(Feature.PLAN_ADAPTATION)),
):
    """
    Adapt a meal plan based on missed preps and ingredient freshness.

    The adaptive engine will:
    - Detect missed prep days
    - Prioritize expiring ingredients
    - Suggest simplified alternatives
    - Provide transparent adaptation explanations

    **Feature flag**: Requires `plan_adaptation` feature to be enabled.
    """
    service = AdaptiveService(db)

    try:
        output = service.adapt_plan(
            user=current_user,
            plan_id=plan_id,
            current_date=request.current_date,
        )

        return output

    except ValueError as e:
        # Plan not found or other validation error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": ErrorCode.PLAN_NOT_FOUND.value,
                "message": str(e),
                "details": {"plan_id": str(plan_id)},
            },
        )
    except SQLAlchemyError as e:
        logger.exception(f"Database error during plan adaptation for plan {plan_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
                "message": "Database error occurred while adapting plan. Please try again.",
                "details": {"plan_id": str(plan_id), "error_type": type(e).__name__},
            },
        )
    except Exception as e:
        logger.exception(f"Failed to adapt plan {plan_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.PLAN_ADAPTATION_FAILED.value,
                "message": f"Failed to adapt meal plan: {str(e)}",
                "details": {
                    "plan_id": str(plan_id),
                    "current_date": str(request.current_date),
                    "error_type": type(e).__name__,
                },
            },
        )


@router.get("/{plan_id}/catch-up", response_model=CatchUpSuggestionsResponse)
async def get_catch_up_view(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get catch-up suggestions without modifying the plan.

    Shows:
    - Missed prep days
    - Expiring ingredients
    - Pending meals
    - Whether adaptation is recommended
    """
    service = AdaptiveService(db)

    try:
        suggestions = service.get_catch_up_suggestions(
            user=current_user,
            plan_id=plan_id,
            current_date=date.today(),
        )

        return CatchUpSuggestionsResponse(
            missed_preps=suggestions["missed_preps"],
            expiring_items=[
                ExpiringItemResponse(**item) for item in suggestions["expiring_items"]
            ],
            pending_meals=[
                PendingMealResponse(**meal) for meal in suggestions["pending_meals"]
            ],
            needs_adaptation=suggestions["needs_adaptation"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_plan(
    plan_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a meal plan.
    """
    service = MealPlanningService(db)
    deleted = service.delete_plan(plan_id, current_user)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found",
        )

    # Audit log: plan deletion
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.DELETE,
        resource_type="plan",
        user_id=current_user.id,
        resource_id=plan_id,
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return None


@router.post("/{plan_id}/duplicate", response_model=MealPlanResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_meal_plan(
    plan_id: UUID,
    request: DuplicatePlanRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature(Feature.PLAN_DUPLICATION)),
):
    """
    Duplicate an existing meal plan to a new date range.

    Creates a copy of the plan with all meal slots, adjusting dates
    relative to the new start date. All prep statuses are reset to PENDING.

    This is useful for reusing a successful plan for a future week.

    **Feature flag**: Requires `plan_duplication` feature to be enabled.
    """
    service = MealPlanningService(db)

    try:
        new_plan = service.duplicate_plan(
            plan_id=plan_id,
            new_start_date=request.start_date,
            user=current_user,
        )

        if not new_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": ErrorCode.PLAN_NOT_FOUND.value,
                    "message": "Source meal plan not found",
                    "details": {"plan_id": str(plan_id)},
                },
            )

        # Audit log: plan duplication
        audit_service = AuditService(db)
        audit_service.log(
            action=AuditAction.CREATE,
            resource_type="plan",
            user_id=current_user.id,
            resource_id=new_plan.id,
            details={
                "source_plan_id": str(plan_id),
                "new_start_date": str(request.start_date),
                "diet_type": new_plan.diet_type.value,
                "duplicated": True,
            },
            ip_address=get_client_ip(http_request),
            user_agent=get_user_agent(http_request),
        )

        return MealPlanResponse.from_db_plan(new_plan, db)

    except HTTPException:
        # Re-raise HTTP exceptions (like 404 not found)
        raise
    except SQLAlchemyError as e:
        logger.exception(f"Database error during plan duplication for plan {plan_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
                "message": "Database error occurred while duplicating plan. Please try again.",
                "details": {"plan_id": str(plan_id), "error_type": type(e).__name__},
            },
        )
    except Exception as e:
        logger.exception(f"Failed to duplicate plan {plan_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.PLAN_GENERATION_FAILED.value,
                "message": f"Failed to duplicate meal plan: {str(e)}",
                "details": {
                    "plan_id": str(plan_id),
                    "new_start_date": str(request.start_date),
                    "error_type": type(e).__name__,
                },
            },
        )


@router.get(
    "/{plan_id}/prep-timeline",
    response_model=OptimizedPrepTimeline
)
async def get_prep_timeline(
    plan_id: UUID,
    prep_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get optimized prep timeline for a specific date.

    Returns a batched preparation schedule that minimizes total prep time
    by grouping similar tasks (chopping, washing, preheating) together.

    The timeline includes:
    - Ordered list of prep steps
    - Time estimates for each step
    - Total prep time
    - Time saved through batching
    """
    service = MealPlanningService(db)
    db_plan = service.get_plan(plan_id, current_user)

    if not db_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found",
        )

    # Convert to schema for the optimizer
    schema_plan = db_meal_plan_to_schema(db_plan, db)

    # Check if the date is within the plan's range
    if prep_date < schema_plan.start_date or prep_date > schema_plan.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date {prep_date} is outside plan range ({schema_plan.start_date} to {schema_plan.end_date})",
        )

    # Generate optimized timeline
    optimizer = PrepOptimizer()
    timeline = optimizer.optimize_meal_prep(schema_plan, prep_date)

    return timeline


@router.patch("/{plan_id}/swap-meal", response_model=MealSwapResponse, status_code=status.HTTP_200_OK)
async def swap_meal(
    plan_id: UUID,
    request: SwapMealRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature(Feature.MEAL_SWAP)),
):
    """
    Swap a meal's recipe with a different recipe.

    Replaces the recipe for a specific meal slot while respecting
    the user's diet type and exclusions. The prep status is reset
    to PENDING after the swap.

    **Feature flag**: Requires `meal_swap` feature to be enabled.
    """
    service = MealPlanningService(db)

    meal_slot = service.swap_meal(
        plan_id=plan_id,
        target_date=request.date,
        meal_type=request.meal_type,
        new_recipe_id=request.new_recipe_id,
        user=current_user,
    )

    if not meal_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found in plan or recipe not found",
        )

    return MealSwapResponse(
        message="Meal swapped successfully",
        date=str(request.date),
        meal_type=request.meal_type,
        new_recipe_id=str(request.new_recipe_id),
    )


@router.get("/{plan_id}/compatible-recipes", response_model=CompatibleRecipesResponse)
async def get_compatible_recipes(
    plan_id: UUID,
    meal_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recipes compatible with the user's diet for a specific meal type.

    Returns recipes that:
    - Match the user's diet type (e.g., low-histamine)
    - Match the specified meal type (breakfast, lunch, dinner)
    - Don't contain any of the user's excluded ingredients
    """
    service = MealPlanningService(db)

    # Verify plan belongs to user
    db_plan = service.get_plan(plan_id, current_user)
    if not db_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found",
        )

    # Get compatible recipes
    recipes = service.get_compatible_recipes(current_user, meal_type)

    return CompatibleRecipesResponse(
        recipes=[
            CompatibleRecipeResponse(
                id=str(recipe.id),
                name=recipe.name,
                meal_type=recipe.meal_type,
                prep_time_minutes=recipe.prep_time_minutes,
                diet_tags=recipe.diet_tags,
                servings=recipe.servings,
            )
            for recipe in recipes
        ],
        total=len(recipes),
    )
