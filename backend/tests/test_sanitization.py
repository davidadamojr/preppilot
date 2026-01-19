"""
Tests for input sanitization utilities.
"""
import pytest
from pydantic import BaseModel, Field, ValidationError

from backend.utils.sanitization import (
    sanitize_text_input,
    sanitize_list_items,
    SanitizedStr,
    SanitizedStrList,
)


class TestSanitizeTextInput:
    """Tests for the sanitize_text_input function."""

    def test_removes_html_tags(self):
        """Should remove all HTML tags from input."""
        assert sanitize_text_input("<script>alert('xss')</script>") == "alert('xss')"
        assert sanitize_text_input("<b>bold</b>") == "bold"
        assert sanitize_text_input("<a href='evil.com'>click</a>") == "click"
        assert sanitize_text_input("<div><span>nested</span></div>") == "nested"

    def test_removes_javascript_uri(self):
        """Should remove javascript: URIs."""
        assert sanitize_text_input("javascript:alert(1)") == "alert(1)"
        assert sanitize_text_input("JAVASCRIPT:evil()") == "evil()"
        assert sanitize_text_input("JaVaScRiPt:mixed()") == "mixed()"

    def test_removes_data_uri(self):
        """Should remove data: URIs."""
        assert sanitize_text_input("data:text/html,<script>") == "text/html,"
        assert sanitize_text_input("DATA:image/png;base64,xyz") == "image/png;base64,xyz"

    def test_removes_vbscript_uri(self):
        """Should remove vbscript: URIs."""
        assert sanitize_text_input("vbscript:msgbox") == "msgbox"
        assert sanitize_text_input("VBSCRIPT:evil") == "evil"

    def test_removes_event_handlers(self):
        """Should remove event handler attributes."""
        assert sanitize_text_input("onclick=evil()") == "evil()"
        assert sanitize_text_input("ONCLICK=evil()") == "evil()"
        assert sanitize_text_input("onerror=steal()") == "steal()"
        assert sanitize_text_input("onload=hack()") == "hack()"
        assert sanitize_text_input("onmouseover=track()") == "track()"

    def test_preserves_legitimate_text(self):
        """Should preserve normal text content."""
        assert sanitize_text_input("Hello World") == "Hello World"
        assert sanitize_text_input("Chicken breast (500g)") == "Chicken breast (500g)"
        assert sanitize_text_input("Gluten-free pasta") == "Gluten-free pasta"
        assert sanitize_text_input("2 cups flour") == "2 cups flour"

    def test_strips_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert sanitize_text_input("  hello  ") == "hello"
        assert sanitize_text_input("\n\thello\t\n") == "hello"

    def test_handles_empty_string(self):
        """Should handle empty strings gracefully."""
        assert sanitize_text_input("") == ""

    def test_handles_none_like_values(self):
        """Should return empty values unchanged."""
        # None values should be handled at the Pydantic level
        assert sanitize_text_input("") == ""

    def test_complex_xss_payloads(self):
        """Should handle complex XSS attack vectors."""
        # Nested tags
        payload = "<img src=x onerror=alert(1)>"
        assert "onerror" not in sanitize_text_input(payload).lower()
        assert "<" not in sanitize_text_input(payload)

        # Mixed case to evade filters
        payload = "<ScRiPt>alert('xss')</ScRiPt>"
        assert "<" not in sanitize_text_input(payload)

        # Multiple event handlers
        payload = "onclick=a() onmouseover=b() onload=c()"
        result = sanitize_text_input(payload)
        assert "onclick" not in result.lower()
        assert "onmouseover" not in result.lower()
        assert "onload" not in result.lower()

    def test_combined_attacks(self):
        """Should handle combinations of attack vectors."""
        payload = "<a href='javascript:alert(1)' onclick='steal()'>click me</a>"
        result = sanitize_text_input(payload)
        assert "<" not in result
        assert "javascript" not in result.lower()
        assert "onclick" not in result.lower()


class TestSanitizeListItems:
    """Tests for the sanitize_list_items function."""

    def test_sanitizes_all_items(self):
        """Should sanitize each item in the list."""
        items = ["<script>bad</script>", "normal", "<b>bold</b>"]
        result = sanitize_list_items(items)
        assert result == ["bad", "normal", "bold"]

    def test_handles_empty_list(self):
        """Should handle empty lists."""
        assert sanitize_list_items([]) == []

    def test_handles_single_item(self):
        """Should handle single-item lists."""
        assert sanitize_list_items(["<b>text</b>"]) == ["text"]


class TestSanitizedStrType:
    """Tests for the SanitizedStr annotated type with Pydantic."""

    def test_sanitizes_on_validation(self):
        """Should sanitize input during Pydantic validation."""
        class TestModel(BaseModel):
            name: SanitizedStr = Field(...)

        model = TestModel(name="<script>evil</script>Hello")
        assert model.name == "evilHello"

    def test_preserves_valid_input(self):
        """Should preserve valid input unchanged."""
        class TestModel(BaseModel):
            name: SanitizedStr = Field(...)

        model = TestModel(name="Valid Name")
        assert model.name == "Valid Name"

    def test_works_with_optional_fields(self):
        """Should work with optional fields."""
        from typing import Optional

        class TestModel(BaseModel):
            name: Optional[SanitizedStr] = None

        model1 = TestModel()
        assert model1.name is None

        model2 = TestModel(name="<b>bold</b>")
        assert model2.name == "bold"


class TestSanitizedStrListType:
    """Tests for the SanitizedStrList annotated type with Pydantic."""

    def test_sanitizes_list_on_validation(self):
        """Should sanitize all list items during Pydantic validation."""
        class TestModel(BaseModel):
            tags: SanitizedStrList = Field(...)

        model = TestModel(tags=["<b>tag1</b>", "tag2", "<script>evil</script>"])
        assert model.tags == ["tag1", "tag2", "evil"]

    def test_handles_empty_list(self):
        """Should handle empty lists."""
        class TestModel(BaseModel):
            tags: SanitizedStrList = Field(default_factory=list)

        model = TestModel()
        assert model.tags == []

    def test_works_with_optional_list(self):
        """Should work with optional list fields."""
        from typing import Optional

        class TestModel(BaseModel):
            tags: Optional[SanitizedStrList] = None

        model1 = TestModel()
        assert model1.tags is None

        model2 = TestModel(tags=["<b>tag</b>"])
        assert model2.tags == ["tag"]


class TestIntegrationWithRouteModels:
    """Integration tests simulating route model usage."""

    def test_register_request_sanitization(self):
        """Should sanitize RegisterRequest fields."""
        class RegisterRequest(BaseModel):
            full_name: SanitizedStr = Field(...)
            dietary_exclusions: SanitizedStrList = Field(default_factory=list)

        request = RegisterRequest(
            full_name="<script>John</script> Doe",
            dietary_exclusions=["<b>gluten</b>", "dairy"]
        )
        assert request.full_name == "John Doe"
        assert request.dietary_exclusions == ["gluten", "dairy"]

    def test_fridge_item_sanitization(self):
        """Should sanitize AddItemRequest fields."""
        class AddItemRequest(BaseModel):
            ingredient_name: SanitizedStr = Field(...)
            quantity: SanitizedStr = Field(...)

        request = AddItemRequest(
            ingredient_name="<b>Chicken</b> breast",
            quantity="500g<script>evil</script>"
        )
        assert request.ingredient_name == "Chicken breast"
        assert request.quantity == "500gevil"

    def test_recipe_create_sanitization(self):
        """Should sanitize RecipeCreate fields."""
        class RecipeCreate(BaseModel):
            name: SanitizedStr = Field(...)
            diet_tags: SanitizedStrList = Field(...)
            prep_steps: SanitizedStrList = Field(...)

        request = RecipeCreate(
            name="<script>Malicious</script> Soup",
            diet_tags=["<b>low-histamine</b>", "gluten-free"],
            prep_steps=["Step 1<script>evil</script>", "Step 2"]
        )
        assert request.name == "Malicious Soup"
        assert request.diet_tags == ["low-histamine", "gluten-free"]
        assert request.prep_steps == ["Step 1evil", "Step 2"]
