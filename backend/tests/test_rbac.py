"""
Tests for Role-Based Access Control (RBAC) functionality.

Tests cover:
- Role assignment and token claims
- Admin-only endpoint protection
- Recipe CRUD operations (admin only)
- User management operations (admin only)
- Role checking dependencies
"""
import pytest
from fastapi import status


class TestRoleAssignment:
    """Tests for user role assignment and token claims."""

    def test_new_user_has_user_role(self, client):
        """New users should have 'user' role by default."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "diet_type": "low_histamine",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Login and check profile
        login_response = client.post(
            "/auth/login",
            json={"email": "newuser@example.com", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        profile_response = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.json()["role"] == "user"

    def test_user_response_includes_role(self, client, auth_headers):
        """User response should include role field."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "role" in response.json()
        assert response.json()["role"] == "user"

    def test_admin_response_includes_role(self, client, admin_auth_headers):
        """Admin response should include admin role."""
        response = client.get("/auth/me", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["role"] == "admin"


class TestAdminRecipeCRUD:
    """Tests for admin-only recipe CRUD operations."""

    def test_create_recipe_requires_admin(self, client, auth_headers):
        """Regular users cannot create recipes."""
        response = client.post(
            "/api/recipes",
            headers=auth_headers,
            json={
                "name": "Test Recipe",
                "diet_tags": ["low_histamine"],
                "meal_type": "dinner",
                "ingredients": [
                    {"name": "chicken", "quantity": "500g", "freshness_days": 3}
                ],
                "prep_steps": ["Cook chicken"],
                "prep_time_minutes": 30,
                "reusability_index": 0.7,
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in response.json()["detail"]

    def test_create_recipe_as_admin(self, client, admin_auth_headers):
        """Admin can create recipes."""
        response = client.post(
            "/api/recipes",
            headers=admin_auth_headers,
            json={
                "name": "Admin Created Recipe",
                "diet_tags": ["low_histamine"],
                "meal_type": "dinner",
                "ingredients": [
                    {"name": "chicken", "quantity": "500g", "freshness_days": 3}
                ],
                "prep_steps": ["Cook chicken", "Serve"],
                "prep_time_minutes": 30,
                "reusability_index": 0.7,
                "servings": 2,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "Admin Created Recipe"

    def test_create_recipe_duplicate_name(self, client, admin_auth_headers, test_recipe):
        """Cannot create recipe with duplicate name."""
        response = client.post(
            "/api/recipes",
            headers=admin_auth_headers,
            json={
                "name": test_recipe.name,  # Same name as existing recipe
                "diet_tags": ["low_histamine"],
                "meal_type": "dinner",
                "ingredients": [
                    {"name": "chicken", "quantity": "500g", "freshness_days": 3}
                ],
                "prep_steps": ["Cook chicken"],
                "prep_time_minutes": 30,
                "reusability_index": 0.7,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_update_recipe_requires_admin(self, client, auth_headers, test_recipe):
        """Regular users cannot update recipes."""
        response = client.put(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
            json={"name": "Updated Recipe Name"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_recipe_as_admin(self, client, admin_auth_headers, test_recipe):
        """Admin can update recipes."""
        response = client.put(
            f"/api/recipes/{test_recipe.id}",
            headers=admin_auth_headers,
            json={"name": "Updated Recipe Name", "prep_time_minutes": 45},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Updated Recipe Name"
        assert response.json()["prep_time_minutes"] == 45

    def test_delete_recipe_requires_admin(self, client, auth_headers, test_recipe):
        """Regular users cannot delete recipes."""
        response = client.delete(
            f"/api/recipes/{test_recipe.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_recipe_as_admin(self, client, admin_auth_headers, db_session):
        """Admin can delete recipes not in use."""
        from backend.db.models import Recipe

        # Create a recipe not used by any meal plans
        recipe = Recipe(
            name="Recipe To Delete",
            diet_tags=["low_histamine"],
            meal_type="lunch",
            ingredients=[{"name": "salad", "quantity": "1 bowl", "freshness_days": 3}],
            prep_steps=["Make salad"],
            prep_time_minutes=10,
            reusability_index=0.5,
            servings=1,
        )
        db_session.add(recipe)
        db_session.commit()
        db_session.refresh(recipe)

        response = client.delete(
            f"/api/recipes/{recipe.id}", headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_delete_recipe_in_use(self, client, admin_auth_headers, test_meal_plan, test_recipe):
        """Cannot delete recipe that is in use by meal plans."""
        response = client.delete(
            f"/api/recipes/{test_recipe.id}", headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "referenced by existing meal plans" in response.json()["detail"]


class TestAdminUserManagement:
    """Tests for admin user management endpoints."""

    def test_list_users_requires_admin(self, client, auth_headers):
        """Regular users cannot list all users."""
        response = client.get("/api/admin/users", headers=auth_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_as_admin(self, client, admin_auth_headers, test_user):
        """Admin can list all users."""
        response = client.get("/api/admin/users", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 2  # At least admin_user and test_user

    def test_list_users_filter_by_role(self, client, admin_auth_headers, test_user):
        """Admin can filter users by role."""
        response = client.get(
            "/api/admin/users", headers=admin_auth_headers, params={"role": "admin"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for user in data["users"]:
            assert user["role"] == "admin"

    def test_list_users_filter_by_status(self, client, admin_auth_headers, inactive_user):
        """Admin can filter users by active status."""
        response = client.get(
            "/api/admin/users",
            headers=admin_auth_headers,
            params={"is_active": False},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for user in data["users"]:
            assert user["is_active"] is False

    def test_get_user_requires_admin(self, client, auth_headers, test_user):
        """Regular users cannot get other user details."""
        response = client.get(
            f"/api/admin/users/{test_user.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_user_as_admin(self, client, admin_auth_headers, test_user):
        """Admin can get specific user details."""
        response = client.get(
            f"/api/admin/users/{test_user.id}", headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["email"] == test_user.email

    def test_update_user_role_requires_admin(self, client, auth_headers, test_user):
        """Regular users cannot change user roles."""
        response = client.patch(
            f"/api/admin/users/{test_user.id}/role",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_role_as_admin(
        self, client, admin_auth_headers, user_factory
    ):
        """Admin can update another user's role."""
        other_user = user_factory.create(email="other@example.com")

        response = client.patch(
            f"/api/admin/users/{other_user.id}/role",
            headers=admin_auth_headers,
            json={"role": "admin"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["role"] == "admin"

    def test_admin_cannot_demote_self(self, client, admin_auth_headers, admin_user):
        """Admin cannot demote themselves."""
        response = client.patch(
            f"/api/admin/users/{admin_user.id}/role",
            headers=admin_auth_headers,
            json={"role": "user"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot demote yourself" in response.json()["detail"]

    def test_update_user_status_as_admin(
        self, client, admin_auth_headers, user_factory
    ):
        """Admin can deactivate another user."""
        other_user = user_factory.create(email="deactivate@example.com")

        response = client.patch(
            f"/api/admin/users/{other_user.id}/status",
            headers=admin_auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["is_active"] is False

    def test_admin_cannot_deactivate_self(self, client, admin_auth_headers, admin_user):
        """Admin cannot deactivate themselves."""
        response = client.patch(
            f"/api/admin/users/{admin_user.id}/status",
            headers=admin_auth_headers,
            json={"is_active": False},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot deactivate yourself" in response.json()["detail"]

    def test_delete_user_requires_admin(self, client, auth_headers, user_factory):
        """Regular users cannot delete other users."""
        other_user = user_factory.create(email="todelete@example.com")

        response = client.delete(
            f"/api/admin/users/{other_user.id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_as_admin(self, client, admin_auth_headers, user_factory):
        """Admin can delete another user."""
        other_user = user_factory.create(email="deleteme@example.com")

        response = client.delete(
            f"/api/admin/users/{other_user.id}", headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_admin_cannot_delete_self(self, client, admin_auth_headers, admin_user):
        """Admin cannot delete themselves."""
        response = client.delete(
            f"/api/admin/users/{admin_user.id}", headers=admin_auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot delete yourself" in response.json()["detail"]

    def test_get_admin_stats(self, client, admin_auth_headers, test_user, test_recipe):
        """Admin can get dashboard statistics."""
        response = client.get("/api/admin/stats", headers=admin_auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "recipes" in data
        assert "meal_plans" in data
        assert data["users"]["total"] >= 2


class TestRegularUserAccess:
    """Tests ensuring regular users can access their normal endpoints."""

    def test_user_can_read_recipes(self, client, auth_headers, test_recipe):
        """Regular users can still read recipes."""
        response = client.get("/api/recipes", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_user_can_get_single_recipe(self, client, auth_headers, test_recipe):
        """Regular users can get specific recipe details."""
        response = client.get(f"/api/recipes/{test_recipe.id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

    def test_user_can_search_recipes(self, client, auth_headers, test_recipe):
        """Regular users can search recipes by ingredient."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "chicken"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_user_can_manage_own_profile(self, client, auth_headers):
        """Regular users can update their own profile."""
        response = client.patch(
            "/auth/me", headers=auth_headers, json={"full_name": "Updated Name"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["full_name"] == "Updated Name"


class TestUnauthenticatedAccess:
    """Tests ensuring unauthenticated users cannot access protected endpoints."""

    def test_admin_endpoints_require_auth(self, client):
        """Admin endpoints require authentication."""
        response = client.get("/api/admin/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_recipe_crud_requires_auth(self, client):
        """Recipe CRUD operations require authentication."""
        response = client.post(
            "/api/recipes",
            json={
                "name": "Test",
                "diet_tags": ["low_histamine"],
                "meal_type": "dinner",
                "ingredients": [{"name": "x", "quantity": "1", "freshness_days": 1}],
                "prep_steps": ["step"],
                "prep_time_minutes": 10,
                "reusability_index": 0.5,
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
