"""
Email notification routes.
"""
import logging
from uuid import UUID
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.db.database import get_db
from backend.db.models import User
from backend.services.email_service import EmailService
from backend.services.meal_service import MealPlanningService
from backend.services.fridge_service import FridgeService
from backend.services.adaptive_service import AdaptiveService
from backend.config import settings
from backend.errors import ErrorCode

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/email", tags=["email"])


class SendPlanEmailRequest(BaseModel):
    """Request to send meal plan email."""
    include_pdf: bool = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "include_pdf": True
                }
            ]
        }
    }


class EmailStatusResponse(BaseModel):
    """Response for email send operations."""
    success: bool
    message: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Meal plan sent to user@example.com"
                }
            ]
        }
    }


class EmailConfigStatusResponse(BaseModel):
    """Response for email service configuration status."""
    enabled: bool
    user_email: str
    smtp_configured: bool

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "enabled": True,
                    "user_email": "user@example.com",
                    "smtp_configured": True
                }
            ]
        }
    }


@router.post("/{plan_id}/send-plan", response_model=EmailStatusResponse)
async def send_meal_plan_email(
    plan_id: UUID,
    request: SendPlanEmailRequest = SendPlanEmailRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send meal plan to user's email with PDF attachment.
    """
    # Get meal plan
    meal_service = MealPlanningService(db)
    plan = meal_service.get_plan(plan_id, current_user)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    # Send email
    email_service = EmailService(db)
    success = email_service.send_weekly_plan_summary(current_user, plan)

    if not success:
        logger.warning(f"Failed to send meal plan email to {current_user.email}")
        return EmailStatusResponse(
            success=False,
            message=f"Failed to send email to {current_user.email}. Please check your email settings or try again later."
        )

    return EmailStatusResponse(
        success=True,
        message=f"Meal plan sent to {current_user.email}"
    )


@router.post("/{plan_id}/send-adaptation", response_model=EmailStatusResponse)
async def send_adaptation_email(
    plan_id: UUID,
    current_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send adaptation summary email after plan changes.
    """
    if current_date is None:
        current_date = date.today()

    # Get meal plan
    meal_service = MealPlanningService(db)
    plan = meal_service.get_plan(plan_id, current_user)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    # Run adaptation to get output
    adaptive_service = AdaptiveService(db)
    try:
        adaptation_output = adaptive_service.adapt_plan(
            user=current_user,
            plan_id=plan_id,
            current_date=current_date,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": ErrorCode.PLAN_NOT_FOUND.value,
                "message": str(e),
                "details": {"plan_id": str(plan_id)},
            }
        )
    except Exception as e:
        logger.exception(f"Failed to adapt plan {plan_id} for email")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.PLAN_ADAPTATION_FAILED.value,
                "message": f"Failed to adapt plan before sending email: {str(e)}",
                "details": {
                    "plan_id": str(plan_id),
                    "error_type": type(e).__name__,
                },
            }
        )

    # Refresh plan after adaptation
    plan = meal_service.get_plan(plan_id, current_user)

    # Send email
    email_service = EmailService(db)
    success = email_service.send_adaptation_summary(
        user=current_user,
        plan=plan,
        adaptation_output=adaptation_output,
    )

    if not success:
        logger.warning(f"Failed to send adaptation email to {current_user.email}")
        return EmailStatusResponse(
            success=False,
            message=f"Failed to send adaptation email to {current_user.email}. The email service may be temporarily unavailable."
        )

    return EmailStatusResponse(
        success=True,
        message=f"Adaptation summary sent to {current_user.email}"
    )


@router.post("/send-expiring-alert", response_model=EmailStatusResponse)
async def send_expiring_items_alert(
    days_threshold: int = settings.fridge_expiring_threshold_default,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send email alert about ingredients expiring soon.
    """
    # Get expiring items
    fridge_service = FridgeService(db)
    expiring_items = fridge_service.get_expiring_items(current_user, days_threshold)

    if not expiring_items:
        return EmailStatusResponse(
            success=True,
            message="No expiring items to alert about."
        )

    # Convert to schema items
    from backend.models.schemas import FridgeItem
    schema_items = [
        FridgeItem(
            ingredient_name=item.ingredient_name,
            quantity=item.quantity,
            days_remaining=item.days_remaining,
            added_date=item.added_date,
            original_freshness_days=item.original_freshness_days,
        )
        for item in expiring_items
    ]

    # Send email
    email_service = EmailService(db)
    success = email_service.send_expiring_items_alert(current_user, schema_items)

    if not success:
        logger.warning(f"Failed to send expiring items alert to {current_user.email}")
        return EmailStatusResponse(
            success=False,
            message=f"Failed to send expiring items alert to {current_user.email}. The email service may be temporarily unavailable."
        )

    return EmailStatusResponse(
        success=True,
        message=f"Alert about {len(expiring_items)} expiring items sent to {current_user.email}"
    )


@router.get("/status", response_model=EmailConfigStatusResponse)
async def get_email_status(
    current_user: User = Depends(get_current_user),
):
    """
    Get email service configuration status.
    """
    return EmailConfigStatusResponse(
        enabled=settings.email_enabled,
        user_email=current_user.email,
        smtp_configured=bool(settings.smtp_username and settings.smtp_password),
    )
