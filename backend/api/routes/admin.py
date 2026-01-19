"""
Admin API routes for user management and feature flags.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import UUID

from backend.db.database import get_db
from backend.db.models import User
from backend.api.dependencies import get_current_admin_user
from backend.models.schemas import AuditAction, DietType, UserRole
from backend.services.audit_service import AuditService, get_client_ip, get_user_agent
from backend.config import settings
from backend.features import Feature, FeatureFlagService, get_feature_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Response schemas
class AdminUserResponse(BaseModel):
    """Admin view of user information (includes all fields)."""
    id: UUID
    email: str
    full_name: Optional[str]
    diet_type: DietType
    dietary_exclusions: List[str]
    role: UserRole
    is_active: bool

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "full_name": "Jane Doe",
                    "diet_type": "low_histamine",
                    "dietary_exclusions": ["dairy", "gluten"],
                    "role": "user",
                    "is_active": True
                }
            ]
        }
    }


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[AdminUserResponse]
    total: int
    page: int
    page_size: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "users": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "user@example.com",
                            "full_name": "Jane Doe",
                            "diet_type": "low_histamine",
                            "dietary_exclusions": ["dairy"],
                            "role": "user",
                            "is_active": True
                        }
                    ],
                    "total": 25,
                    "page": 1,
                    "page_size": 20
                }
            ]
        }
    }


class UpdateUserRoleRequest(BaseModel):
    """Request to update a user's role."""
    role: UserRole = Field(..., description="New role for the user")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "role": "admin"
                }
            ]
        }
    }


class UpdateUserStatusRequest(BaseModel):
    """Request to update a user's active status."""
    is_active: bool = Field(..., description="Whether the user account is active")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "is_active": False
                }
            ]
        }
    }


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "User 'user@example.com' deleted successfully"
                }
            ]
        }
    }


# ============================================================================
# Admin Stats Response Models
# ============================================================================


class UserStatsResponse(BaseModel):
    """User-related statistics."""
    total: int
    active: int
    inactive: int
    admins: int
    regular: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": 150,
                    "active": 142,
                    "inactive": 8,
                    "admins": 3,
                    "regular": 147
                }
            ]
        }
    }


class RecipeStatsResponse(BaseModel):
    """Recipe-related statistics."""
    total: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": 85
                }
            ]
        }
    }


class MealPlanStatsResponse(BaseModel):
    """Meal plan-related statistics."""
    total: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": 312
                }
            ]
        }
    }


class AdminStatsResponse(BaseModel):
    """Admin dashboard statistics response."""
    users: UserStatsResponse
    recipes: RecipeStatsResponse
    meal_plans: MealPlanStatsResponse

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "users": {
                        "total": 150,
                        "active": 142,
                        "inactive": 8,
                        "admins": 3,
                        "regular": 147
                    },
                    "recipes": {
                        "total": 85
                    },
                    "meal_plans": {
                        "total": 312
                    }
                }
            ]
        }
    }


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        default=settings.pagination_default_page_size,
        ge=1,
        le=settings.pagination_max_page_size,
        description="Items per page",
    ),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get list of all users.

    **Admin only**: Requires admin role.
    Supports filtering by role and active status.
    """
    query = db.query(User)

    # Apply filters
    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = query.count()

    # Paginate
    skip = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(skip).limit(page_size).all()

    return UserListResponse(
        users=[AdminUserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID.

    **Admin only**: Requires admin role.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return AdminUserResponse.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: UUID,
    request: UpdateUserRoleRequest,
    http_request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update a user's role.

    **Admin only**: Requires admin role.
    Cannot demote yourself to prevent lockout.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin from demoting themselves
    if user.id == admin_user.id and request.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself. Ask another admin to change your role.",
        )

    old_role = user.role.value
    user.role = request.role
    db.commit()
    db.refresh(user)

    # Audit log: role change
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.ROLE_CHANGE,
        resource_type="user",
        user_id=admin_user.id,
        resource_id=user.id,
        details={
            "target_email": user.email,
            "old_role": old_role,
            "new_role": request.role.value,
            "admin_email": admin_user.email,
        },
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return AdminUserResponse.model_validate(user)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: UUID,
    request: UpdateUserStatusRequest,
    http_request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Activate or deactivate a user account.

    **Admin only**: Requires admin role.
    Cannot deactivate yourself to prevent lockout.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin from deactivating themselves
    if user.id == admin_user.id and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself. Ask another admin.",
        )

    old_status = user.is_active
    user.is_active = request.is_active
    db.commit()
    db.refresh(user)

    # Audit log: status change
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.STATUS_CHANGE,
        resource_type="user",
        user_id=admin_user.id,
        resource_id=user.id,
        details={
            "target_email": user.email,
            "old_status": "active" if old_status else "inactive",
            "new_status": "active" if request.is_active else "inactive",
            "admin_email": admin_user.email,
        },
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return AdminUserResponse.model_validate(user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    http_request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete a user account.

    **Admin only**: Requires admin role.
    Cannot delete yourself.
    This permanently deletes the user and all associated data.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin from deleting themselves
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself. Use the account deletion endpoint or ask another admin.",
        )

    email = user.email
    deleted_user_id = user.id
    db.delete(user)
    db.commit()

    # Audit log: admin deleted user
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.DELETE,
        resource_type="user",
        user_id=admin_user.id,
        resource_id=deleted_user_id,
        details={
            "deleted_email": email,
            "admin_email": admin_user.email,
            "admin_deletion": True,
        },
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return MessageResponse(message=f"User '{email}' deleted successfully")


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get admin dashboard statistics.

    **Admin only**: Requires admin role.
    Returns counts of users, recipes, and meal plans.
    """
    from backend.db.models import MealPlan, Recipe

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
    total_recipes = db.query(Recipe).count()
    total_meal_plans = db.query(MealPlan).count()

    return AdminStatsResponse(
        users=UserStatsResponse(
            total=total_users,
            active=active_users,
            inactive=total_users - active_users,
            admins=admin_users,
            regular=total_users - admin_users,
        ),
        recipes=RecipeStatsResponse(
            total=total_recipes,
        ),
        meal_plans=MealPlanStatsResponse(
            total=total_meal_plans,
        ),
    )


# ==============================================================================
# Audit Log Endpoints
# ==============================================================================


class AuditLogResponse(BaseModel):
    """Single audit log entry response."""
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    details: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "660e8400-e29b-41d4-a716-446655440001",
                    "action": "login",
                    "resource_type": "user",
                    "resource_id": "660e8400-e29b-41d4-a716-446655440001",
                    "details": {"email": "user@example.com"},
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "created_at": "2025-12-21T10:30:00"
                }
            ]
        }
    }


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "logs": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "660e8400-e29b-41d4-a716-446655440001",
                            "action": "login",
                            "resource_type": "user",
                            "resource_id": "660e8400-e29b-41d4-a716-446655440001",
                            "details": {"email": "user@example.com"},
                            "ip_address": "192.168.1.1",
                            "user_agent": "Mozilla/5.0",
                            "created_at": "2025-12-21T10:30:00"
                        }
                    ],
                    "total": 156,
                    "page": 1,
                    "page_size": 50
                }
            ]
        }
    }


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        default=settings.pagination_audit_log_page_size,
        ge=1,
        le=settings.pagination_max_page_size,
        description="Items per page",
    ),
    user_id: Optional[UUID] = Query(None, description="Filter by user who performed the action"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (user, plan, fridge, recipe)"),
    resource_id: Optional[UUID] = Query(None, description="Filter by specific resource ID"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get paginated audit logs with optional filters.

    **Admin only**: Requires admin role.
    Supports filtering by user, action type, resource type, and resource ID.
    """
    audit_service = AuditService(db)

    logs, total = audit_service.get_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        page=page,
        page_size=page_size,
    )

    return AuditLogListResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action.value,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs/user/{target_user_id}", response_model=List[AuditLogResponse])
async def get_user_audit_logs(
    target_user_id: UUID,
    limit: int = Query(
        default=settings.pagination_user_audit_limit,
        ge=1,
        le=settings.pagination_user_audit_max_limit,
        description="Maximum number of logs to return",
    ),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get recent audit logs for a specific user.

    **Admin only**: Requires admin role.
    Returns the most recent audit entries for the specified user.
    """
    audit_service = AuditService(db)
    logs = audit_service.get_user_activity(target_user_id, limit=limit)

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action.value,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


@router.get("/audit-logs/resource/{resource_type}/{resource_id}", response_model=List[AuditLogResponse])
async def get_resource_audit_logs(
    resource_type: str,
    resource_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get audit history for a specific resource.

    **Admin only**: Requires admin role.
    Returns all audit entries related to the specified resource.
    """
    audit_service = AuditService(db)
    logs = audit_service.get_resource_history(resource_type, resource_id)

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action.value,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]


# ==============================================================================
# Feature Flag Endpoints
# ==============================================================================


class FeatureFlagResponse(BaseModel):
    """Single feature flag response."""

    name: str
    enabled: bool
    description: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "plan_duplication",
                    "enabled": True,
                    "description": "Allow users to duplicate existing meal plans",
                }
            ]
        }
    }


class FeatureFlagsResponse(BaseModel):
    """All feature flags response."""

    flags: Dict[str, bool]
    enabled_count: int
    disabled_count: int
    total_count: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "flags": {
                        "email_plan_notifications": True,
                        "export_pdf": True,
                        "plan_duplication": True,
                        "offline_mode": False,
                    },
                    "enabled_count": 14,
                    "disabled_count": 2,
                    "total_count": 16,
                }
            ]
        }
    }


# Feature descriptions for documentation
FEATURE_DESCRIPTIONS: Dict[Feature, str] = {
    Feature.EMAIL_PLAN_NOTIFICATIONS: "Send meal plan notifications via email",
    Feature.EMAIL_EXPIRING_ALERTS: "Send alerts for expiring fridge items",
    Feature.EMAIL_ADAPTATION_SUMMARIES: "Send adaptation summary emails",
    Feature.EXPORT_PDF: "Export meal plans as PDF documents",
    Feature.EXPORT_SHOPPING_LIST: "Export shopping lists as PDF",
    Feature.PLAN_DUPLICATION: "Allow users to duplicate existing meal plans",
    Feature.PLAN_ADAPTATION: "Enable adaptive meal planning based on changes",
    Feature.MEAL_SWAP: "Allow swapping meals within a plan",
    Feature.FRIDGE_BULK_IMPORT: "Bulk import fridge items",
    Feature.FRIDGE_EXPIRING_NOTIFICATIONS: "Show notifications for expiring items",
    Feature.RECIPE_SEARCH: "Search recipes by ingredients",
    Feature.RECIPE_BROWSER: "Browse recipe catalog",
    Feature.ADMIN_USER_MANAGEMENT: "Admin user management features",
    Feature.ADMIN_AUDIT_LOGS: "Admin access to audit logs",
    Feature.PREP_TIMELINE_OPTIMIZATION: "Optimized prep timeline generation",
    Feature.OFFLINE_MODE: "Offline mode support for the frontend",
}


@router.get("/features", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    admin_user: User = Depends(get_current_admin_user),
    feature_service: FeatureFlagService = Depends(get_feature_service),
):
    """
    Get current state of all feature flags.

    **Admin only**: Requires admin role.
    Returns all feature flags with their enabled/disabled status.
    Feature flags are configured via environment variables (FEATURE_<FLAG_NAME>=true/false).
    """
    flags = feature_service.get_all_flags()
    enabled = feature_service.get_enabled_features()
    disabled = feature_service.get_disabled_features()

    return FeatureFlagsResponse(
        flags=flags,
        enabled_count=len(enabled),
        disabled_count=len(disabled),
        total_count=len(flags),
    )


@router.get("/features/{feature_name}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    feature_name: str,
    admin_user: User = Depends(get_current_admin_user),
    feature_service: FeatureFlagService = Depends(get_feature_service),
):
    """
    Get state of a specific feature flag.

    **Admin only**: Requires admin role.
    Returns the feature flag status and description.
    """
    # Validate feature name
    try:
        feature = Feature(feature_name)
    except ValueError:
        valid_features = [f.value for f in Feature]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": f"Feature '{feature_name}' not found",
                "valid_features": valid_features,
            },
        )

    is_enabled = feature_service.is_enabled(feature)
    description = FEATURE_DESCRIPTIONS.get(feature, "No description available")

    return FeatureFlagResponse(
        name=feature.value,
        enabled=is_enabled,
        description=description,
    )
