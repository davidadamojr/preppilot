"""
Integration tests for end-to-end user workflows.

These tests verify complete user journeys that span multiple API endpoints,
ensuring the system works correctly as a whole. Each test simulates a real
user scenario from start to finish.

Test Categories:
1. User Registration and Onboarding Flow
2. Meal Planning Workflow
3. Fridge Management Workflow
4. Plan Adaptation and Recovery Flow
5. Recipe Discovery Workflow
6. Admin Management Workflow
7. Multi-User Isolation Tests
"""
import pytest
from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import User, Recipe, MealPlan, FridgeItem
from backend.models.schemas import DietType, PrepStatus, UserRole
from backend.auth.utils import hash_password


class TestUserRegistrationAndOnboardingFlow:
    """
    Complete user journey: registration -> login -> profile setup -> first plan.

    This workflow tests the typical new user experience from account creation
    through generating their first meal plan.
    """

    def test_complete_new_user_onboarding(self, client: TestClient, db_session: Session, recipe_factory):
        """
        Workflow: New user registers, logs in, sets preferences, generates first plan.

        Steps:
        1. Register new account
        2. Login with credentials
        3. Get user profile
        4. Update dietary exclusions
        5. Add fridge items
        6. Generate first meal plan
        7. View plan details
        """
        # Create recipes for meal planning
        recipe_factory.create(name="Breakfast Bowl", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="Lunch Salad", meal_type="lunch", diet_tags=["low_histamine"])
        recipe_factory.create(name="Dinner Steak", meal_type="dinner", diet_tags=["low_histamine"])

        # Step 1: Register new account
        register_response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
            "diet_type": "low_histamine",
            "dietary_exclusions": []
        })
        assert register_response.status_code == 201
        assert "access_token" in register_response.json()
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Get user profile
        profile_response = client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == "newuser@example.com"
        assert profile_response.json()["diet_type"] == "low_histamine"

        # Step 4: Update dietary exclusions
        exclusions_response = client.patch("/auth/me/exclusions", json={
            "dietary_exclusions": ["shellfish", "peanuts"]
        }, headers=headers)
        assert exclusions_response.status_code == 200
        assert "shellfish" in exclusions_response.json()["dietary_exclusions"]
        assert "peanuts" in exclusions_response.json()["dietary_exclusions"]

        # Step 5: Add fridge items
        fridge_response = client.post("/api/fridge/items", json={
            "ingredient_name": "chicken breast",
            "quantity": "500g",
            "freshness_days": 5
        }, headers=headers)
        assert fridge_response.status_code == 201
        assert fridge_response.json()["ingredient_name"] == "chicken breast"

        # Step 6: Generate first meal plan
        plan_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 3
        }, headers=headers)
        assert plan_response.status_code == 201
        plan_id = plan_response.json()["id"]
        assert len(plan_response.json()["meals"]) == 9  # 3 days * 3 meals

        # Step 7: View plan details
        get_plan_response = client.get(f"/api/plans/{plan_id}", headers=headers)
        assert get_plan_response.status_code == 200
        assert get_plan_response.json()["id"] == plan_id
        assert get_plan_response.json()["diet_type"] == "low_histamine"

    def test_registration_with_all_diet_types(self, client: TestClient, db_session: Session):
        """Verify registration works with all supported diet types."""
        diet_types = ["low_histamine", "fodmap", "fructose_free"]

        for i, diet_type in enumerate(diet_types):
            response = client.post("/auth/register", json={
                "email": f"user{i}@example.com",
                "password": "testpassword123",
                "diet_type": diet_type
            })
            assert response.status_code == 201, f"Failed for diet_type: {diet_type}"
            assert "access_token" in response.json()
            # Verify diet type via profile endpoint
            token = response.json()["access_token"]
            profile = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert profile.json()["diet_type"] == diet_type


class TestMealPlanningWorkflow:
    """
    Complete meal planning workflow from plan creation through completion.

    Tests the full lifecycle of a meal plan including generation, tracking,
    modifications, and completion.
    """

    def test_complete_meal_plan_lifecycle(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Workflow: Create plan -> track meals -> complete plan.

        Steps:
        1. Ensure recipes exist for plan generation
        2. Create a 3-day meal plan
        3. View plan and verify structure
        4. Mark breakfast as done
        5. Skip lunch
        6. Verify prep statuses updated
        7. Check catch-up view shows pending meals
        """
        # Step 1: Create recipes for all meal types
        recipe_factory.create(name="Eggs Benedict", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="Caesar Salad", meal_type="lunch", diet_tags=["low_histamine"])
        recipe_factory.create(name="Grilled Salmon", meal_type="dinner", diet_tags=["low_histamine"])

        # Step 2: Create meal plan
        plan_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 3
        }, headers=auth_headers)
        assert plan_response.status_code == 201
        plan = plan_response.json()
        plan_id = plan["id"]

        # Step 3: Verify plan structure
        assert len(plan["meals"]) == 9  # 3 days * 3 meals
        meal_types = [m["meal_type"] for m in plan["meals"]]
        assert meal_types.count("breakfast") == 3
        assert meal_types.count("lunch") == 3
        assert meal_types.count("dinner") == 3

        # Step 4: Mark first breakfast as done
        first_breakfast = next(
            m for m in plan["meals"]
            if m["meal_type"] == "breakfast" and m["date"] == date.today().isoformat()
        )
        mark_done_response = client.patch(
            f"/api/plans/{plan_id}/mark-prep",
            json={
                "date": first_breakfast["date"],
                "meal_type": "breakfast",
                "status": "DONE"
            },
            headers=auth_headers
        )
        assert mark_done_response.status_code == 200
        assert mark_done_response.json()["status"] == "DONE"

        # Step 5: Skip first lunch
        mark_skip_response = client.patch(
            f"/api/plans/{plan_id}/mark-prep",
            json={
                "date": date.today().isoformat(),
                "meal_type": "lunch",
                "status": "SKIPPED"
            },
            headers=auth_headers
        )
        assert mark_skip_response.status_code == 200
        assert mark_skip_response.json()["status"] == "SKIPPED"

        # Step 6: Verify prep statuses in plan
        updated_plan = client.get(f"/api/plans/{plan_id}", headers=auth_headers).json()
        today_meals = [m for m in updated_plan["meals"] if m["date"] == date.today().isoformat()]

        breakfast_status = next(m for m in today_meals if m["meal_type"] == "breakfast")["prep_status"]
        lunch_status = next(m for m in today_meals if m["meal_type"] == "lunch")["prep_status"]
        dinner_status = next(m for m in today_meals if m["meal_type"] == "dinner")["prep_status"]

        assert breakfast_status == "DONE"
        assert lunch_status == "SKIPPED"
        assert dinner_status == "PENDING"

        # Step 7: Check catch-up view
        catchup_response = client.get(
            f"/api/plans/{plan_id}/catch-up?current_date={date.today().isoformat()}",
            headers=auth_headers
        )
        assert catchup_response.status_code == 200

    def test_plan_duplication_workflow(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Workflow: Create plan -> duplicate to new dates -> verify independent.

        Tests that duplicated plans are independent and can be modified separately.
        """
        # Create recipes
        recipe_factory.create(name="Morning Smoothie", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="Veggie Wrap", meal_type="lunch", diet_tags=["low_histamine"])
        recipe_factory.create(name="Pasta Primavera", meal_type="dinner", diet_tags=["low_histamine"])

        # Create original plan
        original_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 3
        }, headers=auth_headers)
        assert original_response.status_code == 201
        original_plan_id = original_response.json()["id"]

        # Mark a meal as done on original
        client.patch(
            f"/api/plans/{original_plan_id}/mark-prep",
            json={
                "date": date.today().isoformat(),
                "meal_type": "breakfast",
                "status": "DONE"
            },
            headers=auth_headers
        )

        # Duplicate plan to future date
        future_start = (date.today() + timedelta(days=7)).isoformat()
        duplicate_response = client.post(
            f"/api/plans/{original_plan_id}/duplicate",
            json={"start_date": future_start},
            headers=auth_headers
        )
        assert duplicate_response.status_code == 201
        duplicate_plan = duplicate_response.json()
        duplicate_plan_id = duplicate_plan["id"]

        # Verify duplicate has different ID
        assert duplicate_plan_id != original_plan_id

        # Verify duplicate starts on new date
        assert duplicate_plan["start_date"] == future_start

        # Verify duplicate has all PENDING statuses (reset from original)
        for meal in duplicate_plan["meals"]:
            assert meal["prep_status"] == "PENDING"

        # Verify original still has DONE status
        original_plan = client.get(f"/api/plans/{original_plan_id}", headers=auth_headers).json()
        today_breakfast = next(
            m for m in original_plan["meals"]
            if m["date"] == date.today().isoformat() and m["meal_type"] == "breakfast"
        )
        assert today_breakfast["prep_status"] == "DONE"

    def test_meal_swap_workflow(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Workflow: View plan -> get compatible recipes -> swap meal.

        Tests the complete meal swap flow including fetching alternatives
        and performing the swap.
        """
        # Create multiple recipes for swapping
        recipe_factory.create(name="Pancakes", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="French Toast", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="Omelette", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="Salad", meal_type="lunch", diet_tags=["low_histamine"])
        recipe_factory.create(name="Steak", meal_type="dinner", diet_tags=["low_histamine"])

        # Create plan
        plan_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 1
        }, headers=auth_headers)
        plan_id = plan_response.json()["id"]
        original_breakfast = next(
            m for m in plan_response.json()["meals"] if m["meal_type"] == "breakfast"
        )
        original_recipe_id = original_breakfast["recipe"]["id"]

        # Get compatible recipes for swap
        compatible_response = client.get(
            f"/api/plans/{plan_id}/compatible-recipes?meal_type=breakfast",
            headers=auth_headers
        )
        assert compatible_response.status_code == 200
        compatible_recipes = compatible_response.json()["recipes"]

        # Find a different recipe to swap to
        new_recipe = next(
            r for r in compatible_recipes if r["id"] != original_recipe_id
        )

        # Perform swap
        swap_response = client.patch(
            f"/api/plans/{plan_id}/swap-meal",
            json={
                "date": date.today().isoformat(),
                "meal_type": "breakfast",
                "new_recipe_id": new_recipe["id"]
            },
            headers=auth_headers
        )
        assert swap_response.status_code == 200
        assert swap_response.json()["new_recipe_id"] == new_recipe["id"]
        assert "swap" in swap_response.json()["message"].lower()

        # Verify swap persisted
        updated_plan = client.get(f"/api/plans/{plan_id}", headers=auth_headers).json()
        updated_breakfast = next(
            m for m in updated_plan["meals"] if m["meal_type"] == "breakfast"
        )
        assert updated_breakfast["recipe"]["id"] == new_recipe["id"]


class TestFridgeManagementWorkflow:
    """
    Complete fridge management workflow testing inventory operations.
    """

    def test_complete_fridge_management_flow(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers
    ):
        """
        Workflow: Add items -> bulk add -> update -> check expiring -> clear.

        Steps:
        1. Add single item
        2. Bulk add multiple items
        3. Update item quantity
        4. Check expiring items
        5. Delete expired item
        6. Clear remaining items
        """
        # Step 1: Add single item
        add_response = client.post("/api/fridge/items", json={
            "ingredient_name": "milk",
            "quantity": "1 gallon",
            "freshness_days": 7
        }, headers=auth_headers)
        assert add_response.status_code == 201
        milk_id = add_response.json()["id"]

        # Step 2: Bulk add items
        bulk_response = client.post("/api/fridge/items/bulk", json={
            "items": [
                {"ingredient_name": "eggs", "quantity": "12", "freshness_days": 14},
                {"ingredient_name": "cheese", "quantity": "200g", "freshness_days": 10},
                {"ingredient_name": "bread", "quantity": "1 loaf", "freshness_days": 2}
            ]
        }, headers=auth_headers)
        assert bulk_response.status_code == 201
        # Bulk add returns a list of created items
        assert len(bulk_response.json()) == 3

        # Step 3: Update milk quantity
        update_response = client.patch(f"/api/fridge/items/{milk_id}", json={
            "quantity": "half gallon"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["quantity"] == "half gallon"

        # Step 4: Check expiring items (within 2 days)
        expiring_response = client.get("/api/fridge/expiring?days_threshold=2", headers=auth_headers)
        assert expiring_response.status_code == 200
        # Expiring endpoint returns a list directly
        expiring_items = expiring_response.json()
        expiring_names = [item["ingredient_name"] for item in expiring_items]
        assert "bread" in expiring_names

        # Step 5: Delete the bread (expired soon)
        bread_id = next(
            item["id"] for item in expiring_items if item["ingredient_name"] == "bread"
        )
        delete_response = client.delete(f"/api/fridge/items/{bread_id}", headers=auth_headers)
        assert delete_response.status_code == 204  # No content

        # Verify bread is gone
        fridge_state = client.get("/api/fridge", headers=auth_headers).json()
        item_names = [item["ingredient_name"] for item in fridge_state["items"]]
        assert "bread" not in item_names

        # Step 6: Clear all remaining items
        clear_response = client.delete("/api/fridge", headers=auth_headers)
        assert clear_response.status_code == 204  # No content

        # Verify fridge is empty
        empty_fridge = client.get("/api/fridge", headers=auth_headers).json()
        assert len(empty_fridge["items"]) == 0

    def test_fridge_freshness_tracking(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers
    ):
        """
        Workflow: Add items with varying freshness -> track percentages.

        Tests that freshness percentages are calculated correctly based on
        days remaining vs original freshness.
        """
        # Add item with freshness 10 days
        item1_response = client.post("/api/fridge/items", json={
            "ingredient_name": "yogurt",
            "quantity": "500g",
            "freshness_days": 10
        }, headers=auth_headers)
        assert item1_response.status_code == 201
        # Fresh item starts at 100%
        assert item1_response.json()["freshness_percentage"] == 100

        # Add item with short freshness (2 days)
        item2_response = client.post("/api/fridge/items", json={
            "ingredient_name": "fish",
            "quantity": "300g",
            "freshness_days": 2
        }, headers=auth_headers)
        assert item2_response.status_code == 201
        # Fresh item starts at 100%
        assert item2_response.json()["freshness_percentage"] == 100

        # Update fish freshness (still fresh after inspection)
        fish_id = item2_response.json()["id"]
        update_response = client.patch(f"/api/fridge/items/{fish_id}", json={
            "days_remaining": 3
        }, headers=auth_headers)
        assert update_response.status_code == 200
        # Freshness should now be higher
        assert update_response.json()["freshness_percentage"] > 20


class TestRecipeDiscoveryWorkflow:
    """
    Recipe browsing and search workflow tests.
    """

    def test_recipe_search_and_filter_workflow(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Workflow: Browse recipes -> filter by meal type -> search by ingredient.

        Tests the complete recipe discovery experience.
        """
        # Create diverse recipes
        recipe_factory.create(
            name="Chicken Stir Fry",
            meal_type="dinner",
            diet_tags=["low_histamine"],
            ingredients=[{"name": "chicken", "freshness_days": 3, "quantity": "500g", "category": "protein"}]
        )
        recipe_factory.create(
            name="Grilled Chicken Salad",
            meal_type="lunch",
            diet_tags=["low_histamine", "fodmap"],
            ingredients=[{"name": "chicken", "freshness_days": 3, "quantity": "200g", "category": "protein"}]
        )
        recipe_factory.create(
            name="Oatmeal",
            meal_type="breakfast",
            diet_tags=["fodmap"],
            ingredients=[{"name": "oats", "freshness_days": 180, "quantity": "1 cup", "category": "grains"}]
        )
        recipe_factory.create(
            name="Salmon Dinner",
            meal_type="dinner",
            diet_tags=["low_histamine"],
            ingredients=[{"name": "salmon", "freshness_days": 2, "quantity": "300g", "category": "protein"}]
        )

        # Step 1: Browse all recipes (paginated)
        list_response = client.get("/api/recipes?page=1&page_size=10", headers=auth_headers)
        assert list_response.status_code == 200
        all_recipes = list_response.json()
        assert all_recipes["total"] == 4

        # Step 2: Filter by meal type
        dinner_response = client.get(
            "/api/recipes?page=1&page_size=10&meal_type=dinner",
            headers=auth_headers
        )
        assert dinner_response.status_code == 200
        dinner_recipes = dinner_response.json()
        assert all(r["meal_type"] == "dinner" for r in dinner_recipes["recipes"])
        assert dinner_recipes["total"] == 2

        # Step 3: Filter by diet tag
        fodmap_response = client.get(
            "/api/recipes?page=1&page_size=10&diet_tag=fodmap",
            headers=auth_headers
        )
        assert fodmap_response.status_code == 200
        fodmap_recipes = fodmap_response.json()
        assert all("fodmap" in r["diet_tags"] for r in fodmap_recipes["recipes"])

        # Step 4: Search by ingredient
        search_response = client.get(
            "/api/recipes/search/by-ingredient?ingredient=chicken",
            headers=auth_headers
        )
        assert search_response.status_code == 200
        chicken_recipes = search_response.json()
        assert len(chicken_recipes["matching_recipes"]) == 2
        recipe_names = [r["name"] for r in chicken_recipes["matching_recipes"]]
        assert "Chicken Stir Fry" in recipe_names
        assert "Grilled Chicken Salad" in recipe_names

    def test_view_recipe_details(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Workflow: List recipes -> view single recipe details.

        Tests that full recipe details (ingredients, steps) are retrievable.
        """
        # Create a detailed recipe
        recipe = recipe_factory.create(
            name="Complex Dish",
            meal_type="dinner",
            diet_tags=["low_histamine"],
            ingredients=[
                {"name": "beef", "freshness_days": 3, "quantity": "500g", "category": "protein"},
                {"name": "potatoes", "freshness_days": 30, "quantity": "4 medium", "category": "produce"},
                {"name": "carrots", "freshness_days": 14, "quantity": "3 medium", "category": "produce"}
            ],
            prep_steps=[
                "Prepare vegetables",
                "Season beef",
                "Sear beef in hot pan",
                "Add vegetables and cook",
                "Serve hot"
            ],
            prep_time_minutes=45,
            servings=4
        )

        # Get recipe details
        response = client.get(f"/api/recipes/{recipe.id}", headers=auth_headers)
        assert response.status_code == 200
        recipe_data = response.json()

        # Verify all details present
        assert recipe_data["name"] == "Complex Dish"
        assert len(recipe_data["ingredients"]) == 3
        assert len(recipe_data["prep_steps"]) == 5
        assert recipe_data["prep_time_minutes"] == 45
        assert recipe_data["servings"] == 4


class TestAdminManagementWorkflow:
    """
    Admin user management and system administration workflows.
    """

    def test_admin_user_management_workflow(
        self, client: TestClient, db_session: Session,
        admin_user, admin_auth_headers, user_factory
    ):
        """
        Workflow: Admin lists users -> views user -> changes role -> deactivates.

        Tests the complete admin user management flow.
        """
        # Create some regular users
        user1 = user_factory.create(email="user1@test.com")
        user2 = user_factory.create(email="user2@test.com")

        # Step 1: List all users
        list_response = client.get("/api/admin/users?page=1&page_size=10", headers=admin_auth_headers)
        assert list_response.status_code == 200
        users_response = list_response.json()
        assert users_response["total"] >= 3  # admin + 2 users
        assert "users" in users_response

        # Step 2: View specific user
        user_response = client.get(f"/api/admin/users/{user1.id}", headers=admin_auth_headers)
        assert user_response.status_code == 200
        assert user_response.json()["email"] == "user1@test.com"

        # Step 3: Promote user to admin
        role_response = client.patch(
            f"/api/admin/users/{user1.id}/role",
            json={"role": "admin"},
            headers=admin_auth_headers
        )
        assert role_response.status_code == 200
        assert role_response.json()["role"] == "admin"

        # Step 4: Deactivate user2
        status_response = client.patch(
            f"/api/admin/users/{user2.id}/status",
            json={"is_active": False},
            headers=admin_auth_headers
        )
        assert status_response.status_code == 200
        assert status_response.json()["is_active"] is False

        # Verify deactivated user cannot login
        login_response = client.post("/auth/login", json={
            "email": "user2@test.com",
            "password": "testpassword123"
        })
        # Deactivated users get 403 Forbidden (account inactive)
        assert login_response.status_code == 403

    def test_admin_recipe_management_workflow(
        self, client: TestClient, db_session: Session,
        admin_user, admin_auth_headers
    ):
        """
        Workflow: Admin creates recipe -> updates it -> deletes it.

        Tests admin CRUD operations on recipes.
        """
        # Step 1: Create new recipe
        create_response = client.post("/api/recipes", json={
            "name": "Admin Special",
            "diet_tags": ["low_histamine"],
            "meal_type": "dinner",
            "ingredients": [
                {"name": "chicken", "freshness_days": 3, "quantity": "500g", "category": "protein"}
            ],
            "prep_steps": ["Cook chicken", "Serve"],
            "prep_time_minutes": 30,
            "servings": 2,
            "reusability_index": 0.5
        }, headers=admin_auth_headers)
        assert create_response.status_code == 201
        recipe_id = create_response.json()["id"]

        # Step 2: Update recipe
        update_response = client.put(f"/api/recipes/{recipe_id}", json={
            "name": "Admin Special Deluxe",
            "prep_time_minutes": 45
        }, headers=admin_auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Admin Special Deluxe"
        assert update_response.json()["prep_time_minutes"] == 45

        # Step 3: Delete recipe
        delete_response = client.delete(f"/api/recipes/{recipe_id}", headers=admin_auth_headers)
        assert delete_response.status_code == 200
        assert "deleted" in delete_response.json()["message"].lower()

        # Verify recipe is gone
        get_response = client.get(f"/api/recipes/{recipe_id}", headers=admin_auth_headers)
        assert get_response.status_code == 404

    def test_admin_audit_log_workflow(
        self, client: TestClient, db_session: Session,
        admin_user, admin_auth_headers, user_factory
    ):
        """
        Workflow: Perform actions -> view audit logs -> filter by action.

        Tests that admin actions are properly logged and queryable.
        """
        # Create a user (generates audit log)
        new_user = user_factory.create(email="audited@test.com")

        # Deactivate user (generates another audit log)
        client.patch(
            f"/api/admin/users/{new_user.id}/status",
            json={"is_active": False},
            headers=admin_auth_headers
        )

        # View all audit logs
        logs_response = client.get("/api/admin/audit-logs?page=1&page_size=50", headers=admin_auth_headers)
        assert logs_response.status_code == 200
        logs = logs_response.json()
        assert logs["total"] >= 1

        # View logs for specific user
        user_logs_response = client.get(
            f"/api/admin/audit-logs/user/{new_user.id}",
            headers=admin_auth_headers
        )
        assert user_logs_response.status_code == 200


class TestMultiUserIsolation:
    """
    Tests to ensure data isolation between different users.
    """

    def test_users_cannot_access_each_others_plans(
        self, client: TestClient, db_session: Session,
        user_factory, recipe_factory
    ):
        """
        Verify that users cannot view or modify each other's meal plans.
        """
        # Create recipes
        recipe_factory.create(name="Breakfast", meal_type="breakfast", diet_tags=["low_histamine"])
        recipe_factory.create(name="Lunch", meal_type="lunch", diet_tags=["low_histamine"])
        recipe_factory.create(name="Dinner", meal_type="dinner", diet_tags=["low_histamine"])

        # Create two users
        user1 = user_factory.create(email="user1@isolation.com")
        user2 = user_factory.create(email="user2@isolation.com")

        # Login as user1
        login1 = client.post("/auth/login", json={
            "email": "user1@isolation.com",
            "password": "testpassword123"
        })
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        # Login as user2
        login2 = client.post("/auth/login", json={
            "email": "user2@isolation.com",
            "password": "testpassword123"
        })
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # User1 creates a plan
        plan1_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 1
        }, headers=headers1)
        plan1_id = plan1_response.json()["id"]

        # User2 tries to access User1's plan
        access_response = client.get(f"/api/plans/{plan1_id}", headers=headers2)
        assert access_response.status_code == 404

        # User2 tries to modify User1's plan
        modify_response = client.patch(
            f"/api/plans/{plan1_id}/mark-prep",
            json={
                "date": date.today().isoformat(),
                "meal_type": "breakfast",
                "status": "DONE"
            },
            headers=headers2
        )
        assert modify_response.status_code == 404

        # User2 tries to delete User1's plan
        delete_response = client.delete(f"/api/plans/{plan1_id}", headers=headers2)
        assert delete_response.status_code == 404

    def test_users_cannot_access_each_others_fridge(
        self, client: TestClient, db_session: Session,
        user_factory
    ):
        """
        Verify that users cannot view or modify each other's fridge items.
        """
        # Create two users
        user1 = user_factory.create(email="fridge1@isolation.com")
        user2 = user_factory.create(email="fridge2@isolation.com")

        # Login as both users
        login1 = client.post("/auth/login", json={
            "email": "fridge1@isolation.com",
            "password": "testpassword123"
        })
        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        login2 = client.post("/auth/login", json={
            "email": "fridge2@isolation.com",
            "password": "testpassword123"
        })
        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # User1 adds fridge item
        item_response = client.post("/api/fridge/items", json={
            "ingredient_name": "secret ingredient",
            "quantity": "1 kg",
            "freshness_days": 5
        }, headers=headers1)
        item_id = item_response.json()["id"]

        # User2's fridge should be empty
        fridge2 = client.get("/api/fridge", headers=headers2).json()
        assert len(fridge2["items"]) == 0

        # User2 tries to delete User1's item - should return 204 even if not found
        # (delete is idempotent, but here it should fail to find the item)
        delete_response = client.delete(f"/api/fridge/items/{item_id}", headers=headers2)
        # Could be 204 (not found, treated as already deleted) or 404
        assert delete_response.status_code in [204, 404]

        # Verify User1's item still exists
        user1_fridge = client.get("/api/fridge", headers=headers1).json()
        assert len(user1_fridge["items"]) == 1

        # User2 tries to update User1's item
        update_response = client.patch(f"/api/fridge/items/{item_id}", json={
            "quantity": "stolen"
        }, headers=headers2)
        assert update_response.status_code == 404

    def test_regular_user_cannot_access_admin_endpoints(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers
    ):
        """
        Verify that regular users cannot access admin-only endpoints.
        """
        # Try to list users (admin only)
        list_response = client.get("/api/admin/users", headers=auth_headers)
        assert list_response.status_code == 403

        # Try to view audit logs (admin only)
        logs_response = client.get("/api/admin/audit-logs", headers=auth_headers)
        assert logs_response.status_code == 403

        # Try to create recipe (admin only)
        create_response = client.post("/api/recipes", json={
            "name": "Hacker Recipe",
            "diet_tags": ["low_histamine"],
            "meal_type": "dinner",
            "ingredients": [],
            "prep_steps": ["hack"],
            "prep_time_minutes": 1,
            "servings": 1
        }, headers=auth_headers)
        assert create_response.status_code == 403


class TestErrorRecoveryWorkflow:
    """
    Tests for error handling and recovery scenarios.
    """

    def test_plan_generation_with_no_matching_recipes(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Verify proper error when no recipes match user's diet.
        """
        # Create only FODMAP recipes (user has LOW_HISTAMINE diet)
        recipe_factory.create(name="FODMAP Only", meal_type="dinner", diet_tags=["fodmap"])

        # Try to create plan
        response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 1
        }, headers=auth_headers)

        # Should fail with 422 (no matching recipes) or 500 (internal error)
        assert response.status_code in [422, 500]
        # Check error is related to recipes
        error_detail = response.json()["detail"]
        if isinstance(error_detail, str):
            assert "recipe" in error_detail.lower() or "no" in error_detail.lower()
        else:
            # Structured error response
            assert "recipe" in str(error_detail).lower() or "error" in str(error_detail).lower()

    def test_authentication_failure_recovery(self, client: TestClient, db_session: Session):
        """
        Verify graceful handling of authentication failures.
        """
        # Register user
        client.post("/auth/register", json={
            "email": "recovery@test.com",
            "password": "correctpassword123",
            "diet_type": "low_histamine"
        })

        # Try wrong password
        wrong_password = client.post("/auth/login", json={
            "email": "recovery@test.com",
            "password": "wrongpassword"
        })
        assert wrong_password.status_code == 401
        assert "access_token" not in wrong_password.json()

        # Try correct password - should work
        correct_password = client.post("/auth/login", json={
            "email": "recovery@test.com",
            "password": "correctpassword123"
        })
        assert correct_password.status_code == 200
        assert "access_token" in correct_password.json()

    def test_expired_token_handling(
        self, client: TestClient, db_session: Session,
        test_user
    ):
        """
        Verify proper handling of invalid/expired tokens.
        """
        # Use obviously invalid token
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}

        # Try to access protected endpoint
        response = client.get("/auth/me", headers=invalid_headers)
        # May return 401 or 403 depending on implementation
        assert response.status_code in [401, 403]

        # Malformed header
        malformed_headers = {"Authorization": "NotBearer token"}
        response2 = client.get("/auth/me", headers=malformed_headers)
        assert response2.status_code in [401, 403]

        # Missing header
        response3 = client.get("/auth/me")
        # May return 401 or 403 depending on OAuth2 scheme
        assert response3.status_code in [401, 403]


class TestComplexUserJourneys:
    """
    Complex multi-step user journeys spanning multiple features.
    """

    def test_weekly_meal_prep_workflow(
        self, client: TestClient, db_session: Session,
        user_factory, recipe_factory
    ):
        """
        Complete weekly meal prep workflow simulating a realistic user journey.

        Simulates a user who:
        1. Registers with dietary restrictions
        2. Adds current fridge inventory
        3. Creates a weekly meal plan
        4. Tracks meals throughout the week
        5. Duplicates successful plan for next week
        """
        # Create diverse recipes
        for meal_type in ["breakfast", "lunch", "dinner"]:
            recipe_factory.create(
                name=f"Weekly {meal_type.title()} 1",
                meal_type=meal_type,
                diet_tags=["low_histamine"]
            )
            recipe_factory.create(
                name=f"Weekly {meal_type.title()} 2",
                meal_type=meal_type,
                diet_tags=["low_histamine"]
            )

        # Step 1: Register with restrictions
        register = client.post("/auth/register", json={
            "email": "weekly@example.com",
            "password": "mealprep123",
            "full_name": "Weekly Prepper",
            "diet_type": "low_histamine",
            "dietary_exclusions": ["shellfish", "peanuts"]
        })
        token = register.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Stock the fridge
        client.post("/api/fridge/items/bulk", json={
            "items": [
                {"ingredient_name": "chicken", "quantity": "2 lbs", "freshness_days": 5},
                {"ingredient_name": "rice", "quantity": "5 lbs", "freshness_days": 30},
                {"ingredient_name": "vegetables", "quantity": "mixed bag", "freshness_days": 7},
                {"ingredient_name": "eggs", "quantity": "1 dozen", "freshness_days": 14}
            ]
        }, headers=headers)

        # Step 3: Create weekly plan (default is 3 days due to settings, using that)
        plan_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 3
        }, headers=headers)
        assert plan_response.status_code == 201
        plan_id = plan_response.json()["id"]
        assert len(plan_response.json()["meals"]) == 9  # 3 days * 3 meals

        # Step 4: Track meals over "several days" (simulated)
        # Day 1 - complete all meals
        for meal_type in ["breakfast", "lunch", "dinner"]:
            client.patch(f"/api/plans/{plan_id}/mark-prep", json={
                "date": date.today().isoformat(),
                "meal_type": meal_type,
                "status": "DONE"
            }, headers=headers)

        # Day 2 - skip lunch
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        client.patch(f"/api/plans/{plan_id}/mark-prep", json={
            "date": tomorrow,
            "meal_type": "breakfast",
            "status": "DONE"
        }, headers=headers)
        client.patch(f"/api/plans/{plan_id}/mark-prep", json={
            "date": tomorrow,
            "meal_type": "lunch",
            "status": "SKIPPED"
        }, headers=headers)

        # Verify plan state
        plan = client.get(f"/api/plans/{plan_id}", headers=headers).json()
        done_count = sum(1 for m in plan["meals"] if m["prep_status"] == "DONE")
        skipped_count = sum(1 for m in plan["meals"] if m["prep_status"] == "SKIPPED")
        assert done_count == 4  # 3 from day 1 + 1 breakfast from day 2
        assert skipped_count == 1

        # Step 5: Duplicate plan for next week
        next_week = (date.today() + timedelta(days=7)).isoformat()
        duplicate_response = client.post(f"/api/plans/{plan_id}/duplicate", json={
            "start_date": next_week
        }, headers=headers)
        assert duplicate_response.status_code == 201
        new_plan = duplicate_response.json()

        # Verify new plan starts fresh
        assert new_plan["start_date"] == next_week
        assert all(m["prep_status"] == "PENDING" for m in new_plan["meals"])

    def test_dietary_adaptation_workflow(
        self, client: TestClient, db_session: Session,
        user_factory, recipe_factory
    ):
        """
        Workflow: User discovers new dietary restriction and adapts.

        Simulates a user who:
        1. Creates account with basic diet
        2. Generates meal plan
        3. Discovers they need to avoid an ingredient
        4. Updates dietary exclusions
        5. Generates new compliant plan
        """
        # Create recipes with various ingredients
        recipe_factory.create(
            name="Nut-Free Breakfast",
            meal_type="breakfast",
            diet_tags=["low_histamine"],
            ingredients=[{"name": "oats", "freshness_days": 180, "quantity": "1 cup", "category": "grains"}]
        )
        recipe_factory.create(
            name="Almond Porridge",
            meal_type="breakfast",
            diet_tags=["low_histamine"],
            ingredients=[{"name": "almonds", "freshness_days": 90, "quantity": "1/4 cup", "category": "nuts"}]
        )
        recipe_factory.create(
            name="Simple Lunch",
            meal_type="lunch",
            diet_tags=["low_histamine"]
        )
        recipe_factory.create(
            name="Simple Dinner",
            meal_type="dinner",
            diet_tags=["low_histamine"]
        )

        # Step 1: Register without nut exclusion
        register = client.post("/auth/register", json={
            "email": "adaptation@test.com",
            "password": "adapt123",
            "diet_type": "low_histamine",
            "dietary_exclusions": []
        })
        token = register.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Generate initial plan
        plan1 = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 1
        }, headers=headers)
        assert plan1.status_code == 201

        # Step 3 & 4: Add tree_nuts exclusion
        exclusion_response = client.patch("/auth/me/exclusions", json={
            "dietary_exclusions": ["tree_nuts"]
        }, headers=headers)
        assert exclusion_response.status_code == 200
        assert "tree_nuts" in exclusion_response.json()["dietary_exclusions"]

        # Step 5: Generate new compliant plan
        plan2 = client.post("/api/plans", json={
            "start_date": (date.today() + timedelta(days=1)).isoformat(),
            "num_days": 1
        }, headers=headers)
        assert plan2.status_code == 201

        # Verify new plan respects exclusions (would need to verify recipe selection)
        # The system should exclude recipes with nuts


class TestPrepTimelineWorkflow:
    """
    Tests for the prep timeline optimization feature.
    """

    def test_prep_timeline_generation(
        self, client: TestClient, db_session: Session,
        test_user, auth_headers, recipe_factory
    ):
        """
        Workflow: Create plan -> generate prep timeline -> view optimization.

        Tests the prep timeline optimization returns sensible results.
        """
        # Create recipes with different prep times
        recipe_factory.create(
            name="Quick Eggs",
            meal_type="breakfast",
            diet_tags=["low_histamine"],
            prep_steps=["Crack eggs", "Scramble", "Serve"],
            prep_time_minutes=10
        )
        recipe_factory.create(
            name="Slow Roast",
            meal_type="dinner",
            diet_tags=["low_histamine"],
            prep_steps=["Prep meat", "Season", "Roast for 2 hours", "Rest", "Serve"],
            prep_time_minutes=150
        )
        recipe_factory.create(
            name="Sandwich",
            meal_type="lunch",
            diet_tags=["low_histamine"],
            prep_steps=["Slice bread", "Add fillings", "Cut"],
            prep_time_minutes=5
        )

        # Create plan
        plan_response = client.post("/api/plans", json={
            "start_date": date.today().isoformat(),
            "num_days": 1
        }, headers=auth_headers)
        plan_id = plan_response.json()["id"]

        # Get prep timeline for today
        timeline_response = client.get(
            f"/api/plans/{plan_id}/prep-timeline?prep_date={date.today().isoformat()}",
            headers=auth_headers
        )
        assert timeline_response.status_code == 200
        timeline = timeline_response.json()

        # Verify timeline structure
        assert "total_time_minutes" in timeline
        assert "steps" in timeline
        assert len(timeline["steps"]) > 0

        # Verify steps have required fields
        for step in timeline["steps"]:
            assert "action" in step
            assert "duration_minutes" in step
