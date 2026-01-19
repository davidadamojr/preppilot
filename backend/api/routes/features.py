"""
Feature flags API routes.

Public endpoints for authenticated users to check feature availability.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict

from backend.api.dependencies import get_current_user
from backend.db.models import User
from backend.features import Feature, FeatureFlagService, get_feature_service

router = APIRouter(prefix="/api/features", tags=["features"])


class PublicFeatureFlagsResponse(BaseModel):
    """
    Feature flags response for authenticated users.

    Returns only the flag states without admin-only metadata.
    """

    flags: Dict[str, bool]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "flags": {
                        "email_plan_notifications": True,
                        "email_expiring_alerts": True,
                        "email_adaptation_summaries": True,
                        "export_pdf": True,
                        "export_shopping_list": True,
                        "plan_duplication": True,
                        "plan_adaptation": True,
                        "meal_swap": True,
                        "fridge_bulk_import": True,
                        "fridge_expiring_notifications": True,
                        "recipe_search": True,
                        "recipe_browser": True,
                        "admin_user_management": True,
                        "admin_audit_logs": True,
                        "prep_timeline_optimization": True,
                        "offline_mode": False,
                    }
                }
            ]
        }
    }


@router.get("", response_model=PublicFeatureFlagsResponse)
async def get_feature_flags(
    current_user: User = Depends(get_current_user),
    feature_service: FeatureFlagService = Depends(get_feature_service),
):
    """
    Get current state of all feature flags.

    **Authenticated users only**: Returns all feature flags with their enabled/disabled status.
    Use this to conditionally show/hide UI features based on server configuration.
    """
    flags = feature_service.get_all_flags()
    return PublicFeatureFlagsResponse(flags=flags)
