"""
FastAPI dependencies for authentication and authorization.
"""
from typing import Callable, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.jwt import decode_access_token
from backend.models.schemas import UserRole

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user.

    Usage:
        @app.get("/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    token_payload = decode_access_token(token)

    if token_payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_payload.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure the current user is active.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure the current user is an admin.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Admin user object

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """
    Factory function to create a dependency that checks for specific roles.

    Usage:
        @app.get("/admin-or-moderator")
        def admin_endpoint(
            current_user: User = Depends(require_roles([UserRole.ADMIN]))
        ):
            return {"message": "Admin access granted"}

    Args:
        allowed_roles: List of roles that are allowed to access the endpoint

    Returns:
        Dependency function that validates user role
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker
