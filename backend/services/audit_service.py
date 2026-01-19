"""
Audit logging service for tracking user actions and changes.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.db.models import AuditLog
from backend.models.schemas import AuditAction


class AuditService:
    """
    Service for creating and querying audit logs.

    Provides methods for logging user actions and querying the audit trail
    for compliance, debugging, and security monitoring purposes.
    """

    def __init__(self, db: Session):
        """
        Initialize the audit service.

        Args:
            db: SQLAlchemy database session for persistence operations.
        """
        self.db = db

    def log(
        self,
        action: AuditAction,
        resource_type: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The action being performed (from AuditAction enum)
            resource_type: Type of resource being acted upon (user, plan, fridge, recipe)
            user_id: ID of the user performing the action (None for unauthenticated actions)
            resource_id: ID of the resource being acted upon
            details: Additional context (old values, new values, etc.)
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            The created AuditLog entry
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log

    def log_without_commit(
        self,
        action: AuditAction,
        resource_type: str,
        user_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry without committing.

        Use this when you want to include audit logging in an existing transaction
        that will be committed elsewhere. The log entry is added to the session
        but not persisted until the caller commits.

        Args:
            action: The action being performed (from AuditAction enum).
            resource_type: Type of resource being acted upon (user, plan, fridge, recipe).
            user_id: ID of the user performing the action (None for unauthenticated).
            resource_id: ID of the resource being acted upon.
            details: Additional context (old values, new values, etc.).
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            The created (uncommitted) AuditLog entry.
        """
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        return audit_log

    def get_logs(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """
        Query audit logs with filters.

        Args:
            user_id: Filter by user who performed the action
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by specific resource
            start_date: Filter logs created after this date
            end_date: Filter logs created before this date
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            Tuple of (list of audit logs, total count)
        """
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        total = query.count()
        logs = (
            query.order_by(desc(AuditLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return logs, total

    def get_user_activity(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get recent activity for a specific user.

        Args:
            user_id: UUID of the user to get activity for.
            limit: Maximum number of log entries to return.

        Returns:
            List of audit log entries, ordered by most recent first.
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .all()
        )

    def get_resource_history(
        self,
        resource_type: str,
        resource_id: UUID,
    ) -> List[AuditLog]:
        """
        Get all audit logs for a specific resource.

        Args:
            resource_type: Type of resource (user, plan, fridge, recipe).
            resource_id: UUID of the resource.

        Returns:
            List of audit log entries for the resource, ordered by most recent first.
        """
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id,
            )
            .order_by(desc(AuditLog.created_at))
            .all()
        )


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP from request, considering proxies.

    Checks X-Forwarded-For and X-Real-IP headers before falling back
    to the direct client address.

    Args:
        request: FastAPI/Starlette request object.

    Returns:
        Client IP address string, or None if unavailable.
    """
    # Check for forwarded header (common with reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()

    # Check for real IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return None


def get_user_agent(request) -> Optional[str]:
    """
    Extract user agent from request headers.

    Args:
        request: FastAPI/Starlette request object.

    Returns:
        User agent string, or None if not present.
    """
    return request.headers.get("User-Agent")
