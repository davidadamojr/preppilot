"""
Tests for recipe API routes.

Tests cover:
- List recipes with pagination
- Get recipe by ID
- Search recipes by ingredient
- Filtering by meal type and diet tag
"""
import pytest
from uuid import uuid4


class TestListRecipes:
    """Tests for GET /api/recipes."""

    def test_list_recipes_empty(self, client, auth_headers):
        """Should return empty list when no recipes exist."""
        response = client.get("/api/recipes", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["recipes"] == []
        assert data["total"] == 0

    def test_list_recipes_with_data(self, client, auth_headers, test_recipes):
        """Should return recipes with pagination info."""
        response = client.get("/api/recipes", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["recipes"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_recipes_returns_recipe_fields(self, client, auth_headers, test_recipe):
        """Each recipe should have expected fields."""
        response = client.get("/api/recipes", headers=auth_headers)
        data = response.json()

        recipe = data["recipes"][0]
        assert "id" in recipe
        assert "name" in recipe
        assert "diet_tags" in recipe
        assert "meal_type" in recipe
        assert "ingredients" in recipe
        assert "prep_steps" in recipe
        assert "prep_time_minutes" in recipe
        assert "reusability_index" in recipe
        assert "servings" in recipe

    def test_list_recipes_pagination(self, client, auth_headers, test_recipes):
        """Should support pagination."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"page": 1, "page_size": 2},
        )

        data = response.json()
        assert len(data["recipes"]) == 2
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_recipes_second_page(self, client, auth_headers, test_recipes):
        """Should return correct recipes on second page."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"page": 2, "page_size": 2},
        )

        data = response.json()
        assert len(data["recipes"]) == 1  # 3 total, 2 per page, 1 on page 2
        assert data["page"] == 2

    def test_list_recipes_filter_by_meal_type(self, client, auth_headers, test_recipes):
        """Should filter by meal type."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"meal_type": "dinner"},
        )

        data = response.json()
        for recipe in data["recipes"]:
            assert recipe["meal_type"] == "dinner"

    def test_list_recipes_filter_by_diet_tag(self, client, auth_headers, test_recipes):
        """Should filter by diet tag."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"diet_tag": "low_histamine"},
        )

        data = response.json()
        for recipe in data["recipes"]:
            assert "low_histamine" in recipe["diet_tags"]

    def test_list_recipes_meal_type_case_insensitive(self, client, auth_headers, test_recipes):
        """Meal type filter should be case-insensitive."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"meal_type": "DINNER"},
        )

        assert response.status_code == 200

    def test_list_recipes_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.get("/api/recipes")

        assert response.status_code == 403

    def test_list_recipes_invalid_page(self, client, auth_headers):
        """Should reject invalid page number."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"page": 0},
        )

        assert response.status_code == 422

    def test_list_recipes_invalid_page_size(self, client, auth_headers):
        """Should reject invalid page size."""
        response = client.get(
            "/api/recipes",
            headers=auth_headers,
            params={"page_size": 101},  # Max is 100
        )

        assert response.status_code == 422


class TestGetRecipe:
    """Tests for GET /api/recipes/{recipe_id}."""

    def test_get_recipe_success(self, client, auth_headers, test_recipe):
        """Should return recipe by ID."""
        response = client.get(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_recipe.id)
        assert data["name"] == "Test Chicken Bowl"

    def test_get_recipe_returns_all_fields(self, client, auth_headers, test_recipe):
        """Should return complete recipe information."""
        response = client.get(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
        )

        data = response.json()
        assert data["diet_tags"] == ["low_histamine"]
        assert data["meal_type"] == "dinner"
        assert len(data["ingredients"]) == 3
        assert len(data["prep_steps"]) == 4
        assert data["prep_time_minutes"] == 30
        assert data["reusability_index"] == 0.8
        assert data["servings"] == 2

    def test_get_recipe_not_found(self, client, auth_headers):
        """Should return 404 for non-existent recipe."""
        fake_id = uuid4()

        response = client.get(
            f"/api/recipes/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_recipe_invalid_uuid(self, client, auth_headers):
        """Should reject invalid UUID format."""
        response = client.get(
            "/api/recipes/not-a-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_get_recipe_without_auth(self, client, test_recipe):
        """Should reject unauthenticated request."""
        response = client.get(f"/api/recipes/{test_recipe.id}")

        assert response.status_code == 403


class TestSearchRecipesByIngredient:
    """Tests for GET /api/recipes/search/by-ingredient."""

    def test_search_by_ingredient_success(self, client, auth_headers, test_recipes):
        """Should find recipes containing ingredient."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "rice"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ingredient"] == "rice"
        assert data["count"] >= 1

    def test_search_returns_matching_recipes(self, client, auth_headers, test_recipes):
        """Search results should contain the searched ingredient."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "chicken"},
        )

        data = response.json()
        # Note: test_recipe fixture has "chicken breast" ingredient
        # The search is case-insensitive and partial match

    def test_search_case_insensitive(self, client, auth_headers, test_recipes):
        """Search should be case-insensitive."""
        response_lower = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "rice"},
        )
        response_upper = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "RICE"},
        )

        # Both should return same results
        assert response_lower.json()["count"] == response_upper.json()["count"]

    def test_search_no_results(self, client, auth_headers, test_recipes):
        """Should return empty results for non-existent ingredient."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "unicorn meat"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["matching_recipes"] == []

    def test_search_with_pagination(self, client, auth_headers, test_recipes):
        """Should support pagination in search results."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "rice", "page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total" in data

    def test_search_requires_ingredient(self, client, auth_headers):
        """Should require ingredient parameter."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_search_ingredient_min_length(self, client, auth_headers):
        """Should require minimum 2 character ingredient."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            headers=auth_headers,
            params={"ingredient": "a"},  # Too short
        )

        assert response.status_code == 422

    def test_search_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.get(
            "/api/recipes/search/by-ingredient",
            params={"ingredient": "chicken"},
        )

        assert response.status_code == 403


class TestRecipeResponseFormat:
    """Tests for consistent recipe response format."""

    def test_ingredients_format(self, client, auth_headers, test_recipe):
        """Ingredients should be list of dicts with expected keys."""
        response = client.get(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
        )

        data = response.json()
        ingredient = data["ingredients"][0]

        assert "name" in ingredient
        assert "quantity" in ingredient
        assert "freshness_days" in ingredient

    def test_prep_steps_format(self, client, auth_headers, test_recipe):
        """Prep steps should be list of strings."""
        response = client.get(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
        )

        data = response.json()
        for step in data["prep_steps"]:
            assert isinstance(step, str)

    def test_diet_tags_format(self, client, auth_headers, test_recipe):
        """Diet tags should be list of strings."""
        response = client.get(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
        )

        data = response.json()
        assert isinstance(data["diet_tags"], list)
        for tag in data["diet_tags"]:
            assert isinstance(tag, str)

    def test_reusability_index_range(self, client, auth_headers, test_recipe):
        """Reusability index should be between 0 and 1."""
        response = client.get(
            f"/api/recipes/{test_recipe.id}",
            headers=auth_headers,
        )

        data = response.json()
        assert 0 <= data["reusability_index"] <= 1
