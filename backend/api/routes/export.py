"""
Export routes for PDF generation and downloads.
"""
import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from backend.api.dependencies import get_current_user
from backend.db.database import get_db
from backend.db.models import User
from backend.services.pdf_service import PDFService
from backend.services.meal_service import MealPlanningService
from backend.services.adaptive_service import AdaptiveService
from backend.errors import ErrorCode
from backend.features import Feature
from backend.features.service import require_feature

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{plan_id}/pdf")
async def download_meal_plan_pdf(
    plan_id: UUID,
    include_shopping_list: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature(Feature.EXPORT_PDF)),
):
    """
    Download meal plan as PDF.

    Returns a PDF file containing:
    - Daily meal schedule
    - Shopping list (optional)
    - Prep timeline with batched tasks

    **Feature flag**: Requires `export_pdf` feature to be enabled.
    """
    # Get meal plan
    meal_service = MealPlanningService(db)
    plan = meal_service.get_plan(plan_id, current_user)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    # Generate PDF
    pdf_service = PDFService(db)
    pdf_bytes = pdf_service.generate_meal_plan_pdf(
        plan=plan,
        include_shopping_list=include_shopping_list,
    )

    # Create filename
    filename = f"preppilot_meal_plan_{plan.start_date.isoformat()}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{plan_id}/catch-up-pdf")
async def download_catch_up_pdf(
    plan_id: UUID,
    current_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download catch-up PDF after adaptations.

    Returns a PDF containing:
    - Adaptation summary (what changed and why)
    - Priority ingredients to use
    - Updated meal schedule
    - Estimated recovery time
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

    # Get adaptive suggestions
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
        logger.exception(f"Failed to generate adaptation for PDF export: plan {plan_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCode.EXPORT_ADAPTATION_FAILED.value,
                "message": f"Failed to generate adaptation for PDF: {str(e)}",
                "details": {
                    "plan_id": str(plan_id),
                    "current_date": str(current_date),
                    "error_type": type(e).__name__,
                },
            }
        )

    # Get fridge state for context
    from backend.services.fridge_service import FridgeService
    fridge_service = FridgeService(db)
    fridge_state = fridge_service.get_fridge_state(current_user)

    # Refresh plan after adaptation
    plan = meal_service.get_plan(plan_id, current_user)

    # Generate PDF
    pdf_service = PDFService(db)
    pdf_bytes = pdf_service.generate_catch_up_pdf(
        plan=plan,
        adaptation_output=adaptation_output,
        fridge_state=fridge_state,
    )

    filename = f"preppilot_catch_up_{current_date.isoformat()}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{plan_id}/shopping-list-pdf")
async def download_shopping_list_pdf(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_feature(Feature.EXPORT_SHOPPING_LIST)),
):
    """
    Download just the shopping list as a compact PDF.

    **Feature flag**: Requires `export_shopping_list` feature to be enabled.
    """
    # Get meal plan
    meal_service = MealPlanningService(db)
    plan = meal_service.get_plan(plan_id, current_user)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )

    # Generate PDF with only shopping list
    pdf_service = PDFService(db)

    # Generate minimal PDF with shopping list
    from backend.services.meal_service import db_meal_plan_to_schema
    schema_plan = db_meal_plan_to_schema(plan, db)

    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    # Title
    story.append(Paragraph("PrepPilot Shopping List", pdf_service.styles['PrepPilotTitle']))
    date_range = f"{schema_plan.start_date.strftime('%B %d')} - {schema_plan.end_date.strftime('%B %d, %Y')}"
    story.append(Paragraph(date_range, pdf_service.styles['PrepBody']))
    story.append(Spacer(1, 12))

    # Shopping list
    shopping_list = pdf_service._generate_shopping_list(schema_plan)
    ingredients_by_category = pdf_service._group_by_category(shopping_list)

    for category, items in sorted(ingredients_by_category.items()):
        story.append(Paragraph(category.capitalize(), pdf_service.styles['DayHeading']))

        list_items = []
        for item_name, quantity in sorted(items.items()):
            list_items.append(ListItem(
                Paragraph(f"{item_name}: {quantity}", pdf_service.styles['PrepBody']),
                bulletColor=pdf_service.SECONDARY_COLOR,
            ))

        story.append(ListFlowable(list_items, bulletType='bullet', start='•'))
        story.append(Spacer(1, 6))

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    filename = f"preppilot_shopping_list_{plan.start_date.isoformat()}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
