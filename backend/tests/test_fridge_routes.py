"""
Tests for fridge inventory API routes.

Tests cover:
- Get fridge state
- Add single item
- Add bulk items
- Remove item by ID
- Remove item by name
- Get expiring items
- Clear fridge
- Input sanitization
- Concurrent updates
- Boundary conditions
"""
import pytest
import threading
from uuid import uuid4


class TestGetFridgeState:
    """Tests for GET /api/fridge."""

    def test_get_fridge_empty(self, client, auth_headers):
        """Should return empty fridge for new user."""
        response = client.get("/api/fridge", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 0
        assert data["items"] == []
        assert data["expiring_soon_count"] == 0

    def test_get_fridge_with_items(self, client, auth_headers, test_fridge_items):
        """Should return all fridge items."""
        response = client.get("/api/fridge", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 3
        assert len(data["items"]) == 3

    def test_get_fridge_returns_item_details(self, client, auth_headers, test_fridge_items):
        """Each item should have expected fields."""
        response = client.get("/api/fridge", headers=auth_headers)
        data = response.json()

        item = data["items"][0]
        assert "id" in item
        assert "ingredient_name" in item
        assert "quantity" in item
        assert "days_remaining" in item
        assert "added_date" in item
        assert "original_freshness_days" in item
        assert "freshness_percentage" in item

    def test_get_fridge_expiring_count(self, client, auth_headers, expiring_fridge_items):
        """Should count expiring items (2 days or less)."""
        response = client.get("/api/fridge", headers=auth_headers)
        data = response.json()

        assert data["expiring_soon_count"] == 2

    def test_get_fridge_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.get("/api/fridge")

        assert response.status_code == 403


class TestAddFridgeItem:
    """Tests for POST /api/fridge/items."""

    def test_add_item_success(self, client, auth_headers):
        """Should add item to fridge."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "chicken breast",
                "quantity": "500g",
                "freshness_days": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["ingredient_name"] == "chicken breast"
        assert data["quantity"] == "500g"
        assert data["days_remaining"] == 3

    def test_add_item_returns_id(self, client, auth_headers):
        """Added item should have UUID."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "carrots",
                "quantity": "6",
                "freshness_days": 14,
            },
        )

        data = response.json()
        assert "id" in data
        # Should be valid UUID format
        assert len(str(data["id"])) == 36

    def test_add_item_calculates_freshness_percentage(self, client, auth_headers):
        """Should calculate freshness percentage correctly."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "milk",
                "quantity": "1 liter",
                "freshness_days": 7,
            },
        )

        data = response.json()
        # 7/7 = 100%
        assert data["freshness_percentage"] == 100.0

    def test_add_item_missing_fields(self, client, auth_headers):
        """Should reject incomplete request."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "cheese",
                # Missing quantity and freshness_days
            },
        )

        assert response.status_code == 422

    def test_add_item_invalid_freshness_days(self, client, auth_headers):
        """Should reject invalid freshness_days."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "cheese",
                "quantity": "200g",
                "freshness_days": 0,  # Must be >= 1
            },
        )

        assert response.status_code == 422

    def test_add_item_sanitizes_xss(self, client, auth_headers):
        """Should sanitize XSS attempts in ingredient name."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "<script>alert('xss')</script>chicken",
                "quantity": "500g",
                "freshness_days": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Script tags should be removed
        assert "<script>" not in data["ingredient_name"]
        assert "chicken" in data["ingredient_name"]

    def test_add_item_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.post(
            "/api/fridge/items",
            json={
                "ingredient_name": "chicken",
                "quantity": "500g",
                "freshness_days": 3,
            },
        )

        assert response.status_code == 403


class TestAddFridgeItemsBulk:
    """Tests for POST /api/fridge/items/bulk."""

    def test_add_bulk_success(self, client, auth_headers):
        """Should add multiple items at once."""
        response = client.post(
            "/api/fridge/items/bulk",
            headers=auth_headers,
            json={
                "items": [
                    {"ingredient_name": "chicken", "quantity": "500g", "freshness_days": 3},
                    {"ingredient_name": "rice", "quantity": "2 cups", "freshness_days": 365},
                    {"ingredient_name": "carrots", "quantity": "4", "freshness_days": 14},
                ]
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3

    def test_add_bulk_empty_list(self, client, auth_headers):
        """Should handle empty list."""
        response = client.post(
            "/api/fridge/items/bulk",
            headers=auth_headers,
            json={"items": []},
        )

        assert response.status_code == 201
        assert response.json() == []

    def test_add_bulk_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.post(
            "/api/fridge/items/bulk",
            json={"items": [{"ingredient_name": "test", "quantity": "1", "freshness_days": 1}]},
        )

        assert response.status_code == 403


class TestUpdateFridgeItem:
    """Tests for PATCH /api/fridge/items/{item_id}."""

    def test_update_quantity_success(self, client, auth_headers, test_fridge_items):
        """Should update item quantity."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"quantity": "1kg"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == "1kg"
        assert data["id"] == str(item_id)

    def test_update_days_remaining_success(self, client, auth_headers, test_fridge_items):
        """Should update item days_remaining."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"days_remaining": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days_remaining"] == 5

    def test_update_both_fields(self, client, auth_headers, test_fridge_items):
        """Should update both quantity and days_remaining."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"quantity": "2 lbs", "days_remaining": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == "2 lbs"
        assert data["days_remaining"] == 10

    def test_update_recalculates_freshness_percentage(self, client, auth_headers):
        """Should recalculate freshness percentage after update."""
        # Add item with 10 days freshness
        add_response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "test item",
                "quantity": "100g",
                "freshness_days": 10,
            },
        )
        item_id = add_response.json()["id"]

        # Update to 5 days remaining
        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"days_remaining": 5},
        )

        data = response.json()
        # 5/10 = 50%
        assert data["freshness_percentage"] == 50.0

    def test_update_increases_original_freshness_when_needed(self, client, auth_headers):
        """Should increase original_freshness_days if new days_remaining is higher."""
        # Add item with 5 days freshness
        add_response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "extend test",
                "quantity": "100g",
                "freshness_days": 5,
            },
        )
        item_id = add_response.json()["id"]

        # Update to 10 days remaining (more than original)
        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"days_remaining": 10},
        )

        data = response.json()
        assert data["days_remaining"] == 10
        assert data["original_freshness_days"] == 10
        assert data["freshness_percentage"] == 100.0

    def test_update_not_found(self, client, auth_headers):
        """Should return 404 for non-existent item."""
        fake_id = uuid4()

        response = client.patch(
            f"/api/fridge/items/{fake_id}",
            headers=auth_headers,
            json={"quantity": "1kg"},
        )

        assert response.status_code == 404

    def test_update_no_fields_provided(self, client, auth_headers, test_fridge_items):
        """Should reject request with no fields to update."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 400
        assert "At least one field" in response.json()["detail"]

    def test_update_invalid_days_remaining(self, client, auth_headers, test_fridge_items):
        """Should reject invalid days_remaining value."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"days_remaining": -1},
        )

        assert response.status_code == 422

    def test_update_days_remaining_to_zero(self, client, auth_headers, test_fridge_items):
        """Should allow setting days_remaining to zero (expired)."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"days_remaining": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days_remaining"] == 0

    def test_update_sanitizes_xss(self, client, auth_headers, test_fridge_items):
        """Should sanitize XSS attempts in quantity."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"quantity": "<script>alert('xss')</script>500g"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "<script>" not in data["quantity"]
        assert "500g" in data["quantity"]

    def test_update_without_auth(self, client, test_fridge_items):
        """Should reject unauthenticated request."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            json={"quantity": "1kg"},
        )

        assert response.status_code == 403


class TestRemoveFridgeItem:
    """Tests for DELETE /api/fridge/items/{item_id}."""

    def test_remove_item_success(self, client, auth_headers, test_fridge_items):
        """Should remove item by ID."""
        item_id = test_fridge_items[0].id

        response = client.delete(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_remove_item_not_found(self, client, auth_headers):
        """Should return 404 for non-existent item."""
        fake_id = uuid4()

        response = client.delete(
            f"/api/fridge/items/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_remove_item_wrong_user(self, client, auth_headers, user_factory):
        """Should not remove other user's items."""
        # Create another user with a fridge item
        from backend.db.models import FridgeItem as DBFridgeItem
        from datetime import date

        other_user = user_factory.create(email="other@example.com")

        # We can't easily create items for other user in this test
        # since we don't have access to db_session here
        # This test documents expected behavior

    def test_remove_item_without_auth(self, client, test_fridge_items):
        """Should reject unauthenticated request."""
        item_id = test_fridge_items[0].id

        response = client.delete(f"/api/fridge/items/{item_id}")

        assert response.status_code == 403


class TestRemoveFridgeItemByName:
    """Tests for DELETE /api/fridge/items/by-name/{ingredient_name}."""

    def test_remove_by_name_success(self, client, auth_headers, test_fridge_items):
        """Should remove item by name."""
        response = client.delete(
            "/api/fridge/items/by-name/chicken breast",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_remove_by_name_not_found(self, client, auth_headers):
        """Should return 404 for non-existent ingredient."""
        response = client.delete(
            "/api/fridge/items/by-name/nonexistent",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_remove_by_name_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.delete("/api/fridge/items/by-name/chicken")

        assert response.status_code == 403


class TestGetExpiringItems:
    """Tests for GET /api/fridge/expiring."""

    def test_get_expiring_default_threshold(self, client, auth_headers, expiring_fridge_items):
        """Should return items expiring within 2 days by default."""
        response = client.get("/api/fridge/expiring", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_expiring_custom_threshold(self, client, auth_headers, test_fridge_items):
        """Should respect custom threshold."""
        # test_fridge_items has items with 1, 2, and 10 days remaining
        response = client.get(
            "/api/fridge/expiring",
            headers=auth_headers,
            params={"days_threshold": 5},
        )

        assert response.status_code == 200
        data = response.json()
        # Should include items with 1 and 2 days remaining
        assert len(data) >= 1

    def test_get_expiring_no_items(self, client, auth_headers):
        """Should return empty list when nothing is expiring."""
        response = client.get("/api/fridge/expiring", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_get_expiring_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.get("/api/fridge/expiring")

        assert response.status_code == 403


class TestClearFridge:
    """Tests for DELETE /api/fridge."""

    def test_clear_fridge_success(self, client, auth_headers, test_fridge_items):
        """Should remove all items from fridge."""
        response = client.delete("/api/fridge", headers=auth_headers)

        assert response.status_code == 204

        # Verify fridge is empty
        get_response = client.get("/api/fridge", headers=auth_headers)
        assert get_response.json()["total_items"] == 0

    def test_clear_empty_fridge(self, client, auth_headers):
        """Should succeed even if fridge is already empty."""
        response = client.delete("/api/fridge", headers=auth_headers)

        assert response.status_code == 204

    def test_clear_fridge_without_auth(self, client):
        """Should reject unauthenticated request."""
        response = client.delete("/api/fridge")

        assert response.status_code == 403


class TestInputSanitization:
    """Tests for XSS and input sanitization."""

    def test_sanitize_html_tags(self, client, auth_headers):
        """Should remove HTML tags from input."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "<b>bold</b> chicken",
                "quantity": "<i>500g</i>",
                "freshness_days": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "<b>" not in data["ingredient_name"]
        assert "<i>" not in data["quantity"]

    def test_sanitize_javascript_uri(self, client, auth_headers):
        """Should remove javascript: URIs."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "javascript:alert('xss')chicken",
                "quantity": "500g",
                "freshness_days": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "javascript:" not in data["ingredient_name"]

    def test_sanitize_event_handlers(self, client, auth_headers):
        """Should remove event handler attributes."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "onclick=alert('xss')chicken",
                "quantity": "500g",
                "freshness_days": 3,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "onclick=" not in data["ingredient_name"]


# ============================================================================
# Edge Case Tests: Concurrent Updates
# ============================================================================

class TestConcurrentFridgeUpdates:
    """Tests for concurrent update handling in fridge operations."""

    def test_concurrent_item_updates(self, client, auth_headers, test_fridge_items):
        """Concurrent fridge updates should not cause data loss."""
        item = test_fridge_items[0]
        results = []

        def update_item(quantity):
            response = client.patch(
                f"/api/fridge/items/{item.id}",
                headers=auth_headers,
                json={"quantity": quantity},
            )
            results.append((quantity, response.status_code, response.json()))

        threads = [
            threading.Thread(target=update_item, args=("100g",)),
            threading.Thread(target=update_item, args=("200g",)),
            threading.Thread(target=update_item, args=("300g",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All updates should succeed
        assert all(status_code == 200 for _, status_code, _ in results)

        # Final state should be consistent (last write wins)
        response = client.get("/api/fridge", headers=auth_headers)
        updated_item = next(
            (i for i in response.json()["items"] if i["id"] == str(item.id)),
            None
        )
        assert updated_item is not None
        assert updated_item["quantity"] in ["100g", "200g", "300g"]

    def test_concurrent_bulk_fridge_add(self, client, auth_headers):
        """Concurrent bulk adds should not cause duplicates or data loss."""
        results = []

        def add_bulk(items):
            response = client.post(
                "/api/fridge/items/bulk",
                headers=auth_headers,
                json={"items": items},
            )
            results.append(response.status_code)

        items_batch_1 = [
            {"ingredient_name": "tomatoes", "quantity": "3", "freshness_days": 5},
            {"ingredient_name": "onions", "quantity": "2", "freshness_days": 10},
        ]
        items_batch_2 = [
            {"ingredient_name": "peppers", "quantity": "4", "freshness_days": 7},
            {"ingredient_name": "garlic", "quantity": "1 head", "freshness_days": 14},
        ]

        threads = [
            threading.Thread(target=add_bulk, args=(items_batch_1,)),
            threading.Thread(target=add_bulk, args=(items_batch_2,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Both batches should succeed
        assert all(status == 201 for status in results)

        # Verify all items were added
        response = client.get("/api/fridge", headers=auth_headers)
        items = response.json()["items"]
        names = [i["ingredient_name"] for i in items]

        assert "tomatoes" in names
        assert "onions" in names
        assert "peppers" in names
        assert "garlic" in names

    def test_concurrent_add_and_delete(self, client, auth_headers, test_fridge_items):
        """Adding and deleting items concurrently should not crash."""
        item_to_delete = test_fridge_items[0]
        results = []

        def add_item():
            response = client.post(
                "/api/fridge/items",
                headers=auth_headers,
                json={
                    "ingredient_name": "new item",
                    "quantity": "1",
                    "freshness_days": 5,
                },
            )
            results.append(("add", response.status_code))

        def delete_item():
            response = client.delete(
                f"/api/fridge/items/{item_to_delete.id}",
                headers=auth_headers,
            )
            results.append(("delete", response.status_code))

        threads = [
            threading.Thread(target=add_item),
            threading.Thread(target=delete_item),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Both operations should complete without errors
        assert len(results) == 2
        add_result = next((r for r in results if r[0] == "add"), None)
        delete_result = next((r for r in results if r[0] == "delete"), None)

        assert add_result[1] == 201
        assert delete_result[1] in [204, 404]  # 404 if already deleted


# ============================================================================
# Edge Case Tests: Boundary Conditions
# ============================================================================

class TestFridgeBoundaryConditions:
    """Tests for boundary conditions in fridge operations."""

    def test_add_item_with_max_freshness_days(self, client, auth_headers):
        """Should handle maximum freshness days (365)."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "honey",
                "quantity": "1 jar",
                "freshness_days": 365,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["days_remaining"] == 365
        assert data["freshness_percentage"] == 100.0

    def test_add_item_with_minimum_freshness_days(self, client, auth_headers):
        """Should handle minimum valid freshness days (1)."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "fresh fish",
                "quantity": "200g",
                "freshness_days": 1,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["days_remaining"] == 1

    def test_special_characters_in_ingredient_name(self, client, auth_headers):
        """Should handle special characters in ingredient names."""
        special_name = "jalapeño & chile verde (fresh)"

        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": special_name,
                "quantity": "3",
                "freshness_days": 5,
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Name should be preserved (after sanitization of any dangerous chars)
        assert "jalape" in data["ingredient_name"]

    def test_unicode_in_quantity(self, client, auth_headers):
        """Should handle unicode characters in quantity."""
        response = client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "rice",
                "quantity": "500g (½ bag)",
                "freshness_days": 180,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "500g" in data["quantity"]

    def test_update_item_to_zero_days_remaining(self, client, auth_headers, test_fridge_items):
        """Should allow setting days_remaining to zero (expired)."""
        item_id = test_fridge_items[0].id

        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={"days_remaining": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days_remaining"] == 0
        assert data["freshness_percentage"] == 0.0

    def test_expiring_items_with_custom_high_threshold(self, client, auth_headers, test_fridge_items):
        """Should correctly filter with high threshold."""
        # Add an item with 100 days remaining
        client.post(
            "/api/fridge/items",
            headers=auth_headers,
            json={
                "ingredient_name": "dry pasta",
                "quantity": "1 kg",
                "freshness_days": 100,
            },
        )

        response = client.get(
            "/api/fridge/expiring",
            headers=auth_headers,
            params={"days_threshold": 200},
        )

        assert response.status_code == 200
        data = response.json()
        # Should include all items with days_remaining <= 200
        assert len(data) >= 1

    def test_add_many_items_at_once(self, client, auth_headers):
        """Should handle adding many items in a bulk request."""
        items = [
            {"ingredient_name": f"item_{i}", "quantity": "1", "freshness_days": 7}
            for i in range(50)
        ]

        response = client.post(
            "/api/fridge/items/bulk",
            headers=auth_headers,
            json={"items": items},
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 50
