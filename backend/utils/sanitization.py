"""
Input sanitization utilities for XSS prevention.

This module provides consistent input sanitization across all API routes
that accept user-provided text input.
"""
import re
from typing import Annotated, List

from pydantic import AfterValidator


def sanitize_text_input(value: str) -> str:
    """
    Sanitize text input to prevent XSS attacks.

    Removes HTML tags and script-like content while preserving legitimate text.

    Args:
        value: The input string to sanitize.

    Returns:
        The sanitized string with potentially dangerous content removed.

    Examples:
        >>> sanitize_text_input("Hello <script>alert('xss')</script>")
        "Hello alert('xss')"
        >>> sanitize_text_input("Click <a onclick='steal()'>here</a>")
        "Click here"
        >>> sanitize_text_input("javascript:alert(1)")
        "alert(1)"
    """
    if not value:
        return value

    # Remove HTML tags
    value = re.sub(r'<[^>]*>', '', value)
    # Remove javascript:, data:, and vbscript: URIs
    value = re.sub(r'(?i)(javascript|data|vbscript):', '', value)
    # Remove event handlers (onclick, onerror, onload, etc.)
    value = re.sub(r'(?i)on\w+\s*=', '', value)

    return value.strip()


def sanitize_list_items(values: List[str]) -> List[str]:
    """
    Sanitize a list of text inputs.

    Args:
        values: List of strings to sanitize.

    Returns:
        List of sanitized strings.
    """
    return [sanitize_text_input(v) for v in values]


def _validate_sanitized_str(value: str) -> str:
    """Pydantic validator for sanitized strings."""
    return sanitize_text_input(value)


def _validate_sanitized_list(values: List[str]) -> List[str]:
    """Pydantic validator for sanitized string lists."""
    return sanitize_list_items(values)


# Annotated types for use in Pydantic models
# Usage: field_name: SanitizedStr = Field(...)
SanitizedStr = Annotated[str, AfterValidator(_validate_sanitized_str)]

# For lists of strings
# Usage: field_name: SanitizedStrList = Field(...)
SanitizedStrList = Annotated[List[str], AfterValidator(_validate_sanitized_list)]
