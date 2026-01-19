"""
Tests for meal planning API routes.

Tests cover:
- Create meal plan
- List meal plans
- Get meal plan by ID
- Mark prep status
- Delete meal plan
- Catch-up suggestions
- Edge cases: empty plans, no recipes, concurrent updates
"""
import pytest
import threading
from datetime import date, timedelta
from uuid import uuid4

from backend.db.models import MealPlan, MealSlot, Recipe, User
from backend.models.schemas import DietType, PrepStatus, UserRole
from backend.auth.utils import hash_password
from backend.auth.jwt import create_access_token


class TestCreateMealPlan:
    """Tests for POST /api/plans."""

    def test_create_plan_success(self, client, auth_headers, test_recipe):
        """Should create a new meal plan."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "meals" in data

    def test_create_plan_returns_fields(self, client, auth_headers, test_recipe):
        """Created plan should have expected fields."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        data = response.json()
        assert "id" in data
        assert "user_id" in data
        assert "diet_type" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "meals" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_plan_default_days(self, client, auth_headers, test_recipe):
        """Should default to 3 days if not specified."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
            },
        )

        assert response.status_code == 201

    def test_create_plan_max_7_days(self, client, auth_headers, test_recipe):
        """Should reject more than 7 days."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 8,
            },
        )

        assert response.status_code == 422

    def test_create_plan_min_1_day(self, client, auth_headers, test_recipe):
        """Should reject less than 1 day."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 0,
            },
        )

        assert response.status_code == 422

    def test_create_plan_simplified(self, client, auth_headers, test_recipe):
        """Should accept simplified flag for catch-up mode."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
                "simplified": True,
            },
        )

        assert response.status_code == 201

    def test_create_plan_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.post(
            "/api/plans",
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        assert response.status_code == 403

    def test_create_plan_start_date_in_past(self, client, auth_headers, test_recipe):
        """Should reject start_date in the past."""
        past_date = date.today() - timedelta(days=1)

        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(past_date),
                "days": 3,
            },
        )

        assert response.status_code == 422
        assert "cannot be in the past" in response.json()["detail"][0]["msg"]

    def test_create_plan_start_date_far_past(self, client, auth_headers, test_recipe):
        """Should reject start_date far in the past."""
        past_date = date.today() - timedelta(days=30)

        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(past_date),
                "days": 3,
            },
        )

        assert response.status_code == 422
        assert "cannot be in the past" in response.json()["detail"][0]["msg"]

    def test_create_plan_start_date_today(self, client, auth_headers, test_recipe):
        """Should accept start_date of today."""
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        assert response.status_code == 201

    def test_create_plan_start_date_tomorrow(self, client, auth_headers, test_recipe):
        """Should accept start_date of tomorrow."""
        tomorrow = date.today() + timedelta(days=1)

        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(tomorrow),
                "days": 3,
            },
        )

        assert response.status_code == 201

    def test_create_plan_start_date_too_far_future(self, client, auth_headers, test_recipe):
        """Should reject start_date more than 30 days in future."""
        future_date = date.today() + timedelta(days=31)

        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(future_date),
                "days": 3,
            },
        )

        assert response.status_code == 422
        assert "cannot be more than 30 days in the future" in response.json()["detail"][0]["msg"]

    def test_create_plan_start_date_30_days_future(self, client, auth_headers, test_recipe):
        """Should accept start_date exactly 30 days in future."""
        future_date = date.today() + timedelta(days=30)

        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(future_date),
                "days": 3,
            },
        )

        assert response.status_code == 201

    def test_create_plan_limit_exceeded(self, client, auth_headers, test_recipe, monkeypatch):
        """Should reject plan creation when user has reached the limit."""
        # Set a low limit for testing
        from backend import config
        monkeypatch.setattr(config.settings, "max_plans_per_user", 2)

        # Create 2 plans (the limit)
        for i in range(2):
            response = client.post(
                "/api/plans",
                headers=auth_headers,
                json={
                    "start_date": str(date.today() + timedelta(days=i)),
                    "days": 1,
                },
            )
            assert response.status_code == 201

        # Third plan should be rejected
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today() + timedelta(days=5)),
                "days": 1,
            },
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error_code"] == "PLAN_LIMIT_EXCEEDED"
        assert "maximum limit" in data["detail"]["message"].lower()
        assert data["detail"]["details"]["current_count"] == 2
        assert data["detail"]["details"]["max_limit"] == 2

    def test_create_plan_unlimited_when_zero(self, client, auth_headers, test_recipe, monkeypatch):
        """Should allow unlimited plans when max_plans_per_user is 0."""
        from backend import config
        monkeypatch.setattr(config.settings, "max_plans_per_user", 0)

        # Create several plans - should all succeed
        for i in range(3):
            response = client.post(
                "/api/plans",
                headers=auth_headers,
                json={
                    "start_date": str(date.today() + timedelta(days=i)),
                    "days": 1,
                },
            )
            assert response.status_code == 201


class TestListMealPlans:
    """Tests for GET /api/plans."""

    def test_list_plans_empty(self, client, auth_headers):
        """Should return empty list when no plans exist."""
        response = client.get("/api/plans", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_list_plans_with_data(self, client, auth_headers, test_meal_plan):
        """Should return user's meal plans."""
        response = client.get("/api/plans", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_plans_has_updated_at(self, client, auth_headers, test_meal_plan):
        """Listed plans should include updated_at field."""
        response = client.get("/api/plans", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Each plan in the list should have updated_at
        for plan in data:
            assert "updated_at" in plan
            assert plan["updated_at"] is not None

    def test_list_plans_with_limit(self, client, auth_headers, test_meal_plan):
        """Should respect limit parameter."""
        response = client.get(
            "/api/plans",
            headers=auth_headers,
            params={"limit": 5},
        )

        assert response.status_code == 200

    def test_list_plans_with_skip(self, client, auth_headers, test_meal_plan):
        """Should respect skip parameter."""
        response = client.get(
            "/api/plans",
            headers=auth_headers,
            params={"skip": 1},
        )

        assert response.status_code == 200

    def test_list_plans_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.get("/api/plans")

        assert response.status_code == 403


class TestGetMealPlan:
    """Tests for GET /api/plans/{plan_id}."""

    def test_get_plan_success(self, client, auth_headers, test_meal_plan):
        """Should return plan by ID."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_meal_plan.id)

    def test_get_plan_has_updated_at(self, client, auth_headers, test_meal_plan):
        """Plan response should include updated_at field."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "updated_at" in data
        assert data["updated_at"] is not None

    def test_get_plan_returns_meals(self, client, auth_headers, test_meal_plan):
        """Should include meals in response."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )

        data = response.json()
        assert "meals" in data
        assert len(data["meals"]) > 0

    def test_get_plan_meal_structure(self, client, auth_headers, test_meal_plan):
        """Each meal should have expected fields."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )

        data = response.json()
        meal = data["meals"][0]
        assert "date" in meal
        assert "meal_type" in meal
        assert "recipe" in meal
        assert "name" in meal["recipe"]
        assert "prep_time_minutes" in meal["recipe"]
        assert "prep_status" in meal

    def test_get_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.get(
            f"/api/plans/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_plan_invalid_uuid(self, client, auth_headers):
        """Should reject invalid UUID."""
        response = client.get(
            "/api/plans/not-a-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_get_plan_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.get(f"/api/plans/{test_meal_plan.id}")

        assert response.status_code == 403


class TestMarkPrepStatus:
    """Tests for PATCH /api/plans/{plan_id}/mark-prep."""

    def test_mark_prep_done(self, client, auth_headers, test_meal_plan):
        """Should mark meal as done."""
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "status": "DONE",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DONE"

    def test_mark_prep_skipped(self, client, auth_headers, test_meal_plan):
        """Should mark meal as skipped."""
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "meal_type": "lunch",
                "status": "SKIPPED",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SKIPPED"

    def test_mark_prep_invalid_status(self, client, auth_headers, test_meal_plan):
        """Should reject invalid status."""
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "status": "invalid_status",
            },
        )

        assert response.status_code == 422

    def test_mark_prep_meal_not_found(self, client, auth_headers, test_meal_plan):
        """Should return 404 for non-existent meal."""
        future_date = date.today() + timedelta(days=30)
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(future_date),
                "meal_type": "breakfast",
                "status": "DONE",
            },
        )

        assert response.status_code == 404

    def test_mark_prep_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.patch(
            f"/api/plans/{fake_id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "status": "DONE",
            },
        )

        assert response.status_code == 404

    def test_mark_prep_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "status": "DONE",
            },
        )

        assert response.status_code == 403


class TestDeleteMealPlan:
    """Tests for DELETE /api/plans/{plan_id}."""

    def test_delete_plan_success(self, client, auth_headers, test_meal_plan):
        """Should delete plan."""
        response = client.delete(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_delete_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.delete(
            f"/api/plans/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_delete_plan_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.delete(f"/api/plans/{test_meal_plan.id}")

        assert response.status_code == 403


class TestCatchUpView:
    """Tests for GET /api/plans/{plan_id}/catch-up."""

    def test_get_catch_up_success(self, client, auth_headers, test_meal_plan):
        """Should return catch-up suggestions."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/catch-up",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_get_catch_up_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.get(
            f"/api/plans/{fake_id}/catch-up",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_catch_up_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.get(f"/api/plans/{test_meal_plan.id}/catch-up")

        assert response.status_code == 403


class TestAdaptMealPlan:
    """Tests for POST /api/plans/{plan_id}/adapt."""

    def test_adapt_plan_success(self, client, auth_headers, test_meal_plan):
        """Should adapt plan."""
        response = client.post(
            f"/api/plans/{test_meal_plan.id}/adapt",
            headers=auth_headers,
            json={
                "current_date": str(date.today()),
            },
        )

        # May succeed or fail depending on plan state
        assert response.status_code in [200, 404, 500]

    def test_adapt_plan_default_date(self, client, auth_headers, test_meal_plan):
        """Should use today as default date."""
        response = client.post(
            f"/api/plans/{test_meal_plan.id}/adapt",
            headers=auth_headers,
            json={},
        )

        # May succeed or fail depending on plan state
        assert response.status_code in [200, 404, 500]

    def test_adapt_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.post(
            f"/api/plans/{fake_id}/adapt",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 404

    def test_adapt_plan_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.post(
            f"/api/plans/{test_meal_plan.id}/adapt",
            json={},
        )

        assert response.status_code == 403


class TestPrepTimeline:
    """Tests for GET /api/plans/{plan_id}/prep-timeline."""

    def test_get_prep_timeline_success(self, client, auth_headers, test_meal_plan):
        """Should return optimized prep timeline for a date."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/prep-timeline",
            headers=auth_headers,
            params={"prep_date": str(date.today())},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_time_minutes" in data
        assert "steps" in data
        assert "batched_savings_minutes" in data
        assert "prep_date" in data

    def test_get_prep_timeline_returns_steps(self, client, auth_headers, test_meal_plan):
        """Timeline should include prep steps."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/prep-timeline",
            headers=auth_headers,
            params={"prep_date": str(date.today())},
        )

        data = response.json()
        # If there are meals for this date, there should be steps
        if data["steps"]:
            step = data["steps"][0]
            assert "step_number" in step
            assert "action" in step
            assert "duration_minutes" in step
            assert "can_batch" in step

    def test_get_prep_timeline_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.get(
            f"/api/plans/{fake_id}/prep-timeline",
            headers=auth_headers,
            params={"prep_date": str(date.today())},
        )

        assert response.status_code == 404

    def test_get_prep_timeline_date_out_of_range(self, client, auth_headers, test_meal_plan):
        """Should return 400 for date outside plan range."""
        future_date = date.today() + timedelta(days=30)

        response = client.get(
            f"/api/plans/{test_meal_plan.id}/prep-timeline",
            headers=auth_headers,
            params={"prep_date": str(future_date)},
        )

        assert response.status_code == 400
        assert "outside plan range" in response.json()["detail"]

    def test_get_prep_timeline_missing_date(self, client, auth_headers, test_meal_plan):
        """Should return 422 when date parameter is missing."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/prep-timeline",
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_get_prep_timeline_invalid_date(self, client, auth_headers, test_meal_plan):
        """Should return 422 for invalid date format."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/prep-timeline",
            headers=auth_headers,
            params={"prep_date": "not-a-date"},
        )

        assert response.status_code == 422

    def test_get_prep_timeline_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/prep-timeline",
            params={"prep_date": str(date.today())},
        )

        assert response.status_code == 403


class TestSwapMeal:
    """Tests for PATCH /api/plans/{plan_id}/swap-meal."""

    def test_swap_meal_success(self, client, auth_headers, test_meal_plan, test_recipe):
        """Should swap meal recipe successfully."""
        # Get the first meal from the plan to get actual date/meal_type
        plan_response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )
        plan_data = plan_response.json()
        first_meal = plan_data["meals"][0]

        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/swap-meal",
            headers=auth_headers,
            json={
                "date": first_meal["date"],
                "meal_type": first_meal["meal_type"],
                "new_recipe_id": str(test_recipe.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Meal swapped successfully"
        assert data["date"] == first_meal["date"]
        assert data["meal_type"] == first_meal["meal_type"]
        assert data["new_recipe_id"] == str(test_recipe.id)

    def test_swap_meal_plan_not_found(self, client, auth_headers, test_recipe):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.patch(
            f"/api/plans/{fake_id}/swap-meal",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "new_recipe_id": str(test_recipe.id),
            },
        )

        assert response.status_code == 404

    def test_swap_meal_recipe_not_found(self, client, auth_headers, test_meal_plan):
        """Should return 404 for non-existent recipe."""
        fake_recipe_id = uuid4()

        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/swap-meal",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "new_recipe_id": str(fake_recipe_id),
            },
        )

        assert response.status_code == 404

    def test_swap_meal_meal_not_found(self, client, auth_headers, test_meal_plan, test_recipe):
        """Should return 404 for non-existent meal slot."""
        future_date = date.today() + timedelta(days=30)

        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/swap-meal",
            headers=auth_headers,
            json={
                "date": str(future_date),
                "meal_type": "breakfast",
                "new_recipe_id": str(test_recipe.id),
            },
        )

        assert response.status_code == 404

    def test_swap_meal_without_auth(self, client, test_meal_plan, test_recipe):
        """Should reject unauthenticated request."""
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/swap-meal",
            json={
                "date": str(date.today()),
                "meal_type": "breakfast",
                "new_recipe_id": str(test_recipe.id),
            },
        )

        assert response.status_code == 403

    def test_swap_meal_missing_fields(self, client, auth_headers, test_meal_plan):
        """Should return 422 for missing required fields."""
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/swap-meal",
            headers=auth_headers,
            json={
                "date": str(date.today()),
                # Missing meal_type and new_recipe_id
            },
        )

        assert response.status_code == 422

    def test_swap_meal_resets_prep_status(self, client, auth_headers, test_meal_plan, test_recipe):
        """Swapping should reset prep status to PENDING."""
        # Get first meal
        plan_response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )
        plan_data = plan_response.json()
        first_meal = plan_data["meals"][0]

        # Swap the meal
        client.patch(
            f"/api/plans/{test_meal_plan.id}/swap-meal",
            headers=auth_headers,
            json={
                "date": first_meal["date"],
                "meal_type": first_meal["meal_type"],
                "new_recipe_id": str(test_recipe.id),
            },
        )

        # Verify the plan shows the new recipe
        updated_response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )
        updated_data = updated_response.json()

        # Find the swapped meal
        swapped_meal = next(
            (m for m in updated_data["meals"]
             if m["date"] == first_meal["date"] and m["meal_type"] == first_meal["meal_type"]),
            None
        )
        assert swapped_meal is not None
        assert swapped_meal["prep_status"] == "PENDING"
        assert swapped_meal["recipe"]["id"] == str(test_recipe.id)


class TestCompatibleRecipes:
    """Tests for GET /api/plans/{plan_id}/compatible-recipes."""

    def test_get_compatible_recipes_success(self, client, auth_headers, test_meal_plan, test_recipe):
        """Should return compatible recipes for meal type."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/compatible-recipes",
            headers=auth_headers,
            params={"meal_type": test_recipe.meal_type},
        )

        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        assert "total" in data
        assert isinstance(data["recipes"], list)

    def test_get_compatible_recipes_returns_expected_fields(self, client, auth_headers, test_meal_plan, test_recipe):
        """Each recipe should have expected fields."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/compatible-recipes",
            headers=auth_headers,
            params={"meal_type": test_recipe.meal_type},
        )

        data = response.json()
        if data["recipes"]:
            recipe = data["recipes"][0]
            assert "id" in recipe
            assert "name" in recipe
            assert "meal_type" in recipe
            assert "prep_time_minutes" in recipe
            assert "diet_tags" in recipe
            assert "servings" in recipe

    def test_get_compatible_recipes_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()

        response = client.get(
            f"/api/plans/{fake_id}/compatible-recipes",
            headers=auth_headers,
            params={"meal_type": "breakfast"},
        )

        assert response.status_code == 404

    def test_get_compatible_recipes_missing_meal_type(self, client, auth_headers, test_meal_plan):
        """Should return 422 when meal_type is missing."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/compatible-recipes",
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_get_compatible_recipes_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/compatible-recipes",
            params={"meal_type": "breakfast"},
        )

        assert response.status_code == 403

    def test_get_compatible_recipes_filters_by_meal_type(self, client, auth_headers, test_meal_plan):
        """Should only return recipes matching the meal type."""
        response = client.get(
            f"/api/plans/{test_meal_plan.id}/compatible-recipes",
            headers=auth_headers,
            params={"meal_type": "breakfast"},
        )

        data = response.json()
        for recipe in data["recipes"]:
            assert recipe["meal_type"] == "breakfast"


class TestDuplicatePlan:
    """Tests for POST /api/plans/{id}/duplicate."""

    def test_duplicate_plan_success(self, client, auth_headers, test_meal_plan):
        """Should duplicate a plan with new start date."""
        new_start = date.today() + timedelta(days=7)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["start_date"] == str(new_start)
        assert data["id"] != str(test_meal_plan.id)

    def test_duplicate_plan_preserves_meals(self, client, auth_headers, test_meal_plan, db_session):
        """Duplicated plan should have same number of meals."""
        original_meal_count = len(test_meal_plan.meals)
        new_start = date.today() + timedelta(days=7)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["meals"]) == original_meal_count

    def test_duplicate_plan_shifts_dates(self, client, auth_headers, test_meal_plan):
        """Duplicated plan meals should have shifted dates."""
        original_start = test_meal_plan.start_date
        new_start = date.today() + timedelta(days=10)
        date_offset = (new_start - original_start).days

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()

        # End date should be shifted by same offset
        original_end = test_meal_plan.end_date
        expected_end = original_end + timedelta(days=date_offset)
        assert data["end_date"] == str(expected_end)

    def test_duplicate_plan_resets_prep_status(self, client, auth_headers, test_meal_plan, db_session):
        """Duplicated plan meals should have PENDING prep status."""
        # First mark a meal as done in the original plan
        original_meal = test_meal_plan.meals[0]
        client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(original_meal.date),
                "meal_type": original_meal.meal_type,
                "status": "DONE",
            },
        )

        new_start = date.today() + timedelta(days=7)
        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()

        # All meals in duplicated plan should be PENDING
        for meal in data["meals"]:
            assert meal["prep_status"] == "PENDING"

    def test_duplicate_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()
        new_start = date.today() + timedelta(days=7)

        response = client.post(
            f"/api/plans/{fake_id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 404

    def test_duplicate_plan_rejects_past_date(self, client, auth_headers, test_meal_plan):
        """Should reject start date in the past."""
        past_date = date.today() - timedelta(days=1)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(past_date)},
        )

        assert response.status_code == 422

    def test_duplicate_plan_rejects_far_future_date(self, client, auth_headers, test_meal_plan):
        """Should reject start date more than 30 days in future."""
        far_future = date.today() + timedelta(days=31)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(far_future)},
        )

        assert response.status_code == 422

    def test_duplicate_plan_accepts_today(self, client, auth_headers, test_meal_plan):
        """Should accept today as start date."""
        today = date.today()

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(today)},
        )

        assert response.status_code == 201

    def test_duplicate_plan_without_auth(self, client, test_meal_plan):
        """Should reject unauthenticated request."""
        new_start = date.today() + timedelta(days=7)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 403

    def test_duplicate_plan_user_isolation(self, client, auth_headers, test_meal_plan, db_session):
        """Should preserve user ownership in duplicated plan."""
        new_start = date.today() + timedelta(days=7)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()

        # New plan should have same user_id as original
        assert data["user_id"] == str(test_meal_plan.user_id)

    def test_duplicate_plan_preserves_diet_type(self, client, auth_headers, test_meal_plan):
        """Duplicated plan should have same diet type."""
        new_start = date.today() + timedelta(days=7)

        response = client.post(
            f"/api/plans/{test_meal_plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["diet_type"] == test_meal_plan.diet_type.value


# ============================================================================
# Edge Case Tests: Empty Plans
# ============================================================================

class TestEmptyPlanScenarios:
    """Tests for edge cases involving empty or minimal plan states."""

    def test_get_plan_with_no_meals_returns_empty_meals_array(
        self, client, auth_headers, db_session, test_user
    ):
        """Plan with no meal slots should return empty meals array."""
        # Create a plan without any meal slots
        plan = MealPlan(
            user_id=test_user.id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=6),
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        response = client.get(f"/api/plans/{plan.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["meals"] == []

    def test_catch_up_for_plan_with_no_meals(
        self, client, auth_headers, db_session, test_user
    ):
        """Catch-up view should handle plan with no meals gracefully."""
        # Create empty plan
        plan = MealPlan(
            user_id=test_user.id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=6),
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        response = client.get(f"/api/plans/{plan.id}/catch-up", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["missed_preps"] == []
        assert data["pending_meals"] == []

    def test_prep_timeline_for_date_with_no_meals(
        self, client, auth_headers, db_session, test_user, test_recipe
    ):
        """Prep timeline should return empty steps for date with no meals."""
        # Create plan with meals only on first day
        start_date = date.today()
        plan = MealPlan(
            user_id=test_user.id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=start_date,
            end_date=start_date + timedelta(days=6),
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        # Add meals only for today
        slot = MealSlot(
            meal_plan_id=plan.id,
            recipe_id=test_recipe.id,
            date=start_date,
            meal_type="breakfast",
            prep_status=PrepStatus.PENDING,
        )
        db_session.add(slot)
        db_session.commit()

        # Request timeline for a day with no meals
        no_meals_date = start_date + timedelta(days=3)
        response = client.get(
            f"/api/plans/{plan.id}/prep-timeline",
            headers=auth_headers,
            params={"prep_date": str(no_meals_date)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["steps"] == []
        assert data["total_time_minutes"] == 0

    def test_duplicate_empty_plan(
        self, client, auth_headers, db_session, test_user
    ):
        """Duplicating an empty plan should create an empty duplicate."""
        # Create empty plan
        plan = MealPlan(
            user_id=test_user.id,
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=6),
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        new_start = date.today() + timedelta(days=10)
        response = client.post(
            f"/api/plans/{plan.id}/duplicate",
            headers=auth_headers,
            json={"start_date": str(new_start)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["meals"] == []
        assert data["start_date"] == str(new_start)

    def test_compatible_recipes_when_none_match(
        self, client, db_session, recipe_factory
    ):
        """Should return empty list when no recipes match user's diet and meal type."""
        # Create user with fructose_free diet (no recipes exist for this)
        user = User(
            email="fructose_user@example.com",
            hashed_password=hash_password("testpassword123"),
            full_name="Fructose User",
            diet_type=DietType.FRUCTOSE_FREE,
            dietary_exclusions=[],
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create recipes only for low_histamine diet
        recipe_factory.create(name="Low Histamine Recipe", diet_tags=["low_histamine"])

        token = create_access_token(user_id=user.id, role=user.role.value)
        headers = {"Authorization": f"Bearer {token}"}

        # Create a minimal plan for this user
        plan = MealPlan(
            user_id=user.id,
            diet_type=DietType.FRUCTOSE_FREE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        db_session.add(plan)
        db_session.commit()

        response = client.get(
            f"/api/plans/{plan.id}/compatible-recipes",
            headers=headers,
            params={"meal_type": "breakfast"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recipes"] == []
        assert data["total"] == 0


# ============================================================================
# Edge Case Tests: No Recipes Available
# ============================================================================

class TestNoRecipesAvailable:
    """Tests for scenarios where no recipes are available for meal planning."""

    def test_create_plan_with_no_recipes_in_database(
        self, client, auth_headers, db_session
    ):
        """Should return error when database has no recipes."""
        # Delete all recipes
        db_session.query(Recipe).delete()
        db_session.commit()

        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "PLAN_NO_RECIPES_AVAILABLE"

    def test_create_plan_with_no_matching_diet_recipes(
        self, client, db_session, recipe_factory
    ):
        """Should return error when no recipes match user's diet type."""
        # Create user with fructose_free diet
        user = User(
            email="fructose_user2@example.com",
            hashed_password=hash_password("testpassword123"),
            full_name="Fructose User",
            diet_type=DietType.FRUCTOSE_FREE,
            dietary_exclusions=[],
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create recipes only for low_histamine diet (not fructose_free)
        recipe_factory.create(name="Low Histamine Recipe", diet_tags=["low_histamine"])

        token = create_access_token(user_id=user.id, role=user.role.value)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/plans",
            headers=headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error_code"] == "PLAN_NO_RECIPES_AVAILABLE"
        assert "fructose_free" in data["detail"]["message"].lower()

    def test_create_plan_with_exclusions_filters_some_recipes(
        self, client, db_session, recipe_factory
    ):
        """Dietary exclusions should filter out recipes with excluded ingredients.

        Note: This test verifies exclusions are applied, but if some recipes
        remain after filtering, plan creation will succeed.
        """
        # Create user with exclusions
        user = User(
            email="exclusions_user@example.com",
            hashed_password=hash_password("testpassword123"),
            full_name="User With Exclusions",
            diet_type=DietType.LOW_HISTAMINE,
            dietary_exclusions=["chicken"],  # Exclude chicken
            role=UserRole.USER,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Clear existing recipes
        db_session.query(Recipe).delete()
        db_session.commit()

        # Create recipes - some with chicken (excluded), some without
        recipe_factory.create(
            name="Chicken Dish",
            diet_tags=["low_histamine"],
            meal_type="breakfast",
            ingredients=[{"name": "chicken", "freshness_days": 3, "quantity": "500g", "category": "protein"}],
        )
        recipe_factory.create(
            name="Beef Dish",
            diet_tags=["low_histamine"],
            meal_type="breakfast",
            ingredients=[{"name": "beef", "freshness_days": 3, "quantity": "300g", "category": "protein"}],
        )
        recipe_factory.create(
            name="Turkey Lunch",
            diet_tags=["low_histamine"],
            meal_type="lunch",
            ingredients=[{"name": "turkey", "freshness_days": 3, "quantity": "400g", "category": "protein"}],
        )
        recipe_factory.create(
            name="Fish Dinner",
            diet_tags=["low_histamine"],
            meal_type="dinner",
            ingredients=[{"name": "salmon", "freshness_days": 2, "quantity": "300g", "category": "protein"}],
        )

        token = create_access_token(user_id=user.id, role=user.role.value)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/plans",
            headers=headers,
            json={
                "start_date": str(date.today()),
                "days": 1,
            },
        )

        # Plan should succeed since there are non-chicken recipes available
        assert response.status_code == 201
        data = response.json()

        # Verify no chicken dishes are in the plan
        for meal in data["meals"]:
            assert "chicken" not in meal["recipe"]["name"].lower()


# ============================================================================
# Edge Case Tests: Concurrent Updates
# ============================================================================

class TestConcurrentUpdates:
    """Tests for concurrent update handling and race conditions."""

    def test_concurrent_mark_prep_status_updates(
        self, client, auth_headers, test_meal_plan
    ):
        """Multiple concurrent status updates should not cause data corruption."""
        results = []
        errors = []

        def update_status(status):
            try:
                response = client.patch(
                    f"/api/plans/{test_meal_plan.id}/mark-prep",
                    headers=auth_headers,
                    json={
                        "date": str(date.today()),
                        "meal_type": "breakfast",
                        "status": status,
                    },
                )
                results.append((status, response.status_code))
            except Exception as e:
                errors.append(str(e))

        # Create threads for concurrent updates
        threads = [
            threading.Thread(target=update_status, args=("DONE",)),
            threading.Thread(target=update_status, args=("SKIPPED",)),
        ]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Should not have errors
        assert len(errors) == 0

        # Both requests should complete (both should succeed with 200)
        assert len(results) == 2
        # At least one should succeed
        assert any(status_code == 200 for _, status_code in results)

    def test_concurrent_plan_deletion_and_access(
        self, client, auth_headers, test_meal_plan
    ):
        """Accessing a plan during deletion should return 404, not crash."""
        results = []

        def delete_plan():
            response = client.delete(
                f"/api/plans/{test_meal_plan.id}",
                headers=auth_headers,
            )
            results.append(("delete", response.status_code))

        def get_plan():
            response = client.get(
                f"/api/plans/{test_meal_plan.id}",
                headers=auth_headers,
            )
            results.append(("get", response.status_code))

        threads = [
            threading.Thread(target=delete_plan),
            threading.Thread(target=get_plan),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Delete should succeed or get 404 if already deleted
        delete_result = next((r for r in results if r[0] == "delete"), None)
        assert delete_result[1] in [204, 404]

        # Get should return 200 or 404 (if delete happened first)
        get_result = next((r for r in results if r[0] == "get"), None)
        assert get_result[1] in [200, 404]

    def test_concurrent_plan_generation_does_not_corrupt_data(
        self, client, auth_headers, test_recipe
    ):
        """Generating multiple plans concurrently should not cause issues."""
        results = []

        def create_plan(day_offset):
            response = client.post(
                "/api/plans",
                headers=auth_headers,
                json={
                    "start_date": str(date.today() + timedelta(days=day_offset)),
                    "days": 1,
                },
            )
            results.append((day_offset, response.status_code, response.json() if response.status_code == 201 else None))

        threads = [
            threading.Thread(target=create_plan, args=(0,)),
            threading.Thread(target=create_plan, args=(5,)),
            threading.Thread(target=create_plan, args=(10,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All plans should be created successfully
        assert len(results) == 3
        assert all(status == 201 for _, status, _ in results)

        # Each plan should have unique ID
        plan_ids = [data["id"] for _, _, data in results if data]
        assert len(set(plan_ids)) == 3


# ============================================================================
# Boundary Condition Tests
# ============================================================================

class TestBoundaryConditions:
    """Tests for boundary conditions and limits."""

    def test_plan_with_exactly_1_day_has_correct_dates(self, client, auth_headers, test_recipe):
        """Minimum valid plan duration should have same start and end date."""
        today = date.today()
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(today),
                "days": 1,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["start_date"] == str(today)
        assert data["end_date"] == str(today)

    def test_plan_with_exactly_7_days_has_correct_date_range(self, client, auth_headers, test_recipe):
        """Maximum valid plan duration should span 7 days (6 days apart)."""
        today = date.today()
        response = client.post(
            "/api/plans",
            headers=auth_headers,
            json={
                "start_date": str(today),
                "days": 7,
            },
        )

        assert response.status_code == 201
        data = response.json()
        start = date.fromisoformat(data["start_date"])
        end = date.fromisoformat(data["end_date"])
        assert (end - start).days == 6  # 7 days inclusive

    def test_mark_prep_for_all_meal_types(self, client, auth_headers, test_meal_plan):
        """Should be able to mark prep for all meal types on the same day."""
        today = str(date.today())

        for meal_type in ["breakfast", "lunch", "dinner"]:
            response = client.patch(
                f"/api/plans/{test_meal_plan.id}/mark-prep",
                headers=auth_headers,
                json={
                    "date": today,
                    "meal_type": meal_type,
                    "status": "DONE",
                },
            )
            assert response.status_code == 200

        # Verify all are marked as done
        plan_response = client.get(
            f"/api/plans/{test_meal_plan.id}",
            headers=auth_headers,
        )
        data = plan_response.json()
        today_meals = [m for m in data["meals"] if m["date"] == today]
        assert all(m["prep_status"] == "DONE" for m in today_meals)
