"""
Tests for error handling and error response format.

Tests cover:
- Custom exception classes and error codes
- Structured error responses from API endpoints
- Specific error messages for different failure scenarios
- Error code propagation through the API
"""
import pytest
from datetime import date, timedelta
from uuid import uuid4

from backend.errors import (
    ErrorCode,
    ErrorResponse,
    PrepPilotError,
    PlanNotFoundError,
    NoRecipesAvailableError,
    InsufficientRecipesError,
    PlanGenerationError,
    PlanAdaptationError,
    FridgeItemNotFoundError,
    FridgeOperationError,
    EmailError,
    EmailNotConfiguredError,
    EmailSendError,
    PDFGenerationError,
    RecipeNotFoundError,
    DatabaseError,
    DatabaseConnectionError,
)


class TestErrorCodeEnum:
    """Tests for ErrorCode enumeration."""

    def test_error_codes_are_strings(self):
        """Error codes should be string values."""
        assert isinstance(ErrorCode.PLAN_NOT_FOUND.value, str)
        assert ErrorCode.PLAN_NOT_FOUND.value == "PLAN_NOT_FOUND"

    def test_plan_related_codes_exist(self):
        """Plan-related error codes should exist."""
        plan_codes = [
            ErrorCode.PLAN_NOT_FOUND,
            ErrorCode.PLAN_NO_RECIPES_AVAILABLE,
            ErrorCode.PLAN_INSUFFICIENT_RECIPES,
            ErrorCode.PLAN_GENERATION_FAILED,
            ErrorCode.PLAN_ADAPTATION_FAILED,
            ErrorCode.PLAN_DATE_OUT_OF_RANGE,
            ErrorCode.PLAN_MEAL_NOT_FOUND,
        ]
        for code in plan_codes:
            assert code.value.startswith("PLAN_")

    def test_fridge_related_codes_exist(self):
        """Fridge-related error codes should exist."""
        fridge_codes = [
            ErrorCode.FRIDGE_ITEM_NOT_FOUND,
            ErrorCode.FRIDGE_ADD_FAILED,
            ErrorCode.FRIDGE_UPDATE_FAILED,
            ErrorCode.FRIDGE_BULK_ADD_FAILED,
        ]
        for code in fridge_codes:
            assert code.value.startswith("FRIDGE_")

    def test_email_related_codes_exist(self):
        """Email-related error codes should exist."""
        email_codes = [
            ErrorCode.EMAIL_SEND_FAILED,
            ErrorCode.EMAIL_NOT_CONFIGURED,
            ErrorCode.EMAIL_INVALID_RECIPIENT,
        ]
        for code in email_codes:
            assert code.value.startswith("EMAIL_")

    def test_database_related_codes_exist(self):
        """Database-related error codes should exist."""
        db_codes = [
            ErrorCode.DATABASE_CONNECTION_ERROR,
            ErrorCode.DATABASE_QUERY_ERROR,
            ErrorCode.DATABASE_INTEGRITY_ERROR,
        ]
        for code in db_codes:
            assert code.value.startswith("DATABASE_")


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_create_error_response(self):
        """Should create error response with all fields."""
        response = ErrorResponse(
            error_code=ErrorCode.PLAN_NOT_FOUND,
            message="Meal plan not found",
            details={"plan_id": "123"},
        )

        assert response.error_code == ErrorCode.PLAN_NOT_FOUND
        assert response.message == "Meal plan not found"
        assert response.details == {"plan_id": "123"}

    def test_error_response_without_details(self):
        """Should create error response without details."""
        response = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An error occurred",
        )

        assert response.error_code == ErrorCode.INTERNAL_ERROR
        assert response.details is None


class TestPrepPilotError:
    """Tests for base PrepPilotError exception."""

    def test_create_error(self):
        """Should create error with all attributes."""
        error = PrepPilotError(
            message="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"key": "value"},
            status_code=500,
        )

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.details == {"key": "value"}
        assert error.status_code == 500

    def test_to_response(self):
        """Should convert error to ErrorResponse."""
        error = PrepPilotError(
            message="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            details={"key": "value"},
        )

        response = error.to_response()
        assert isinstance(response, ErrorResponse)
        assert response.error_code == ErrorCode.INTERNAL_ERROR
        assert response.message == "Test error"
        assert response.details == {"key": "value"}

    def test_default_values(self):
        """Should have sensible defaults."""
        error = PrepPilotError(message="Test error")

        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.details == {}
        assert error.status_code == 500


class TestPlanExceptions:
    """Tests for plan-related exception classes."""

    def test_plan_not_found_error(self):
        """Should create plan not found error with details."""
        plan_id = str(uuid4())
        error = PlanNotFoundError(plan_id=plan_id)

        assert error.error_code == ErrorCode.PLAN_NOT_FOUND
        assert error.status_code == 404
        assert plan_id in error.message
        assert error.details["plan_id"] == plan_id

    def test_plan_not_found_custom_message(self):
        """Should accept custom message."""
        error = PlanNotFoundError(
            plan_id="123",
            message="Custom message",
        )

        assert error.message == "Custom message"

    def test_no_recipes_available_error(self):
        """Should create no recipes error with diet info."""
        error = NoRecipesAvailableError(
            diet_type="low_histamine",
            meal_type="dinner",
            exclusions=["peanuts", "shellfish"],
        )

        assert error.error_code == ErrorCode.PLAN_NO_RECIPES_AVAILABLE
        assert error.status_code == 422
        assert "low_histamine" in error.message
        assert "dinner" in error.message
        assert "peanuts" in error.message
        assert error.details["diet_type"] == "low_histamine"
        assert error.details["meal_type"] == "dinner"
        assert error.details["exclusions"] == ["peanuts", "shellfish"]

    def test_no_recipes_available_minimal(self):
        """Should work with only diet type."""
        error = NoRecipesAvailableError(diet_type="fodmap")

        assert "fodmap" in error.message
        assert "meal_type" not in error.details

    def test_insufficient_recipes_error(self):
        """Should provide recipe count information."""
        error = InsufficientRecipesError(
            needed=5,
            available=2,
            meal_type="breakfast",
            diet_type="low_histamine",
        )

        assert error.error_code == ErrorCode.PLAN_INSUFFICIENT_RECIPES
        assert error.status_code == 422
        assert "5" in error.message
        assert "2" in error.message
        assert error.details["needed"] == 5
        assert error.details["available"] == 2

    def test_plan_generation_error(self):
        """Should include reason for failure."""
        error = PlanGenerationError(
            reason="Database connection failed",
            details={"attempt": 3},
        )

        assert error.error_code == ErrorCode.PLAN_GENERATION_FAILED
        assert error.status_code == 500
        assert "Database connection failed" in error.message

    def test_plan_adaptation_error(self):
        """Should include plan ID and reason."""
        error = PlanAdaptationError(
            plan_id="123",
            reason="No alternative recipes found",
        )

        assert error.error_code == ErrorCode.PLAN_ADAPTATION_FAILED
        assert error.details["plan_id"] == "123"
        assert error.details["reason"] == "No alternative recipes found"


class TestFridgeExceptions:
    """Tests for fridge-related exception classes."""

    def test_fridge_item_not_found_by_id(self):
        """Should create error for item not found by ID."""
        item_id = str(uuid4())
        error = FridgeItemNotFoundError(item_id=item_id)

        assert error.error_code == ErrorCode.FRIDGE_ITEM_NOT_FOUND
        assert error.status_code == 404
        assert item_id in error.message
        assert error.details["item_id"] == item_id

    def test_fridge_item_not_found_by_name(self):
        """Should create error for ingredient not found by name."""
        error = FridgeItemNotFoundError(ingredient_name="chicken")

        assert "chicken" in error.message
        assert error.details["ingredient_name"] == "chicken"

    def test_fridge_operation_error(self):
        """Should describe failed operation."""
        error = FridgeOperationError(
            operation="add",
            reason="Duplicate ingredient",
            error_code=ErrorCode.FRIDGE_ADD_FAILED,
        )

        assert error.error_code == ErrorCode.FRIDGE_ADD_FAILED
        assert "add" in error.message
        assert error.details["operation"] == "add"
        assert error.details["reason"] == "Duplicate ingredient"


class TestEmailExceptions:
    """Tests for email-related exception classes."""

    def test_email_not_configured_error(self):
        """Should indicate SMTP not configured."""
        error = EmailNotConfiguredError()

        assert error.error_code == ErrorCode.EMAIL_NOT_CONFIGURED
        assert error.status_code == 503
        assert "SMTP" in error.message

    def test_email_send_error(self):
        """Should include recipient and reason."""
        error = EmailSendError(
            recipient="test@example.com",
            reason="Connection timeout",
            retryable=True,
        )

        assert error.error_code == ErrorCode.EMAIL_SEND_FAILED
        assert error.status_code == 502  # Retryable error
        assert "test@example.com" in error.message
        assert error.details["retryable"] is True

    def test_email_send_error_not_retryable(self):
        """Should return 500 for non-retryable errors."""
        error = EmailSendError(
            recipient="invalid@",
            reason="Invalid email address",
            retryable=False,
        )

        assert error.status_code == 500


class TestExportExceptions:
    """Tests for export-related exception classes."""

    def test_pdf_generation_error(self):
        """Should describe PDF generation failure."""
        error = PDFGenerationError(
            document_type="meal_plan",
            reason="Memory limit exceeded",
        )

        assert error.error_code == ErrorCode.EXPORT_PDF_GENERATION_FAILED
        assert "meal_plan" in error.message
        assert error.details["document_type"] == "meal_plan"
        assert error.details["reason"] == "Memory limit exceeded"


class TestDatabaseExceptions:
    """Tests for database-related exception classes."""

    def test_database_connection_error(self):
        """Should provide connection error message."""
        error = DatabaseConnectionError()

        assert error.error_code == ErrorCode.DATABASE_CONNECTION_ERROR
        assert error.status_code == 500
        assert "connect" in error.message.lower()


class TestPlanRouteErrorResponses:
    """Tests for error responses from plan routes."""

    def test_create_plan_no_recipes(self, client, db_session):
        """Should return structured error when no recipes match diet type."""
        from backend.db.models import User
        from backend.models.schemas import DietType
        from backend.auth.utils import hash_password

        # Create a user with a diet type that has no recipes in the database
        unique_email = f"fructose_test_{uuid4().hex[:8]}@example.com"
        fructose_user = User(
            email=unique_email,
            hashed_password=hash_password("password123"),
            diet_type=DietType.FRUCTOSE_FREE,  # No recipes exist for this diet type
        )
        db_session.add(fructose_user)
        db_session.commit()

        # Login as this user
        login_response = client.post(
            "/auth/login",
            json={"email": unique_email, "password": "password123"},
        )
        token = login_response.json()["access_token"]
        fructose_headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/plans",
            headers=fructose_headers,
            json={
                "start_date": str(date.today()),
                "days": 3,
            },
        )

        # Should get 422 error since no recipes match fructose_free diet
        assert response.status_code == 422
        data = response.json()
        detail = data.get("detail", {})
        # Should have structured error format
        assert "error_code" in detail
        assert "message" in detail

    def test_get_plan_not_found(self, client, auth_headers):
        """Should return 404 with structured error for missing plan."""
        fake_id = uuid4()
        response = client.get(
            f"/api/plans/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "Meal plan not found" in data["detail"]

    def test_delete_plan_not_found(self, client, auth_headers):
        """Should return 404 for non-existent plan."""
        fake_id = uuid4()
        response = client.delete(
            f"/api/plans/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_adapt_plan_not_found(self, client, auth_headers):
        """Should return structured error when plan not found for adaptation."""
        fake_id = uuid4()
        response = client.post(
            f"/api/plans/{fake_id}/adapt",
            headers=auth_headers,
            json={"current_date": str(date.today())},
        )

        assert response.status_code == 404
        data = response.json()
        detail = data.get("detail", {})
        assert detail.get("error_code") == ErrorCode.PLAN_NOT_FOUND.value

    def test_mark_prep_meal_not_found(self, client, auth_headers, test_meal_plan):
        """Should return 404 when marking non-existent meal."""
        # Try to mark a meal for a date outside the plan's range
        response = client.patch(
            f"/api/plans/{test_meal_plan.id}/mark-prep",
            headers=auth_headers,
            json={
                "date": str(date.today() + timedelta(days=100)),
                "meal_type": "dinner",
                "status": "DONE",  # Must match PrepStatus enum value
            },
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestFridgeRouteErrorResponses:
    """Tests for error responses from fridge routes."""

    def test_remove_item_not_found(self, client, auth_headers):
        """Should return 404 with clear message for missing item."""
        fake_id = uuid4()
        response = client.delete(
            f"/api/fridge/items/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_remove_by_name_not_found(self, client, auth_headers):
        """Should return 404 with ingredient name in message."""
        response = client.delete(
            "/api/fridge/items/by-name/nonexistent_ingredient",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "nonexistent_ingredient" in data["detail"]

    def test_update_item_not_found(self, client, auth_headers):
        """Should return 404 for non-existent item update."""
        fake_id = uuid4()
        response = client.patch(
            f"/api/fridge/items/{fake_id}",
            headers=auth_headers,
            json={"quantity": "500g"},
        )

        assert response.status_code == 404

    def test_update_item_no_fields(self, client, auth_headers, test_fridge_items):
        """Should return 400 when no fields provided for update."""
        item_id = test_fridge_items[0].id
        response = client.patch(
            f"/api/fridge/items/{item_id}",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 400
        data = response.json()
        assert "at least one field" in data["detail"].lower()


class TestExportRouteErrorResponses:
    """Tests for error responses from export routes."""

    def test_pdf_plan_not_found(self, client, auth_headers):
        """Should return 404 when exporting non-existent plan."""
        fake_id = uuid4()
        response = client.get(
            f"/api/export/{fake_id}/pdf",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_catch_up_pdf_plan_not_found(self, client, auth_headers):
        """Should return 404 for catch-up PDF of non-existent plan."""
        fake_id = uuid4()
        response = client.get(
            f"/api/export/{fake_id}/catch-up-pdf",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_shopping_list_pdf_plan_not_found(self, client, auth_headers):
        """Should return 404 for shopping list of non-existent plan."""
        fake_id = uuid4()
        response = client.get(
            f"/api/export/{fake_id}/shopping-list-pdf",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestEmailRouteErrorResponses:
    """Tests for error responses from email routes."""

    def test_send_plan_email_not_found(self, client, auth_headers):
        """Should return 404 when plan not found for email."""
        fake_id = uuid4()
        response = client.post(
            f"/api/email/{fake_id}/send-plan",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_send_adaptation_email_plan_not_found(self, client, auth_headers):
        """Should return 404 with structured error for missing plan."""
        fake_id = uuid4()
        response = client.post(
            f"/api/email/{fake_id}/send-adaptation",
            headers=auth_headers,
        )

        assert response.status_code == 404
