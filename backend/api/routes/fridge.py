"""
Fridge inventory management API routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

from backend.db.database import get_db
from backend.db.models import User, FridgeItem as DBFridgeItem
from backend.api.dependencies import get_current_user
from backend.services.fridge_service import FridgeService
from backend.services.audit_service import AuditService, get_client_ip, get_user_agent
from backend.models.schemas import AuditAction, FridgeState
from backend.utils.sanitization import SanitizedStr
from backend.errors import ErrorCode
from backend.config import settings
from backend.features import Feature
from backend.features.service import require_feature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fridge", tags=["fridge"])


# Request/Response schemas
class AddItemRequest(BaseModel):
    """Request to add a single item to fridge."""
    ingredient_name: SanitizedStr = Field(..., min_length=1, max_length=255)
    quantity: SanitizedStr = Field(..., min_length=1, max_length=100, description="e.g., '500g', '2 cups'")
    freshness_days: int = Field(
        ...,
        ge=1,
        le=settings.fridge_max_freshness_days,
        description="Days until expiration",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ingredient_name": "chicken breast",
                    "quantity": "500g",
                    "freshness_days": 3
                }
            ]
        }
    }


class AddItemsBulkRequest(BaseModel):
    """Request to add multiple items to fridge."""
    items: List[AddItemRequest]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {"ingredient_name": "chicken breast", "quantity": "500g", "freshness_days": 3},
                        {"ingredient_name": "broccoli", "quantity": "2 heads", "freshness_days": 5},
                        {"ingredient_name": "carrots", "quantity": "6 medium", "freshness_days": 14}
                    ]
                }
            ]
        }
    }


class UpdateItemRequest(BaseModel):
    """Request to update a fridge item."""
    quantity: Optional[SanitizedStr] = Field(None, min_length=1, max_length=100, description="e.g., '500g', '2 cups'")
    days_remaining: Optional[int] = Field(
        None,
        ge=0,
        le=settings.fridge_max_freshness_days,
        description="Days until expiration",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "quantity": "300g",
                    "days_remaining": 2
                }
            ]
        }
    }


class FridgeItemResponse(BaseModel):
    """Single fridge item response."""
    id: UUID
    ingredient_name: str
    quantity: str
    days_remaining: int
    added_date: str
    original_freshness_days: int
    freshness_percentage: float

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "ingredient_name": "chicken breast",
                    "quantity": "500g",
                    "days_remaining": 2,
                    "added_date": "2025-12-20",
                    "original_freshness_days": 3,
                    "freshness_percentage": 66.67
                }
            ]
        }
    }


class FridgeStateResponse(BaseModel):
    """Complete fridge state response."""
    user_id: UUID
    items: List[FridgeItemResponse]
    total_items: int
    expiring_soon_count: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "items": [
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440001",
                            "ingredient_name": "chicken breast",
                            "quantity": "500g",
                            "days_remaining": 2,
                            "added_date": "2025-12-20",
                            "original_freshness_days": 3,
                            "freshness_percentage": 66.67
                        },
                        {
                            "id": "660e8400-e29b-41d4-a716-446655440002",
                            "ingredient_name": "spinach",
                            "quantity": "200g",
                            "days_remaining": 1,
                            "added_date": "2025-12-19",
                            "original_freshness_days": 5,
                            "freshness_percentage": 20.0
                        }
                    ],
                    "total_items": 2,
                    "expiring_soon_count": 1
                }
            ]
        }
    }


@router.get("", response_model=FridgeStateResponse)
async def get_fridge_state(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current fridge inventory.

    Returns all items with freshness information.
    """
    service = FridgeService(db)
    fridge_state = service.get_fridge_state(current_user)

    # Get actual DB items for full response
    db_items = db.query(DBFridgeItem).filter(
        DBFridgeItem.user_id == current_user.id
    ).all()

    items_response = [
        FridgeItemResponse(
            id=item.id,
            ingredient_name=item.ingredient_name,
            quantity=item.quantity,
            days_remaining=item.days_remaining,
            added_date=item.added_date.isoformat(),
            original_freshness_days=item.original_freshness_days,
            freshness_percentage=item.freshness_percentage,
        )
        for item in db_items
    ]

    expiring_items = service.get_expiring_items(current_user, days_threshold=2)

    return FridgeStateResponse(
        user_id=current_user.id,
        items=items_response,
        total_items=len(items_response),
        expiring_soon_count=len(expiring_items),
    )


@router.post("/items", response_model=FridgeItemResponse, status_code=status.HTTP_201_CREATED)
async def add_fridge_item(
    request: AddItemRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a single item to fridge.

    If item already exists, quantities will be combined and fresher expiration used.
    """
    service = FridgeService(db)

    try:
        db_item = service.add_item(
            user=current_user,
            ingredient_name=request.ingredient_name,
            quantity=request.quantity,
            freshness_days=request.freshness_days,
        )

        # Audit log: fridge item added
        audit_service = AuditService(db)
        audit_service.log(
            action=AuditAction.CREATE,
            resource_type="fridge",
            user_id=current_user.id,
            resource_id=db_item.id,
            details={
                "ingredient_name": request.ingredient_name,
                "quantity": request.quantity,
                "freshness_days": request.freshness_days,
            },
            ip_address=get_client_ip(http_request),
            user_agent=get_user_agent(http_request),
        )

        return FridgeItemResponse(
            id=db_item.id,
            ingredient_name=db_item.ingredient_name,
            quantity=db_item.quantity,
            days_remaining=db_item.days_remaining,
            added_date=db_item.added_date.isoformat(),
            original_freshness_days=db_item.original_freshness_days,
            freshness_percentage=db_item.freshness_percentage,
        )

    except SQLAlchemyError as e:
        logger.exception(f"Database error adding fridge item: {request.ingredient_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
                "message": "Database error occurred while adding ingredient. Please try again.",
                "details": {
                    "ingredient_name": request.ingredient_name,
                    "error_type": type(e).__name__,
                },
            },
        )
    except Exception as e:
        logger.exception(f"Failed to add fridge item: {request.ingredient_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.FRIDGE_ADD_FAILED.value,
                "message": f"Failed to add ingredient to fridge: {str(e)}",
                "details": {
                    "ingredient_name": request.ingredient_name,
                    "error_type": type(e).__name__,
                },
            },
        )


@router.post("/items/bulk", response_model=List[FridgeItemResponse], status_code=status.HTTP_201_CREATED)
async def add_fridge_items_bulk(
    request: AddItemsBulkRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature(Feature.FRIDGE_BULK_IMPORT)),
):
    """
    Add multiple items to fridge at once.

    Useful after shopping or meal plan generation.

    **Feature flag**: Requires `fridge_bulk_import` feature to be enabled.
    """
    service = FridgeService(db)

    try:
        items_data = [
            {
                "ingredient_name": item.ingredient_name,
                "quantity": item.quantity,
                "freshness_days": item.freshness_days,
            }
            for item in request.items
        ]

        db_items = service.add_items_bulk(current_user, items_data)

        # Audit log: bulk fridge items added
        audit_service = AuditService(db)
        audit_service.log(
            action=AuditAction.BULK_CREATE,
            resource_type="fridge",
            user_id=current_user.id,
            details={
                "item_count": len(db_items),
                "items": [item.ingredient_name for item in db_items],
            },
            ip_address=get_client_ip(http_request),
            user_agent=get_user_agent(http_request),
        )

        return [
            FridgeItemResponse(
                id=item.id,
                ingredient_name=item.ingredient_name,
                quantity=item.quantity,
                days_remaining=item.days_remaining,
                added_date=item.added_date.isoformat(),
                original_freshness_days=item.original_freshness_days,
                freshness_percentage=item.freshness_percentage,
            )
            for item in db_items
        ]

    except SQLAlchemyError as e:
        logger.exception(f"Database error during bulk fridge add")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
                "message": "Database error occurred while adding ingredients. Please try again.",
                "details": {
                    "item_count": len(request.items),
                    "error_type": type(e).__name__,
                },
            },
        )
    except Exception as e:
        logger.exception(f"Failed to bulk add fridge items")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.FRIDGE_BULK_ADD_FAILED.value,
                "message": f"Failed to add ingredients to fridge: {str(e)}",
                "details": {
                    "item_count": len(request.items),
                    "error_type": type(e).__name__,
                },
            },
        )


@router.patch("/items/{item_id}", response_model=FridgeItemResponse)
async def update_fridge_item(
    item_id: UUID,
    request: UpdateItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a fridge item's quantity and/or freshness.

    At least one field must be provided.
    """
    # Validate at least one field is provided
    if request.quantity is None and request.days_remaining is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (quantity or days_remaining) must be provided",
        )

    service = FridgeService(db)

    try:
        db_item = service.update_item(
            user=current_user,
            item_id=item_id,
            quantity=request.quantity,
            days_remaining=request.days_remaining,
        )

        if not db_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fridge item not found",
            )

        return FridgeItemResponse(
            id=db_item.id,
            ingredient_name=db_item.ingredient_name,
            quantity=db_item.quantity,
            days_remaining=db_item.days_remaining,
            added_date=db_item.added_date.isoformat(),
            original_freshness_days=db_item.original_freshness_days,
            freshness_percentage=db_item.freshness_percentage,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception(f"Database error updating fridge item: {item_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.DATABASE_QUERY_ERROR.value,
                "message": "Database error occurred while updating ingredient. Please try again.",
                "details": {
                    "item_id": str(item_id),
                    "error_type": type(e).__name__,
                },
            },
        )
    except Exception as e:
        logger.exception(f"Failed to update fridge item: {item_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.FRIDGE_UPDATE_FAILED.value,
                "message": f"Failed to update ingredient: {str(e)}",
                "details": {
                    "item_id": str(item_id),
                    "error_type": type(e).__name__,
                },
            },
        )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fridge_item(
    item_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove an item from fridge by ID.
    """
    service = FridgeService(db)
    deleted = service.remove_item(current_user, item_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fridge item not found",
        )

    # Audit log: fridge item deleted
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.DELETE,
        resource_type="fridge",
        user_id=current_user.id,
        resource_id=item_id,
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return None


@router.delete("/items/by-name/{ingredient_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_fridge_item_by_name(
    ingredient_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove an item from fridge by ingredient name.
    """
    service = FridgeService(db)
    deleted = service.remove_item_by_name(current_user, ingredient_name)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient '{ingredient_name}' not found in fridge",
        )

    return None


@router.get("/expiring", response_model=List[FridgeItemResponse])
async def get_expiring_items(
    days_threshold: int = settings.fridge_expiring_threshold_default,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get items expiring within specified days.

    Default threshold is 2 days.
    """
    service = FridgeService(db)
    expiring_items = service.get_expiring_items(current_user, days_threshold)

    return [
        FridgeItemResponse(
            id=item.id,
            ingredient_name=item.ingredient_name,
            quantity=item.quantity,
            days_remaining=item.days_remaining,
            added_date=item.added_date.isoformat(),
            original_freshness_days=item.original_freshness_days,
            freshness_percentage=item.freshness_percentage,
        )
        for item in expiring_items
    ]


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_fridge(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Clear all items from fridge.

    Use with caution!
    """
    service = FridgeService(db)
    count = service.clear_fridge(current_user)

    # Audit log: fridge cleared
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.BULK_DELETE,
        resource_type="fridge",
        user_id=current_user.id,
        details={"items_deleted": count},
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return None
