"""
Custom exceptions and error codes for the PrepPilot application.

This module provides:
- Structured error codes for categorized error handling
- Custom exception classes for specific failure scenarios
- Error response schema for consistent API responses
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """
    Application-wide error codes for categorized error handling.

    Format: CATEGORY_SPECIFIC_ERROR
    Categories:
    - PLAN_*: Meal plan related errors
    - RECIPE_*: Recipe related errors
    - FRIDGE_*: Fridge/ingredient related errors
    - EMAIL_*: Email service errors
    - AUTH_*: Authentication errors
    - VALIDATION_*: Input validation errors
    - DATABASE_*: Database operation errors
    - EXTERNAL_*: External service errors
    """

    # Plan-related errors
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    PLAN_NO_RECIPES_AVAILABLE = "PLAN_NO_RECIPES_AVAILABLE"
    PLAN_INSUFFICIENT_RECIPES = "PLAN_INSUFFICIENT_RECIPES"
    PLAN_GENERATION_FAILED = "PLAN_GENERATION_FAILED"
    PLAN_ADAPTATION_FAILED = "PLAN_ADAPTATION_FAILED"
    PLAN_DATE_OUT_OF_RANGE = "PLAN_DATE_OUT_OF_RANGE"
    PLAN_MEAL_NOT_FOUND = "PLAN_MEAL_NOT_FOUND"
    PLAN_LIMIT_EXCEEDED = "PLAN_LIMIT_EXCEEDED"

    # Recipe-related errors
    RECIPE_NOT_FOUND = "RECIPE_NOT_FOUND"
    RECIPE_ALREADY_EXISTS = "RECIPE_ALREADY_EXISTS"
    RECIPE_INVALID_DATA = "RECIPE_INVALID_DATA"

    # Fridge-related errors
    FRIDGE_ITEM_NOT_FOUND = "FRIDGE_ITEM_NOT_FOUND"
    FRIDGE_ADD_FAILED = "FRIDGE_ADD_FAILED"
    FRIDGE_UPDATE_FAILED = "FRIDGE_UPDATE_FAILED"
    FRIDGE_BULK_ADD_FAILED = "FRIDGE_BULK_ADD_FAILED"

    # Email-related errors
    EMAIL_SEND_FAILED = "EMAIL_SEND_FAILED"
    EMAIL_NOT_CONFIGURED = "EMAIL_NOT_CONFIGURED"
    EMAIL_INVALID_RECIPIENT = "EMAIL_INVALID_RECIPIENT"
    EMAIL_TEMPLATE_ERROR = "EMAIL_TEMPLATE_ERROR"
    EMAIL_ATTACHMENT_ERROR = "EMAIL_ATTACHMENT_ERROR"

    # Export-related errors
    EXPORT_PDF_GENERATION_FAILED = "EXPORT_PDF_GENERATION_FAILED"
    EXPORT_ADAPTATION_FAILED = "EXPORT_ADAPTATION_FAILED"

    # Validation errors
    VALIDATION_INVALID_DATE = "VALIDATION_INVALID_DATE"
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"

    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_INTEGRITY_ERROR = "DATABASE_INTEGRITY_ERROR"

    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorResponse(BaseModel):
    """Structured error response for API errors."""
    error_code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class PrepPilotError(Exception):
    """
    Base exception for all PrepPilot application errors.

    Provides structured error information for consistent error handling.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def to_response(self) -> ErrorResponse:
        """Convert exception to ErrorResponse for API output."""
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details if self.details else None,
        )


# Plan-related exceptions

class PlanNotFoundError(PrepPilotError):
    """Raised when a meal plan is not found."""

    def __init__(self, plan_id: str, message: str = None):
        super().__init__(
            message=message or f"Meal plan '{plan_id}' not found",
            error_code=ErrorCode.PLAN_NOT_FOUND,
            details={"plan_id": plan_id},
            status_code=404,
        )


class NoRecipesAvailableError(PrepPilotError):
    """Raised when no recipes are available for the given criteria."""

    def __init__(
        self,
        diet_type: str,
        meal_type: str = None,
        exclusions: list = None,
    ):
        details = {"diet_type": diet_type}
        if meal_type:
            details["meal_type"] = meal_type
        if exclusions:
            details["exclusions"] = exclusions

        message = f"No recipes available for diet type '{diet_type}'"
        if meal_type:
            message += f" and meal type '{meal_type}'"
        if exclusions:
            message += f" (excluding: {', '.join(exclusions)})"
        message += ". Please adjust your dietary preferences or add more recipes."

        super().__init__(
            message=message,
            error_code=ErrorCode.PLAN_NO_RECIPES_AVAILABLE,
            details=details,
            status_code=422,
        )


class InsufficientRecipesError(PrepPilotError):
    """Raised when there aren't enough recipes to fill the plan."""

    def __init__(
        self,
        needed: int,
        available: int,
        meal_type: str,
        diet_type: str,
    ):
        super().__init__(
            message=f"Insufficient recipes for {meal_type}: need {needed}, but only {available} available for '{diet_type}' diet",
            error_code=ErrorCode.PLAN_INSUFFICIENT_RECIPES,
            details={
                "needed": needed,
                "available": available,
                "meal_type": meal_type,
                "diet_type": diet_type,
            },
            status_code=422,
        )


class PlanGenerationError(PrepPilotError):
    """Raised when meal plan generation fails."""

    def __init__(self, reason: str, details: Dict[str, Any] = None):
        super().__init__(
            message=f"Failed to generate meal plan: {reason}",
            error_code=ErrorCode.PLAN_GENERATION_FAILED,
            details=details,
            status_code=500,
        )


class PlanAdaptationError(PrepPilotError):
    """Raised when plan adaptation fails."""

    def __init__(self, plan_id: str, reason: str, details: Dict[str, Any] = None):
        base_details = {"plan_id": plan_id, "reason": reason}
        if details:
            base_details.update(details)
        super().__init__(
            message=f"Failed to adapt meal plan: {reason}",
            error_code=ErrorCode.PLAN_ADAPTATION_FAILED,
            details=base_details,
            status_code=500,
        )


class MealNotFoundError(PrepPilotError):
    """Raised when a specific meal is not found in a plan."""

    def __init__(self, plan_id: str, date: str, meal_type: str):
        super().__init__(
            message=f"Meal '{meal_type}' not found for date {date} in plan",
            error_code=ErrorCode.PLAN_MEAL_NOT_FOUND,
            details={
                "plan_id": plan_id,
                "date": date,
                "meal_type": meal_type,
            },
            status_code=404,
        )


class PlanLimitExceededError(PrepPilotError):
    """Raised when user has reached the maximum number of meal plans."""

    def __init__(self, current_count: int, max_limit: int):
        super().__init__(
            message=f"You have reached the maximum limit of {max_limit} meal plans. Please delete an existing plan to create a new one.",
            error_code=ErrorCode.PLAN_LIMIT_EXCEEDED,
            details={
                "current_count": current_count,
                "max_limit": max_limit,
            },
            status_code=403,
        )


# Fridge-related exceptions

class FridgeItemNotFoundError(PrepPilotError):
    """Raised when a fridge item is not found."""

    def __init__(self, item_id: str = None, ingredient_name: str = None):
        if item_id:
            message = f"Fridge item '{item_id}' not found"
            details = {"item_id": item_id}
        else:
            message = f"Ingredient '{ingredient_name}' not found in fridge"
            details = {"ingredient_name": ingredient_name}

        super().__init__(
            message=message,
            error_code=ErrorCode.FRIDGE_ITEM_NOT_FOUND,
            details=details,
            status_code=404,
        )


class FridgeOperationError(PrepPilotError):
    """Raised when a fridge operation fails."""

    def __init__(
        self,
        operation: str,
        reason: str,
        error_code: ErrorCode = ErrorCode.FRIDGE_ADD_FAILED,
        details: Dict[str, Any] = None,
    ):
        base_details = {"operation": operation, "reason": reason}
        if details:
            base_details.update(details)
        super().__init__(
            message=f"Fridge {operation} failed: {reason}",
            error_code=error_code,
            details=base_details,
            status_code=500,
        )


# Email-related exceptions

class EmailError(PrepPilotError):
    """Base exception for email-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.EMAIL_SEND_FAILED,
        details: Dict[str, Any] = None,
        status_code: int = 500,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=status_code,
        )


class EmailNotConfiguredError(EmailError):
    """Raised when email service is not properly configured."""

    def __init__(self):
        super().__init__(
            message="Email service is not configured. Please configure SMTP settings.",
            error_code=ErrorCode.EMAIL_NOT_CONFIGURED,
            status_code=503,
        )


class EmailSendError(EmailError):
    """Raised when email sending fails."""

    def __init__(self, recipient: str, reason: str, retryable: bool = False):
        super().__init__(
            message=f"Failed to send email to {recipient}: {reason}",
            error_code=ErrorCode.EMAIL_SEND_FAILED,
            details={
                "recipient": recipient,
                "reason": reason,
                "retryable": retryable,
            },
            status_code=502 if retryable else 500,
        )


# Export-related exceptions

class ExportError(PrepPilotError):
    """Base exception for export-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.EXPORT_PDF_GENERATION_FAILED,
        details: Dict[str, Any] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=500,
        )


class PDFGenerationError(ExportError):
    """Raised when PDF generation fails."""

    def __init__(self, document_type: str, reason: str):
        super().__init__(
            message=f"Failed to generate {document_type} PDF: {reason}",
            error_code=ErrorCode.EXPORT_PDF_GENERATION_FAILED,
            details={
                "document_type": document_type,
                "reason": reason,
            },
        )


# Recipe-related exceptions

class RecipeNotFoundError(PrepPilotError):
    """Raised when a recipe is not found."""

    def __init__(self, recipe_id: str):
        super().__init__(
            message=f"Recipe '{recipe_id}' not found",
            error_code=ErrorCode.RECIPE_NOT_FOUND,
            details={"recipe_id": recipe_id},
            status_code=404,
        )


class RecipeAlreadyExistsError(PrepPilotError):
    """Raised when trying to create a recipe that already exists."""

    def __init__(self, recipe_name: str):
        super().__init__(
            message=f"Recipe with name '{recipe_name}' already exists",
            error_code=ErrorCode.RECIPE_ALREADY_EXISTS,
            details={"recipe_name": recipe_name},
            status_code=409,
        )


# Database-related exceptions

class DatabaseError(PrepPilotError):
    """Base exception for database-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DATABASE_QUERY_ERROR,
        details: Dict[str, Any] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            status_code=500,
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self):
        super().__init__(
            message="Unable to connect to the database. Please try again later.",
            error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
        )


class DatabaseIntegrityError(DatabaseError):
    """Raised when a database integrity constraint is violated."""

    def __init__(self, constraint: str, details: Dict[str, Any] = None):
        super().__init__(
            message=f"Database integrity error: {constraint}",
            error_code=ErrorCode.DATABASE_INTEGRITY_ERROR,
            details=details,
        )
