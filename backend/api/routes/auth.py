"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.utils import hash_password, verify_password
from backend.auth.jwt import create_access_token
from backend.api.dependencies import get_current_user
from backend.models.schemas import AuditAction, DietType, DietaryExclusion, UserRole
from backend.config import settings
from backend.utils.sanitization import SanitizedStr, SanitizedStrList
from backend.services.audit_service import AuditService, get_client_ip, get_user_agent

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiter for auth endpoints
# Disabled in debug/test mode or when rate_limit_enabled is False
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled and not settings.debug,
)


# Request/Response schemas
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: Optional[SanitizedStr] = None
    diet_type: DietType = DietType.LOW_HISTAMINE
    dietary_exclusions: SanitizedStrList = Field(default_factory=list, description="List of excluded ingredients or categories")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!",
                    "full_name": "Jane Doe",
                    "diet_type": "low_histamine",
                    "dietary_exclusions": ["dairy", "gluten", "eggs"]
                }
            ]
        }
    }


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ",
                    "token_type": "bearer"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """User information response."""
    id: UUID
    email: str
    full_name: Optional[str]
    diet_type: DietType
    dietary_exclusions: List[str] = Field(default_factory=list)
    role: UserRole = UserRole.USER
    is_active: bool
    created_at: datetime

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
                    "is_active": True,
                    "created_at": "2024-01-15T10:00:00Z"
                }
            ]
        }
    }


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.

    Rate limited to 10 requests per minute per IP to prevent mass account creation.
    Returns a JWT access token upon successful registration.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    new_user = User(
        email=request.email.lower(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        diet_type=request.diet_type,
        dietary_exclusions=request.dietary_exclusions,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Audit log: registration
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.REGISTER,
        resource_type="user",
        user_id=new_user.id,
        resource_id=new_user.id,
        details={"email": new_user.email, "diet_type": new_user.diet_type.value},
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    # Generate access token with role
    access_token = create_access_token(user_id=new_user.id, role=new_user.role.value)

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Login with email and password.

    Rate limited to 5 requests per minute per IP to prevent brute force attacks.
    Returns a JWT access token upon successful authentication.
    """
    audit_service = AuditService(db)
    client_ip = get_client_ip(http_request)
    user_agent = get_user_agent(http_request)

    # Find user by email
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if not user:
        # Audit log: failed login (user not found)
        audit_service.log(
            action=AuditAction.LOGIN_FAILED,
            resource_type="user",
            details={"email": request.email.lower(), "reason": "user_not_found"},
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        # Audit log: failed login (wrong password)
        audit_service.log(
            action=AuditAction.LOGIN_FAILED,
            resource_type="user",
            user_id=user.id,
            resource_id=user.id,
            details={"email": user.email, "reason": "invalid_password"},
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        # Audit log: failed login (inactive account)
        audit_service.log(
            action=AuditAction.LOGIN_FAILED,
            resource_type="user",
            user_id=user.id,
            resource_id=user.id,
            details={"email": user.email, "reason": "account_inactive"},
            ip_address=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Audit log: successful login
    audit_service.log(
        action=AuditAction.LOGIN,
        resource_type="user",
        user_id=user.id,
        resource_id=user.id,
        details={"email": user.email},
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # Generate access token with role
    access_token = create_access_token(user_id=user.id, role=user.role.value)

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user's information.

    Requires: Bearer token in Authorization header.
    """
    return UserResponse.model_validate(current_user)


class UpdateExclusionsRequest(BaseModel):
    """Request to update dietary exclusions."""
    dietary_exclusions: SanitizedStrList = Field(..., description="List of excluded ingredients or categories")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "dietary_exclusions": ["dairy", "gluten", "shellfish", "peanuts"]
                }
            ]
        }
    }

    @classmethod
    def get_valid_exclusions(cls) -> set:
        """Get set of valid exclusion values."""
        return {e.value for e in DietaryExclusion}

    def validate_exclusions(self) -> List[str]:
        """Validate and return invalid exclusions if any."""
        valid_exclusions = self.get_valid_exclusions()
        invalid = [e for e in self.dietary_exclusions if e not in valid_exclusions]
        return invalid


@router.patch("/me/exclusions", response_model=UserResponse)
async def update_dietary_exclusions(
    request: UpdateExclusionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user's dietary exclusions.

    Requires: Bearer token in Authorization header.
    Only accepts valid exclusion values from the DietaryExclusion enum.
    """
    # Validate exclusions against allowed values
    invalid_exclusions = request.validate_exclusions()
    if invalid_exclusions:
        valid_options = sorted(request.get_valid_exclusions())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid exclusions: {invalid_exclusions}. Valid options are: {valid_options}",
        )

    # Update user's dietary exclusions
    current_user.dietary_exclusions = request.dietary_exclusions
    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


class AvailableExclusionsResponse(BaseModel):
    """Response with available dietary exclusion options."""
    exclusions: List[dict] = Field(..., description="List of available exclusion options with name and value")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "exclusions": [
                        {"name": "Peanuts", "value": "peanuts"},
                        {"name": "Tree Nuts", "value": "tree_nuts"},
                        {"name": "Shellfish", "value": "shellfish"},
                        {"name": "Dairy", "value": "dairy"},
                        {"name": "Gluten", "value": "gluten"}
                    ]
                }
            ]
        }
    }


@router.get("/exclusions/available", response_model=AvailableExclusionsResponse)
async def get_available_exclusions():
    """
    Get list of available dietary exclusion options.

    This endpoint is public and doesn't require authentication.
    Returns all supported dietary exclusions for UI selection.
    """
    exclusions = [
        {"name": exclusion.name.replace("_", " ").title(), "value": exclusion.value}
        for exclusion in DietaryExclusion
    ]

    return AvailableExclusionsResponse(exclusions=exclusions)


# ============================================================================
# Account Management Endpoints
# ============================================================================

class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""
    full_name: Optional[SanitizedStr] = Field(None, max_length=255, description="User's full name")
    diet_type: Optional[DietType] = Field(None, description="User's diet type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "full_name": "Jane Doe",
                    "diet_type": "fodmap"
                }
            ]
        }
    }


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's profile.

    Requires: Bearer token in Authorization header.
    Only updates fields that are provided (non-None).
    """
    # Track changes for audit log
    changes = {}
    if request.full_name is not None and request.full_name != current_user.full_name:
        changes["full_name"] = {"old": current_user.full_name, "new": request.full_name}
        current_user.full_name = request.full_name
    if request.diet_type is not None and request.diet_type != current_user.diet_type:
        changes["diet_type"] = {"old": current_user.diet_type.value, "new": request.diet_type.value}
        current_user.diet_type = request.diet_type

    if changes:
        db.commit()
        db.refresh(current_user)

        # Audit log: profile update
        audit_service = AuditService(db)
        audit_service.log(
            action=AuditAction.UPDATE,
            resource_type="user",
            user_id=current_user.id,
            resource_id=current_user.id,
            details={"changes": changes},
            ip_address=get_client_ip(http_request),
            user_agent=get_user_agent(http_request),
        )

    return UserResponse.model_validate(current_user)


class ChangePasswordRequest(BaseModel):
    """Request to change password."""
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "current_password": "OldPassword123!",
                    "new_password": "NewSecurePass456!"
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
                    "message": "Operation completed successfully"
                }
            ]
        }
    }


@router.post("/change-password", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_password_change)
async def change_password(
    request: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.

    Requires: Bearer token in Authorization header.
    Rate limited to 5 requests per minute per IP.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Ensure new password is different
    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()

    # Audit log: password change
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.PASSWORD_CHANGE,
        resource_type="user",
        user_id=current_user.id,
        resource_id=current_user.id,
        details={"email": current_user.email},
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return MessageResponse(message="Password changed successfully")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete current user's account.

    Requires: Bearer token in Authorization header.
    This permanently deletes the user and all associated data (meal plans, fridge items).
    This action cannot be undone.
    """
    # Capture user info before deletion for audit log
    user_id = current_user.id
    user_email = current_user.email

    # Delete user (cascades to meal_plans and fridge_items due to relationship config)
    db.delete(current_user)
    db.commit()

    # Audit log: account deletion (user_id set to None since user is deleted)
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.DELETE,
        resource_type="user",
        user_id=None,  # User no longer exists
        resource_id=user_id,
        details={"email": user_email, "self_deletion": True},
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    return MessageResponse(message="Account deleted successfully")


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset."""
    email: EmailStr

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com"
                }
            ]
        }
    }


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_forgot_password)
async def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Initiate password reset flow.

    Rate limited to 3 requests per minute per IP.
    Always returns success to prevent email enumeration attacks.
    If email exists, a password reset email will be sent.
    """
    # Find user by email (but don't reveal if not found)
    user = db.query(User).filter(User.email == request.email.lower()).first()

    # Audit log: password reset request (log regardless of user existence for security monitoring)
    audit_service = AuditService(db)
    audit_service.log(
        action=AuditAction.PASSWORD_RESET_REQUEST,
        resource_type="user",
        user_id=user.id if user else None,
        resource_id=user.id if user else None,
        details={
            "email": request.email.lower(),
            "user_found": user is not None,
            "user_active": user.is_active if user else None,
        },
        ip_address=get_client_ip(http_request),
        user_agent=get_user_agent(http_request),
    )

    if user and user.is_active:
        # TODO: Generate password reset token and send email
        # For now, we log this action. Full implementation requires:
        # 1. Password reset token table
        # 2. Email service integration
        # 3. Reset password endpoint with token validation
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Password reset requested for user: {user.email}")

    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )
