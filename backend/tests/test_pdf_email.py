"""
Tests for PDF generation and email services.

Unit tests run without database. Integration tests require PostgreSQL.
"""
import pytest
from datetime import date, datetime, timedelta
from uuid import uuid4
from unittest.mock import patch, MagicMock, Mock

from backend.services.pdf_service import PDFService
from backend.services.email_service import EmailService
from backend.models.schemas import (
    MealPlan, MealSlot, Recipe, Ingredient, DietType, PrepStatus,
    AdaptiveEngineOutput, AdaptationReason, FridgeState, FridgeItem
)


# ============================================================================
# Unit Tests (no database required)
# ============================================================================

class TestPDFServiceUnit:
    """Unit tests for PDF service that don't require database."""

    def test_group_by_category(self):
        """Shopping list should be grouped by category."""
        mock_db = Mock()
        pdf_service = PDFService(mock_db)

        shopping_list = {
            "chicken thighs": "500g",
            "carrots": "3 medium",
            "rice": "2 cups",
            "olive oil": "2 tbsp",
        }

        grouped = pdf_service._group_by_category(shopping_list)

        assert "protein" in grouped
        assert "produce" in grouped
        assert "grains" in grouped
        assert "chicken thighs" in grouped["protein"]
        assert "carrots" in grouped["produce"]
        assert "rice" in grouped["grains"]

    def test_format_status_done(self):
        """Format status should return correct text for done."""
        mock_db = Mock()
        pdf_service = PDFService(mock_db)

        result = pdf_service._format_status(PrepStatus.DONE)
        assert "Done" in result

    def test_format_status_pending(self):
        """Format status should return correct text for pending."""
        mock_db = Mock()
        pdf_service = PDFService(mock_db)

        result = pdf_service._format_status(PrepStatus.PENDING)
        assert "Pending" in result

    def test_format_status_skipped(self):
        """Format status should return correct text for skipped."""
        mock_db = Mock()
        pdf_service = PDFService(mock_db)

        result = pdf_service._format_status(PrepStatus.SKIPPED)
        assert "Skipped" in result

    def test_generate_shopping_list(self):
        """Should generate aggregated shopping list from meal plan."""
        mock_db = Mock()
        pdf_service = PDFService(mock_db)

        # Create a simple meal plan
        recipe = Recipe(
            id="test-1",
            name="Test Recipe",
            diet_tags=["low_histamine"],
            meal_type="dinner",
            ingredients=[
                Ingredient(name="chicken", freshness_days=3, quantity="500g", category="protein"),
                Ingredient(name="rice", freshness_days=30, quantity="1 cup", category="grains"),
            ],
            prep_steps=["Cook"],
            prep_time_minutes=30,
            reusability_index=0.8,
            servings=2
        )

        plan = MealPlan(
            id=uuid4(),
            user_id=uuid4(),
            diet_type=DietType.LOW_HISTAMINE,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            meals=[
                MealSlot(date=date.today(), meal_type="dinner", recipe=recipe, prep_status=PrepStatus.PENDING)
            ]
        )

        shopping = pdf_service._generate_shopping_list(plan)

        assert "chicken" in shopping
        assert "rice" in shopping
        assert shopping["chicken"] == "500g"


class TestEmailServiceUnit:
    """Unit tests for email service that don't require database."""

    def test_email_disabled_returns_true(self):
        """When email is disabled, send should return True without sending."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = False

            result = email_service._send_email(
                to_email="test@example.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is True

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Email should be sent successfully when configured."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_body="<p>Test Body</p>"
            )

            assert result is True
            mock_server.sendmail.assert_called_once()

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_send_email_with_attachment(self, mock_smtp):
        """Email with attachment should include the file."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test with PDF",
                html_body="<p>See attached</p>",
                attachments=[("test.pdf", b"PDF content here")]
            )

            assert result is True

    def test_build_adaptation_email_html(self):
        """Adaptation email HTML should be generated correctly."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        # Create mock user
        mock_user = Mock()
        mock_user.full_name = "Test User"
        mock_user.email = "test@example.com"

        # Create test adaptation output
        adaptation_output = AdaptiveEngineOutput(
            new_plan=MealPlan(
                id=uuid4(),
                user_id=uuid4(),
                diet_type=DietType.LOW_HISTAMINE,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=2),
                meals=[]
            ),
            adaptation_summary=[
                AdaptationReason(
                    type="simplify",
                    affected_date=date.today(),
                    original_meal="Complex Stew",
                    new_meal="Simple Bowl",
                    reason="Simplified for faster catch-up"
                )
            ],
            priority_ingredients=["chicken", "carrots"],
            estimated_recovery_time_minutes=45
        )

        html = email_service._build_adaptation_email_html(mock_user, adaptation_output)

        assert "PrepPilot" in html
        assert "45" in html  # Recovery time
        assert "chicken" in html
        assert "carrots" in html

    def test_build_expiring_items_email_html(self):
        """Expiring items email HTML should be generated correctly."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        mock_user = Mock()
        mock_user.full_name = "Test User"
        mock_user.email = "test@example.com"

        expiring_items = [
            FridgeItem(
                ingredient_name="chicken",
                quantity="500g",
                days_remaining=1,
                added_date=date.today() - timedelta(days=2),
                original_freshness_days=3
            ),
            FridgeItem(
                ingredient_name="carrots",
                quantity="3 medium",
                days_remaining=2,
                added_date=date.today() - timedelta(days=5),
                original_freshness_days=7
            )
        ]

        html = email_service._build_expiring_items_email_html(mock_user, expiring_items)

        assert "chicken" in html
        assert "500g" in html
        assert "carrots" in html

    def test_build_weekly_summary_email_html(self):
        """Weekly summary email HTML should be generated correctly."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        mock_user = Mock()
        mock_user.full_name = "Test User"
        mock_user.email = "test@example.com"

        mock_plan = Mock()
        mock_plan.start_date = date.today()
        mock_plan.end_date = date.today() + timedelta(days=2)

        html = email_service._build_weekly_summary_email_html(mock_user, mock_plan)

        assert "PrepPilot" in html
        assert "meal plan is ready" in html


# ============================================================================
# Integration Tests (require database)
# ============================================================================


class TestPDFService:
    """Tests for PDF generation service."""

    def test_generate_meal_plan_pdf_returns_bytes(self, db_session, test_user, test_meal_plan):
        """PDF generation should return valid bytes."""
        pdf_service = PDFService(db_session)

        pdf_bytes = pdf_service.generate_meal_plan_pdf(test_meal_plan)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b'%PDF'

    def test_generate_meal_plan_pdf_without_shopping_list(self, db_session, test_meal_plan):
        """PDF can be generated without shopping list."""
        pdf_service = PDFService(db_session)

        pdf_bytes = pdf_service.generate_meal_plan_pdf(
            test_meal_plan,
            include_shopping_list=False
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b'%PDF'

    def test_generate_meal_plan_pdf_with_adaptation_notes(self, db_session, test_meal_plan):
        """PDF should include adaptation notes when provided."""
        pdf_service = PDFService(db_session)

        adaptation_notes = [
            "Simplified Thursday plan due to missed prep",
            "Substituted salmon with turkey for freshness"
        ]

        pdf_bytes = pdf_service.generate_meal_plan_pdf(
            test_meal_plan,
            adaptation_notes=adaptation_notes
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_generate_catch_up_pdf(self, db_session, test_user, test_meal_plan):
        """Catch-up PDF should include adaptation details."""
        pdf_service = PDFService(db_session)

        # Create adaptation output
        from backend.services.meal_service import db_meal_plan_to_schema
        schema_plan = db_meal_plan_to_schema(test_meal_plan, db_session)

        adaptation_output = AdaptiveEngineOutput(
            new_plan=schema_plan,
            adaptation_summary=[
                AdaptationReason(
                    type="simplify",
                    affected_date=date.today(),
                    original_meal="Complex Stew",
                    new_meal="Simple Bowl",
                    reason="Simplified for faster catch-up"
                )
            ],
            grocery_adjustments=["Remove salmon", "Add turkey"],
            priority_ingredients=["chicken", "carrots"],
            estimated_recovery_time_minutes=45
        )

        fridge_state = FridgeState(
            user_id=test_user.id,
            items=[
                FridgeItem(
                    ingredient_name="chicken",
                    quantity="500g",
                    days_remaining=1,
                    added_date=date.today() - timedelta(days=2),
                    original_freshness_days=3
                )
            ]
        )

        pdf_bytes = pdf_service.generate_catch_up_pdf(
            test_meal_plan,
            adaptation_output,
            fridge_state
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b'%PDF'

    def test_group_by_category(self, db_session):
        """Shopping list should be grouped by category."""
        pdf_service = PDFService(db_session)

        shopping_list = {
            "chicken thighs": "500g",
            "carrots": "3 medium",
            "rice": "2 cups",
            "olive oil": "2 tbsp",
        }

        grouped = pdf_service._group_by_category(shopping_list)

        assert "protein" in grouped
        assert "produce" in grouped
        assert "grains" in grouped
        assert "chicken thighs" in grouped["protein"]
        assert "carrots" in grouped["produce"]
        assert "rice" in grouped["grains"]


class TestEmailService:
    """Tests for email notification service."""

    def test_email_disabled_returns_true(self, db_session, test_user):
        """When email is disabled, send should return True without sending."""
        email_service = EmailService(db_session)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = False

            result = email_service._send_email(
                to_email=test_user.email,
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is True

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, db_session, test_user):
        """Email should be sent successfully when configured."""
        email_service = EmailService(db_session)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"

            result = email_service._send_email(
                to_email=test_user.email,
                subject="Test Subject",
                html_body="<p>Test Body</p>"
            )

            assert result is True
            mock_server.sendmail.assert_called_once()

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_send_email_with_attachment(self, mock_smtp, db_session, test_user):
        """Email with attachment should include the file."""
        email_service = EmailService(db_session)

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"

            result = email_service._send_email(
                to_email=test_user.email,
                subject="Test with PDF",
                html_body="<p>See attached</p>",
                attachments=[("test.pdf", b"PDF content here")]
            )

            assert result is True

    def test_build_adaptation_email_html(self, db_session, test_user):
        """Adaptation email HTML should be generated correctly."""
        email_service = EmailService(db_session)

        # Create test adaptation output
        adaptation_output = AdaptiveEngineOutput(
            new_plan=MealPlan(
                id=uuid4(),
                user_id=test_user.id,
                diet_type=DietType.LOW_HISTAMINE,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=2),
                meals=[]
            ),
            adaptation_summary=[
                AdaptationReason(
                    type="simplify",
                    affected_date=date.today(),
                    original_meal="Complex Stew",
                    new_meal="Simple Bowl",
                    reason="Simplified for faster catch-up"
                )
            ],
            priority_ingredients=["chicken", "carrots"],
            estimated_recovery_time_minutes=45
        )

        html = email_service._build_adaptation_email_html(test_user, adaptation_output)

        assert "PrepPilot" in html
        assert "45" in html  # Recovery time
        assert "chicken" in html
        assert "carrots" in html

    def test_build_expiring_items_email_html(self, db_session, test_user):
        """Expiring items email HTML should be generated correctly."""
        email_service = EmailService(db_session)

        expiring_items = [
            FridgeItem(
                ingredient_name="chicken",
                quantity="500g",
                days_remaining=1,
                added_date=date.today() - timedelta(days=2),
                original_freshness_days=3
            ),
            FridgeItem(
                ingredient_name="carrots",
                quantity="3 medium",
                days_remaining=2,
                added_date=date.today() - timedelta(days=5),
                original_freshness_days=7
            )
        ]

        html = email_service._build_expiring_items_email_html(test_user, expiring_items)

        assert "chicken" in html
        assert "500g" in html
        assert "carrots" in html
        assert "1 day" in html or "1 days" in html

    def test_build_weekly_summary_email_html(self, db_session, test_user, test_meal_plan):
        """Weekly summary email HTML should be generated correctly."""
        email_service = EmailService(db_session)

        html = email_service._build_weekly_summary_email_html(test_user, test_meal_plan)

        assert "PrepPilot" in html
        assert "meal plan is ready" in html


# Fixtures are now provided by conftest.py:
# - db_session: In-memory SQLite database session
# - test_user: Test user with email="test@example.com"
# - test_meal_plan: Test meal plan with meal slots
