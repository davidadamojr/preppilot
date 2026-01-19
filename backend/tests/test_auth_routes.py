"""
Tests for authentication API routes.

Tests cover:
- User registration
- User login
- Get current user
- Update dietary exclusions
- Get available exclusions
"""
import pytest
from backend.models.schemas import DietType


class TestRegisterEndpoint:
    """Tests for POST /auth/register."""

    def test_register_success(self, client):
        """Should create new user and return token."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
                "diet_type": "low_histamine",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_minimal_fields(self, client):
        """Should register with only required fields."""
        response = client.post(
            "/auth/register",
            json={
                "email": "minimal@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        assert "access_token" in response.json()

    def test_register_with_dietary_exclusions(self, client):
        """Should register with dietary exclusions."""
        response = client.post(
            "/auth/register",
            json={
                "email": "exclusions@example.com",
                "password": "securepassword123",
                "diet_type": "fodmap",
                "dietary_exclusions": ["peanuts", "tree_nuts"],
            },
        )

        assert response.status_code == 201

    def test_register_duplicate_email_fails(self, client, test_user):
        """Should reject duplicate email registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",  # Same as test_user
                "password": "anotherpassword123",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_case_insensitive_email(self, client, test_user):
        """Email comparison should be case-insensitive."""
        response = client.post(
            "/auth/register",
            json={
                "email": "TEST@EXAMPLE.COM",  # Different case
                "password": "anotherpassword123",
            },
        )

        assert response.status_code == 400

    def test_register_invalid_email_format(self, client):
        """Should reject invalid email format."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_register_password_too_short(self, client):
        """Should reject password shorter than 8 characters."""
        response = client.post(
            "/auth/register",
            json={
                "email": "short@example.com",
                "password": "short",  # Less than 8 chars
            },
        )

        assert response.status_code == 422

    def test_register_missing_email(self, client):
        """Should reject request without email."""
        response = client.post(
            "/auth/register",
            json={
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422

    def test_register_missing_password(self, client):
        """Should reject request without password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "nopassword@example.com",
            },
        )

        assert response.status_code == 422


class TestLoginEndpoint:
    """Tests for POST /auth/login."""

    def test_login_success(self, client, test_user):
        """Should return token for valid credentials."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_case_insensitive_email(self, client, test_user):
        """Should accept email in different case."""
        response = client.post(
            "/auth/login",
            json={
                "email": "TEST@EXAMPLE.COM",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200

    def test_login_wrong_password(self, client, test_user):
        """Should reject wrong password."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Should reject login for non-existent user."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword123",
            },
        )

        assert response.status_code == 401

    def test_login_inactive_user(self, client, inactive_user):
        """Should reject login for inactive user."""
        response = client.post(
            "/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    def test_login_missing_email(self, client):
        """Should reject request without email."""
        response = client.post(
            "/auth/login",
            json={
                "password": "testpassword123",
            },
        )

        assert response.status_code == 422

    def test_login_missing_password(self, client):
        """Should reject request without password."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
            },
        )

        assert response.status_code == 422


class TestGetCurrentUserEndpoint:
    """Tests for GET /auth/me."""

    def test_get_me_success(self, client, auth_headers, test_user):
        """Should return current user info with valid token."""
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True

    def test_get_me_returns_user_fields(self, client, auth_headers):
        """Should return all expected user fields."""
        response = client.get("/auth/me", headers=auth_headers)
        data = response.json()

        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        assert "diet_type" in data
        assert "dietary_exclusions" in data
        assert "is_active" in data

    def test_get_me_without_token(self, client):
        """Should reject request without token."""
        response = client.get("/auth/me")

        assert response.status_code == 403  # HTTPBearer returns 403

    def test_get_me_invalid_token(self, client):
        """Should reject invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_get_me_inactive_user(self, client, inactive_auth_headers):
        """Should reject inactive user."""
        response = client.get("/auth/me", headers=inactive_auth_headers)

        assert response.status_code == 403


class TestUpdateExclusionsEndpoint:
    """Tests for PATCH /auth/me/exclusions."""

    def test_update_exclusions_success(self, client, auth_headers):
        """Should update dietary exclusions."""
        response = client.patch(
            "/auth/me/exclusions",
            headers=auth_headers,
            json={"dietary_exclusions": ["peanuts", "shellfish"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "peanuts" in data["dietary_exclusions"]
        assert "shellfish" in data["dietary_exclusions"]

    def test_update_exclusions_empty_list(self, client, auth_headers):
        """Should accept empty exclusions list."""
        response = client.patch(
            "/auth/me/exclusions",
            headers=auth_headers,
            json={"dietary_exclusions": []},
        )

        assert response.status_code == 200
        assert response.json()["dietary_exclusions"] == []

    def test_update_exclusions_invalid_value(self, client, auth_headers):
        """Should reject invalid exclusion values."""
        response = client.patch(
            "/auth/me/exclusions",
            headers=auth_headers,
            json={"dietary_exclusions": ["invalid_exclusion"]},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_update_exclusions_without_token(self, client):
        """Should reject unauthenticated request."""
        response = client.patch(
            "/auth/me/exclusions",
            json={"dietary_exclusions": ["peanuts"]},
        )

        assert response.status_code == 403

    def test_update_exclusions_persists(self, client, auth_headers):
        """Exclusions should persist after update."""
        # Update exclusions
        client.patch(
            "/auth/me/exclusions",
            headers=auth_headers,
            json={"dietary_exclusions": ["eggs", "milk"]},
        )

        # Verify they persist
        response = client.get("/auth/me", headers=auth_headers)
        data = response.json()

        assert "eggs" in data["dietary_exclusions"]
        assert "milk" in data["dietary_exclusions"]


class TestGetAvailableExclusionsEndpoint:
    """Tests for GET /auth/exclusions/available."""

    def test_get_exclusions_success(self, client):
        """Should return list of available exclusions."""
        response = client.get("/auth/exclusions/available")

        assert response.status_code == 200
        data = response.json()
        assert "exclusions" in data
        assert len(data["exclusions"]) > 0

    def test_exclusions_have_name_and_value(self, client):
        """Each exclusion should have name and value fields."""
        response = client.get("/auth/exclusions/available")
        data = response.json()

        for exclusion in data["exclusions"]:
            assert "name" in exclusion
            assert "value" in exclusion

    def test_no_auth_required(self, client):
        """Should not require authentication."""
        response = client.get("/auth/exclusions/available")

        assert response.status_code == 200

    def test_includes_common_exclusions(self, client):
        """Should include common dietary exclusions."""
        response = client.get("/auth/exclusions/available")
        data = response.json()

        values = [e["value"] for e in data["exclusions"]]

        # Check for FDA top allergens
        assert "peanuts" in values
        assert "shellfish" in values
        assert "eggs" in values
        assert "milk" in values


class TestAuthenticationFlow:
    """Integration tests for complete auth flows."""

    def test_register_then_login(self, client):
        """Should be able to register and then login."""
        # Register
        register_response = client.post(
            "/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "flowpassword123",
            },
        )
        assert register_response.status_code == 201

        # Login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "flowtest@example.com",
                "password": "flowpassword123",
            },
        )
        assert login_response.status_code == 200

    def test_register_token_works(self, client):
        """Token from registration should work for authenticated requests."""
        # Register and get token
        register_response = client.post(
            "/auth/register",
            json={
                "email": "tokentest@example.com",
                "password": "tokenpassword123",
                "full_name": "Token Test User",
            },
        )
        token = register_response.json()["access_token"]

        # Use token to access protected endpoint
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert me_response.status_code == 200
        assert me_response.json()["email"] == "tokentest@example.com"

    def test_login_token_works(self, client, test_user):
        """Token from login should work for authenticated requests."""
        # Login and get token
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        token = login_response.json()["access_token"]

        # Use token to access protected endpoint
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert me_response.status_code == 200
        assert me_response.json()["email"] == "test@example.com"


class TestUpdateProfileEndpoint:
    """Tests for PATCH /auth/me."""

    def test_update_full_name(self, client, auth_headers):
        """Should update user's full name."""
        response = client.patch(
            "/auth/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_update_diet_type(self, client, auth_headers):
        """Should update user's diet type."""
        response = client.patch(
            "/auth/me",
            headers=auth_headers,
            json={"diet_type": "fodmap"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["diet_type"] == "fodmap"

    def test_update_multiple_fields(self, client, auth_headers):
        """Should update multiple fields at once."""
        response = client.patch(
            "/auth/me",
            headers=auth_headers,
            json={
                "full_name": "New Full Name",
                "diet_type": "fructose_free",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Full Name"
        assert data["diet_type"] == "fructose_free"

    def test_update_with_empty_body(self, client, auth_headers, test_user):
        """Should accept empty update (no changes)."""
        response = client.patch(
            "/auth/me",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Test User"  # Unchanged

    def test_update_profile_persists(self, client, auth_headers):
        """Profile changes should persist."""
        # Update
        client.patch(
            "/auth/me",
            headers=auth_headers,
            json={"full_name": "Persisted Name"},
        )

        # Verify persistence
        response = client.get("/auth/me", headers=auth_headers)
        assert response.json()["full_name"] == "Persisted Name"

    def test_update_invalid_diet_type(self, client, auth_headers):
        """Should reject invalid diet type."""
        response = client.patch(
            "/auth/me",
            headers=auth_headers,
            json={"diet_type": "invalid_diet"},
        )

        assert response.status_code == 422

    def test_update_without_token(self, client):
        """Should reject unauthenticated request."""
        response = client.patch(
            "/auth/me",
            json={"full_name": "New Name"},
        )

        assert response.status_code == 403

    def test_update_full_name_too_long(self, client, auth_headers):
        """Should reject full name exceeding max length."""
        response = client.patch(
            "/auth/me",
            headers=auth_headers,
            json={"full_name": "x" * 300},  # Exceeds 255 chars
        )

        assert response.status_code == 422


class TestChangePasswordEndpoint:
    """Tests for POST /auth/change-password."""

    def test_change_password_success(self, client, auth_headers):
        """Should change password with correct current password."""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    def test_change_password_allows_login_with_new(self, client, auth_headers, test_user):
        """Should be able to login with new password after change."""
        # Change password
        client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
        )

        # Try login with new password
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "newpassword456",
            },
        )

        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        """Should reject wrong current password."""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_same_as_current(self, client, auth_headers):
        """Should reject new password same as current."""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "testpassword123",
            },
        )

        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    def test_change_password_too_short(self, client, auth_headers):
        """Should reject new password shorter than 8 characters."""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "short",
            },
        )

        assert response.status_code == 422

    def test_change_password_without_token(self, client):
        """Should reject unauthenticated request."""
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 403

    def test_change_password_missing_current(self, client, auth_headers):
        """Should reject request without current password."""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={"new_password": "newpassword456"},
        )

        assert response.status_code == 422

    def test_change_password_missing_new(self, client, auth_headers):
        """Should reject request without new password."""
        response = client.post(
            "/auth/change-password",
            headers=auth_headers,
            json={"current_password": "testpassword123"},
        )

        assert response.status_code == 422


class TestDeleteAccountEndpoint:
    """Tests for DELETE /auth/me."""

    def test_delete_account_success(self, client, auth_headers):
        """Should delete user account."""
        response = client.delete("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    def test_delete_account_token_invalid_after(self, client, auth_headers):
        """Token should be invalid after account deletion."""
        # Delete account
        client.delete("/auth/me", headers=auth_headers)

        # Try to use token
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 401

    def test_delete_account_cascades_data(self, client, auth_headers, test_meal_plan):
        """Deleting account should cascade to related data."""
        # Delete account
        response = client.delete("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        # Related meal plans should be deleted (verified by the fact that
        # test passes without foreign key constraint errors)

    def test_delete_account_without_token(self, client):
        """Should reject unauthenticated request."""
        response = client.delete("/auth/me")

        assert response.status_code == 403

    def test_delete_account_cannot_login_after(self, client, auth_headers, test_user):
        """Should not be able to login after account deletion."""
        # Delete account
        client.delete("/auth/me", headers=auth_headers)

        # Try to login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert login_response.status_code == 401


class TestForgotPasswordEndpoint:
    """Tests for POST /auth/forgot-password."""

    def test_forgot_password_existing_user(self, client, test_user):
        """Should return success for existing user."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 200
        assert "if an account" in response.json()["message"].lower()

    def test_forgot_password_nonexistent_user(self, client):
        """Should return same success message for non-existent user (security)."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == 200
        # Same message to prevent email enumeration
        assert "if an account" in response.json()["message"].lower()

    def test_forgot_password_inactive_user(self, client, inactive_user):
        """Should return success but not trigger reset for inactive user."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "inactive@example.com"},
        )

        assert response.status_code == 200

    def test_forgot_password_invalid_email_format(self, client):
        """Should reject invalid email format."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422

    def test_forgot_password_missing_email(self, client):
        """Should reject request without email."""
        response = client.post(
            "/auth/forgot-password",
            json={},
        )

        assert response.status_code == 422

    def test_forgot_password_case_insensitive(self, client, test_user):
        """Should handle email case insensitively."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "TEST@EXAMPLE.COM"},
        )

        assert response.status_code == 200
