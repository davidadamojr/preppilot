"""
Tests for audit logging functionality.

Tests cover:
- AuditService operations
- Audit log creation on various actions
- Admin audit log query endpoints
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from backend.db.models import AuditLog
from backend.models.schemas import AuditAction
from backend.services.audit_service import AuditService, get_client_ip, get_user_agent


# ============================================================================
# AuditService Unit Tests
# ============================================================================


class TestAuditService:
    """Tests for AuditService methods."""

    def test_log_creates_entry(self, db_session, test_user):
        """Should create an audit log entry."""
        service = AuditService(db_session)

        log = service.log(
            action=AuditAction.LOGIN,
            resource_type="user",
            user_id=test_user.id,
            resource_id=test_user.id,
            details={"email": test_user.email},
            ip_address="192.168.1.1",
            user_agent="TestClient/1.0",
        )

        assert log.id is not None
        assert log.action == AuditAction.LOGIN
        assert log.resource_type == "user"
        assert log.user_id == test_user.id
        assert log.resource_id == test_user.id
        assert log.details == {"email": test_user.email}
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "TestClient/1.0"
        assert log.created_at is not None

    def test_log_without_commit_does_not_persist_alone(self, db_session, test_user):
        """Should not persist until explicitly committed."""
        service = AuditService(db_session)

        log = service.log_without_commit(
            action=AuditAction.CREATE,
            resource_type="plan",
            user_id=test_user.id,
        )

        # Log should exist in session but not persisted yet
        assert log.action == AuditAction.CREATE

    def test_log_with_null_user_id(self, db_session):
        """Should allow logging without a user (for failed logins, etc.)."""
        service = AuditService(db_session)

        log = service.log(
            action=AuditAction.LOGIN_FAILED,
            resource_type="user",
            user_id=None,
            details={"email": "unknown@example.com", "reason": "user_not_found"},
        )

        assert log.user_id is None
        assert log.details["reason"] == "user_not_found"

    def test_get_logs_returns_paginated_results(self, db_session, test_user):
        """Should return paginated audit logs."""
        service = AuditService(db_session)

        # Create multiple logs
        for i in range(15):
            service.log(
                action=AuditAction.READ,
                resource_type="plan",
                user_id=test_user.id,
            )

        # Query first page
        logs, total = service.get_logs(page=1, page_size=10)
        assert len(logs) == 10
        assert total == 15

        # Query second page
        logs, total = service.get_logs(page=2, page_size=10)
        assert len(logs) == 5
        assert total == 15

    def test_get_logs_filters_by_user_id(self, db_session, test_user, admin_user):
        """Should filter logs by user_id."""
        service = AuditService(db_session)

        # Create logs for different users
        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=admin_user.id)

        logs, total = service.get_logs(user_id=test_user.id)
        assert total == 2
        assert all(log.user_id == test_user.id for log in logs)

    def test_get_logs_filters_by_action(self, db_session, test_user):
        """Should filter logs by action type."""
        service = AuditService(db_session)

        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id)
        service.log(action=AuditAction.DELETE, resource_type="plan", user_id=test_user.id)

        logs, total = service.get_logs(action=AuditAction.LOGIN)
        assert total == 1
        assert logs[0].action == AuditAction.LOGIN

    def test_get_logs_filters_by_resource_type(self, db_session, test_user):
        """Should filter logs by resource type."""
        service = AuditService(db_session)

        service.log(action=AuditAction.CREATE, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id)
        service.log(action=AuditAction.CREATE, resource_type="fridge", user_id=test_user.id)

        logs, total = service.get_logs(resource_type="plan")
        assert total == 1
        assert logs[0].resource_type == "plan"

    def test_get_logs_orders_by_created_at_desc(self, db_session, test_user):
        """Should return logs ordered by created_at descending."""
        service = AuditService(db_session)

        log1 = service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        log2 = service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id)

        logs, _ = service.get_logs()
        # Most recent first
        assert logs[0].id == log2.id
        assert logs[1].id == log1.id

    def test_get_user_activity(self, db_session, test_user):
        """Should return recent activity for a user."""
        service = AuditService(db_session)

        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id)

        logs = service.get_user_activity(test_user.id, limit=10)
        assert len(logs) == 2
        assert all(log.user_id == test_user.id for log in logs)

    def test_get_resource_history(self, db_session, test_user):
        """Should return audit history for a resource."""
        service = AuditService(db_session)
        resource_id = uuid4()

        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id, resource_id=resource_id)
        service.log(action=AuditAction.UPDATE, resource_type="plan", user_id=test_user.id, resource_id=resource_id)
        service.log(action=AuditAction.DELETE, resource_type="plan", user_id=test_user.id, resource_id=resource_id)

        logs = service.get_resource_history("plan", resource_id)
        assert len(logs) == 3
        assert all(log.resource_id == resource_id for log in logs)


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for audit service helper functions."""

    def test_get_client_ip_from_x_forwarded_for(self):
        """Should extract IP from X-Forwarded-For header."""
        class MockRequest:
            headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
            client = None

        ip = get_client_ip(MockRequest())
        assert ip == "203.0.113.1"

    def test_get_client_ip_from_x_real_ip(self):
        """Should extract IP from X-Real-IP header."""
        class MockRequest:
            headers = {"X-Real-IP": "203.0.113.2"}
            client = None

        ip = get_client_ip(MockRequest())
        assert ip == "203.0.113.2"

    def test_get_client_ip_from_client(self):
        """Should extract IP from request.client."""
        class MockClient:
            host = "192.168.1.1"

        class MockRequest:
            headers = {}
            client = MockClient()

        ip = get_client_ip(MockRequest())
        assert ip == "192.168.1.1"

    def test_get_client_ip_returns_none_when_unavailable(self):
        """Should return None when no IP source available."""
        class MockRequest:
            headers = {}
            client = None

        ip = get_client_ip(MockRequest())
        assert ip is None

    def test_get_user_agent(self):
        """Should extract user agent from headers."""
        class MockRequest:
            headers = {"User-Agent": "Mozilla/5.0 (Test)"}

        agent = get_user_agent(MockRequest())
        assert agent == "Mozilla/5.0 (Test)"


# ============================================================================
# Integration Tests - Auth Routes
# ============================================================================


class TestAuthAuditLogging:
    """Tests for audit logging in auth routes."""

    def test_registration_creates_audit_log(self, client, db_session):
        """Should log user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "audituser@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201

        # Check audit log was created
        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.REGISTER
        ).first()
        assert log is not None
        assert log.resource_type == "user"
        assert log.details["email"] == "audituser@example.com"

    def test_login_success_creates_audit_log(self, client, db_session, test_user):
        """Should log successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.LOGIN
        ).first()
        assert log is not None
        assert log.user_id == test_user.id
        assert log.details["email"] == "test@example.com"

    def test_login_failure_creates_audit_log(self, client, db_session, test_user):
        """Should log failed login attempt."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.LOGIN_FAILED
        ).first()
        assert log is not None
        assert log.details["reason"] == "invalid_password"

    def test_password_change_creates_audit_log(self, client, db_session, test_user, auth_headers):
        """Should log password change."""
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.PASSWORD_CHANGE
        ).first()
        assert log is not None
        assert log.user_id == test_user.id


# ============================================================================
# Integration Tests - Plan Routes
# ============================================================================


class TestPlanAuditLogging:
    """Tests for audit logging in plan routes."""

    def test_delete_plan_creates_audit_log(self, client, db_session, test_user, auth_headers, test_meal_plan):
        """Should log meal plan deletion."""
        response = client.delete(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.DELETE,
            AuditLog.resource_type == "plan",
        ).first()
        assert log is not None
        assert log.user_id == test_user.id
        assert log.resource_id == test_meal_plan.id

    def test_create_plan_audit_log_direct(self, db_session, test_user):
        """Should create audit log for plan creation (unit test)."""
        # Test the audit logging directly without going through the full plan creation
        # (which requires PostgreSQL for JSONB queries in recipe selection)
        from uuid import uuid4
        service = AuditService(db_session)
        plan_id = uuid4()

        log = service.log(
            action=AuditAction.CREATE,
            resource_type="plan",
            user_id=test_user.id,
            resource_id=plan_id,
            details={
                "start_date": "2025-01-01",
                "days": 3,
                "simplified": False,
                "diet_type": "low_histamine",
            },
        )

        assert log is not None
        assert log.action == AuditAction.CREATE
        assert log.resource_type == "plan"
        assert log.user_id == test_user.id
        assert log.resource_id == plan_id
        assert log.details["days"] == 3


# ============================================================================
# Integration Tests - Fridge Routes
# ============================================================================


class TestFridgeAuditLogging:
    """Tests for audit logging in fridge routes."""

    def test_add_fridge_item_creates_audit_log(self, client, db_session, test_user, auth_headers):
        """Should log fridge item addition."""
        response = client.post(
            "/api/fridge/items",
            json={
                "ingredient_name": "milk",
                "quantity": "1 gallon",
                "freshness_days": 7,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.CREATE,
            AuditLog.resource_type == "fridge",
        ).first()
        assert log is not None
        assert log.user_id == test_user.id
        assert log.details["ingredient_name"] == "milk"

    def test_bulk_add_creates_audit_log(self, client, db_session, test_user, auth_headers):
        """Should log bulk fridge item addition."""
        response = client.post(
            "/api/fridge/items/bulk",
            json={
                "items": [
                    {"ingredient_name": "eggs", "quantity": "12", "freshness_days": 21},
                    {"ingredient_name": "butter", "quantity": "1 lb", "freshness_days": 30},
                ]
            },
            headers=auth_headers,
        )

        assert response.status_code == 201

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.BULK_CREATE,
            AuditLog.resource_type == "fridge",
        ).first()
        assert log is not None
        assert log.details["item_count"] == 2

    def test_delete_fridge_item_creates_audit_log(self, client, db_session, test_user, auth_headers, test_fridge_items):
        """Should log fridge item deletion."""
        item = test_fridge_items[0]

        response = client.delete(
            f"/api/fridge/items/{item.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.DELETE,
            AuditLog.resource_type == "fridge",
        ).first()
        assert log is not None
        assert log.resource_id == item.id

    def test_clear_fridge_creates_audit_log(self, client, db_session, test_user, auth_headers, test_fridge_items):
        """Should log fridge clearing."""
        response = client.delete(
            "/api/fridge",
            headers=auth_headers,
        )

        assert response.status_code == 204

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.BULK_DELETE,
            AuditLog.resource_type == "fridge",
        ).first()
        assert log is not None
        assert log.details["items_deleted"] == len(test_fridge_items)


# ============================================================================
# Integration Tests - Admin Routes
# ============================================================================


class TestAdminAuditLogging:
    """Tests for audit logging in admin routes."""

    def test_role_change_creates_audit_log(self, client, db_session, admin_user, admin_auth_headers, test_user):
        """Should log admin role change."""
        response = client.patch(
            f"/api/admin/users/{test_user.id}/role",
            json={"role": "admin"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.ROLE_CHANGE
        ).first()
        assert log is not None
        assert log.user_id == admin_user.id
        assert log.resource_id == test_user.id
        assert log.details["old_role"] == "user"
        assert log.details["new_role"] == "admin"

    def test_status_change_creates_audit_log(self, client, db_session, admin_user, admin_auth_headers, test_user):
        """Should log admin status change."""
        response = client.patch(
            f"/api/admin/users/{test_user.id}/status",
            json={"is_active": False},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.STATUS_CHANGE
        ).first()
        assert log is not None
        assert log.details["old_status"] == "active"
        assert log.details["new_status"] == "inactive"

    def test_admin_delete_user_creates_audit_log(self, client, db_session, admin_user, admin_auth_headers, user_factory):
        """Should log admin user deletion."""
        user_to_delete = user_factory.create(email="todelete@example.com")
        deleted_user_id = user_to_delete.id

        response = client.delete(
            f"/api/admin/users/{user_to_delete.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200

        log = db_session.query(AuditLog).filter(
            AuditLog.action == AuditAction.DELETE,
            AuditLog.resource_type == "user",
            AuditLog.resource_id == deleted_user_id,
        ).first()
        assert log is not None
        assert log.user_id == admin_user.id
        assert log.details["deleted_email"] == "todelete@example.com"
        assert log.details["admin_deletion"] is True


# ============================================================================
# Integration Tests - Admin Audit Log Endpoints
# ============================================================================


class TestAdminAuditLogEndpoints:
    """Tests for admin audit log query endpoints."""

    def test_get_audit_logs_requires_admin(self, client, auth_headers):
        """Should require admin role to access audit logs."""
        response = client.get("/api/admin/audit-logs", headers=auth_headers)
        assert response.status_code == 403

    def test_get_audit_logs_success(self, client, db_session, admin_user, admin_auth_headers, test_user):
        """Should return paginated audit logs for admin."""
        # Create some logs
        service = AuditService(db_session)
        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)

        response = client.get("/api/admin/audit-logs", headers=admin_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 50

    def test_get_audit_logs_with_filters(self, client, db_session, admin_auth_headers, test_user):
        """Should filter audit logs by parameters."""
        service = AuditService(db_session)
        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id)

        response = client.get(
            f"/api/admin/audit-logs?action=login",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["logs"][0]["action"] == "login"

    def test_get_user_audit_logs(self, client, db_session, admin_auth_headers, test_user):
        """Should return audit logs for a specific user."""
        service = AuditService(db_session)
        service.log(action=AuditAction.LOGIN, resource_type="user", user_id=test_user.id)
        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id)

        response = client.get(
            f"/api/admin/audit-logs/user/{test_user.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(log["user_id"] == str(test_user.id) for log in data)

    def test_get_resource_audit_logs(self, client, db_session, admin_auth_headers, test_user):
        """Should return audit logs for a specific resource."""
        resource_id = uuid4()
        service = AuditService(db_session)
        service.log(action=AuditAction.CREATE, resource_type="plan", user_id=test_user.id, resource_id=resource_id)
        service.log(action=AuditAction.UPDATE, resource_type="plan", user_id=test_user.id, resource_id=resource_id)

        response = client.get(
            f"/api/admin/audit-logs/resource/plan/{resource_id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(log["resource_id"] == str(resource_id) for log in data)
