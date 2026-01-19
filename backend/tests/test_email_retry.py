"""
Tests for email retry logic with exponential backoff.

Tests the EmailRetryQueue, backoff calculation, and retry behavior.
"""
import pytest
import smtplib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
from uuid import uuid4

from backend.services.email_service import (
    EmailService,
    EmailRetryQueue,
    EmailQueueEntry,
    EmailStatus,
    calculate_backoff_delay,
)


class TestCalculateBackoffDelay:
    """Tests for exponential backoff delay calculation."""

    def test_first_attempt_uses_base_delay(self):
        """First attempt (attempt=0) should use base delay."""
        delay = calculate_backoff_delay(attempt=0, base_delay=1.0)
        assert delay == 1.0

    def test_exponential_growth(self):
        """Delay should grow exponentially."""
        delays = [calculate_backoff_delay(i, base_delay=1.0, exponential_base=2.0) for i in range(4)]
        assert delays == [1.0, 2.0, 4.0, 8.0]

    def test_respects_max_delay(self):
        """Delay should not exceed max_delay."""
        delay = calculate_backoff_delay(attempt=10, base_delay=1.0, max_delay=60.0)
        assert delay == 60.0

    def test_custom_exponential_base(self):
        """Should use custom exponential base."""
        delay = calculate_backoff_delay(attempt=2, base_delay=1.0, exponential_base=3.0)
        assert delay == 9.0  # 1 * 3^2

    def test_custom_base_delay(self):
        """Should use custom base delay."""
        delay = calculate_backoff_delay(attempt=1, base_delay=5.0, exponential_base=2.0)
        assert delay == 10.0  # 5 * 2^1


class TestEmailQueueEntry:
    """Tests for EmailQueueEntry dataclass."""

    def test_create_sets_defaults(self):
        """create() should set default values correctly."""
        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Body</p>",
        )

        assert entry.to_email == "test@example.com"
        assert entry.subject == "Test Subject"
        assert entry.html_body == "<p>Body</p>"
        assert entry.text_body is None
        assert entry.attachments is None
        assert entry.status == EmailStatus.PENDING
        assert entry.attempt_count == 0
        assert entry.next_retry_at is None
        assert entry.last_error is None
        assert entry.id is not None
        assert entry.created_at is not None

    def test_create_with_attachments(self):
        """create() should accept attachments."""
        attachments = [("file.pdf", b"content")]
        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Body</p>",
            attachments=attachments,
        )

        assert entry.attachments == attachments


class TestEmailRetryQueue:
    """Tests for EmailRetryQueue."""

    def test_add_and_get_all(self):
        """Should add entries and retrieve them."""
        queue = EmailRetryQueue()
        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Body</p>",
        )

        queue.add(entry)
        all_entries = queue.get_all()

        assert len(all_entries) == 1
        assert all_entries[0].id == entry.id

    def test_remove(self):
        """Should remove entry by ID."""
        queue = EmailRetryQueue()
        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Body</p>",
        )
        queue.add(entry)

        removed = queue.remove(entry.id)

        assert removed is not None
        assert removed.id == entry.id
        assert len(queue.get_all()) == 0

    def test_remove_nonexistent_returns_none(self):
        """Remove should return None for nonexistent ID."""
        queue = EmailRetryQueue()
        result = queue.remove(uuid4())
        assert result is None

    def test_get_pending_retries_filters_correctly(self):
        """Should only return entries ready for retry."""
        queue = EmailRetryQueue()

        # Entry ready for retry (past next_retry_at)
        ready_entry = EmailQueueEntry.create(
            to_email="ready@example.com",
            subject="Ready",
            html_body="<p>Ready</p>",
        )
        ready_entry.status = EmailStatus.RETRY_SCHEDULED
        ready_entry.next_retry_at = datetime.utcnow() - timedelta(minutes=5)
        queue.add(ready_entry)

        # Entry not ready (future next_retry_at)
        future_entry = EmailQueueEntry.create(
            to_email="future@example.com",
            subject="Future",
            html_body="<p>Future</p>",
        )
        future_entry.status = EmailStatus.RETRY_SCHEDULED
        future_entry.next_retry_at = datetime.utcnow() + timedelta(hours=1)
        queue.add(future_entry)

        # Entry with wrong status
        pending_entry = EmailQueueEntry.create(
            to_email="pending@example.com",
            subject="Pending",
            html_body="<p>Pending</p>",
        )
        pending_entry.status = EmailStatus.PENDING
        queue.add(pending_entry)

        pending_retries = queue.get_pending_retries()

        assert len(pending_retries) == 1
        assert pending_retries[0].to_email == "ready@example.com"

    def test_get_failed(self):
        """Should return only failed entries."""
        queue = EmailRetryQueue()

        failed_entry = EmailQueueEntry.create(
            to_email="failed@example.com",
            subject="Failed",
            html_body="<p>Failed</p>",
        )
        failed_entry.status = EmailStatus.FAILED
        queue.add(failed_entry)

        scheduled_entry = EmailQueueEntry.create(
            to_email="scheduled@example.com",
            subject="Scheduled",
            html_body="<p>Scheduled</p>",
        )
        scheduled_entry.status = EmailStatus.RETRY_SCHEDULED
        queue.add(scheduled_entry)

        failed = queue.get_failed()

        assert len(failed) == 1
        assert failed[0].to_email == "failed@example.com"

    def test_clear(self):
        """Should clear all entries and return count."""
        queue = EmailRetryQueue()

        for i in range(5):
            entry = EmailQueueEntry.create(
                to_email=f"test{i}@example.com",
                subject="Test",
                html_body="<p>Body</p>",
            )
            queue.add(entry)

        count = queue.clear()

        assert count == 5
        assert len(queue.get_all()) == 0


class TestEmailServiceRetry:
    """Tests for EmailService retry logic."""

    def test_email_disabled_returns_true_no_retry(self):
        """When email disabled, should return True without retry."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = False

            result = email_service._send_email(
                to_email="test@example.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is True
            assert len(retry_queue.get_all()) == 0

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_successful_first_attempt(self, mock_smtp):
        """Should succeed on first attempt without retries."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

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
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 0.01  # Fast for tests
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is True
            assert mock_server.sendmail.call_count == 1
            assert len(retry_queue.get_all()) == 0

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_retries_on_transient_failure(self, mock_smtp):
        """Should retry on transient failures."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        mock_server = MagicMock()
        # Fail twice, then succeed
        mock_server.sendmail.side_effect = [
            smtplib.SMTPServerDisconnected("Connection lost"),
            smtplib.SMTPServerDisconnected("Connection lost again"),
            None,  # Success
        ]
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is True
            assert mock_server.sendmail.call_count == 3
            assert len(retry_queue.get_all()) == 0

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_queues_after_max_retries(self, mock_smtp):
        """Should queue email after exhausting all retries."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPServerDisconnected("Always fail")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 2  # Will try 3 times total
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_body="<p>Test</p>"
            )

            assert result is False
            assert mock_server.sendmail.call_count == 3  # Initial + 2 retries
            assert len(retry_queue.get_all()) == 1

            queued = retry_queue.get_all()[0]
            assert queued.to_email == "recipient@test.com"
            assert queued.subject == "Test Subject"
            assert queued.status == EmailStatus.RETRY_SCHEDULED
            assert queued.last_error is not None
            assert queued.next_retry_at is not None

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_no_retry_on_permanent_failure(self, mock_smtp):
        """Should not retry on permanent failures like invalid recipient."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPRecipientsRefused(
            {"bad@example.com": (550, "User unknown")}
        )
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="bad@example.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is False
            # Should only try once for permanent failure
            assert mock_server.sendmail.call_count == 1
            # Still queued for record-keeping, but won't be retried
            assert len(retry_queue.get_all()) == 1


class TestEmailServiceProcessQueue:
    """Tests for processing the retry queue."""

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_process_empty_queue(self, mock_smtp):
        """Should handle empty queue gracefully."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        results = email_service.process_retry_queue()

        assert results == {"processed": 0, "succeeded": 0, "failed": 0}

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_process_queue_success(self, mock_smtp):
        """Should successfully process ready retries."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        # Add a ready-to-retry entry
        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
        )
        entry.status = EmailStatus.RETRY_SCHEDULED
        entry.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
        entry.attempt_count = 1
        retry_queue.add(entry)

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
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 1.0
            mock_settings.email_retry_max_delay = 60.0
            mock_settings.email_retry_exponential_base = 2.0

            results = email_service.process_retry_queue()

            assert results["processed"] == 1
            assert results["succeeded"] == 1
            assert results["failed"] == 0
            assert len(retry_queue.get_all()) == 0

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_process_queue_reschedules_failure(self, mock_smtp):
        """Should reschedule failed retry attempts."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
        )
        entry.status = EmailStatus.RETRY_SCHEDULED
        entry.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
        entry.attempt_count = 1
        retry_queue.add(entry)

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPServerDisconnected("Failed")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 1.0
            mock_settings.email_retry_max_delay = 60.0
            mock_settings.email_retry_exponential_base = 2.0

            results = email_service.process_retry_queue()

            assert results["processed"] == 1
            assert results["succeeded"] == 0
            assert results["failed"] == 0  # Not permanently failed yet

            # Entry should still be in queue with updated next_retry_at
            all_entries = retry_queue.get_all()
            assert len(all_entries) == 1
            assert all_entries[0].status == EmailStatus.RETRY_SCHEDULED
            assert all_entries[0].attempt_count == 2
            assert all_entries[0].next_retry_at > datetime.utcnow()

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_process_queue_marks_permanent_failure(self, mock_smtp):
        """Should mark as permanently failed after max attempts."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        entry = EmailQueueEntry.create(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
        )
        entry.status = EmailStatus.RETRY_SCHEDULED
        entry.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
        entry.attempt_count = 8  # Already at max (3 * 3 - 1)
        retry_queue.add(entry)

        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPServerDisconnected("Failed")
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 1.0
            mock_settings.email_retry_max_delay = 60.0
            mock_settings.email_retry_exponential_base = 2.0

            results = email_service.process_retry_queue()

            assert results["processed"] == 1
            assert results["succeeded"] == 0
            assert results["failed"] == 1

            all_entries = retry_queue.get_all()
            assert len(all_entries) == 1
            assert all_entries[0].status == EmailStatus.FAILED


class TestEmailServiceQueueStatus:
    """Tests for queue status reporting."""

    def test_get_queue_status_empty(self):
        """Should report empty queue correctly."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        status = email_service.get_queue_status()

        assert status == {
            "total": 0,
            "pending_retry": 0,
            "failed": 0,
            "scheduled": 0,
        }

    def test_get_queue_status_with_entries(self):
        """Should report queue status correctly."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        # Add various entries
        scheduled = EmailQueueEntry.create(
            to_email="scheduled@example.com",
            subject="Scheduled",
            html_body="<p>Scheduled</p>",
        )
        scheduled.status = EmailStatus.RETRY_SCHEDULED
        scheduled.next_retry_at = datetime.utcnow() + timedelta(hours=1)
        retry_queue.add(scheduled)

        ready = EmailQueueEntry.create(
            to_email="ready@example.com",
            subject="Ready",
            html_body="<p>Ready</p>",
        )
        ready.status = EmailStatus.RETRY_SCHEDULED
        ready.next_retry_at = datetime.utcnow() - timedelta(minutes=5)
        retry_queue.add(ready)

        failed = EmailQueueEntry.create(
            to_email="failed@example.com",
            subject="Failed",
            html_body="<p>Failed</p>",
        )
        failed.status = EmailStatus.FAILED
        retry_queue.add(failed)

        status = email_service.get_queue_status()

        assert status["total"] == 3
        assert status["pending_retry"] == 1  # Only 'ready' is pending
        assert status["failed"] == 1
        assert status["scheduled"] == 2  # Both scheduled entries


class TestBuildMimeMessage:
    """Tests for MIME message building."""

    def test_build_mime_message_basic(self):
        """Should build basic MIME message."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_from_address = "sender@test.com"
            mock_settings.email_from_name = "Sender"

            msg = email_service._build_mime_message(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_body="<p>HTML body</p>",
            )

            assert msg["Subject"] == "Test Subject"
            assert msg["To"] == "recipient@test.com"
            assert "sender@test.com" in msg["From"]

    def test_build_mime_message_with_text_body(self):
        """Should include text body when provided."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_from_address = "sender@test.com"
            mock_settings.email_from_name = "Sender"

            msg = email_service._build_mime_message(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>HTML</p>",
                text_body="Plain text",
            )

            # Message should have multiple parts
            assert msg.is_multipart()

    def test_build_mime_message_with_attachments(self):
        """Should include attachments when provided."""
        mock_db = Mock()
        email_service = EmailService(mock_db)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_from_address = "sender@test.com"
            mock_settings.email_from_name = "Sender"

            msg = email_service._build_mime_message(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>HTML</p>",
                attachments=[("file.pdf", b"PDF content")],
            )

            assert msg.is_multipart()
            # Should have at least 2 parts (HTML + attachment)
            parts = list(msg.walk())
            assert len(parts) >= 2


# ============================================================================
# Edge Case Tests: Email Service Failures
# ============================================================================

class TestEmailConnectionFailures:
    """Tests for various email connection failure scenarios."""

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_smtp_connection_timeout(self, mock_smtp):
        """Should handle SMTP connection timeout gracefully."""
        mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Connection timed out")

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 2
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is False
            # Should be queued for retry
            assert len(retry_queue.get_all()) == 1

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_smtp_authentication_failure_retries_and_fails(self, mock_smtp):
        """Authentication failure should retry (as SMTPException) and eventually fail."""
        mock_server = MagicMock()
        # Authentication error during sendmail is caught and retried
        mock_server.sendmail.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "baduser"
            mock_settings.smtp_password = "badpass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 2
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is False
            # Should have made all attempts (initial + retries)
            assert mock_server.sendmail.call_count == 3

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_smtp_data_error_retries(self, mock_smtp):
        """Should retry on transient SMTP data errors."""
        mock_server = MagicMock()
        # Fail twice with data error, then succeed
        mock_server.sendmail.side_effect = [
            smtplib.SMTPDataError(451, "Temporary failure"),
            smtplib.SMTPDataError(451, "Temporary failure again"),
            None,  # Success
        ]
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 3
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is True
            assert mock_server.sendmail.call_count == 3

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_smtp_sender_refused_retries_and_fails(self, mock_smtp):
        """Sender refused error is treated as SMTP error and retried."""
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPSenderRefused(
            550, "Sender not allowed", "test@test.com"
        )
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 2
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            # SMTPSenderRefused inherits from SMTPException, so it's retried
            assert result is False
            # Should retry (initial + 2 retries)
            assert mock_server.sendmail.call_count == 3

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_smtp_helo_error_retries_and_fails(self, mock_smtp):
        """HELO error during sendmail is retried and eventually fails."""
        mock_server = MagicMock()
        # Simulate HELO error during sendmail (connection issues)
        mock_server.sendmail.side_effect = smtplib.SMTPHeloError(500, "HELO failed")
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 2
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is False
            # Should retry (initial + 2 retries)
            assert mock_server.sendmail.call_count == 3

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_generic_smtp_exception(self, mock_smtp):
        """Should handle generic SMTP exceptions."""
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = smtplib.SMTPException("Unknown SMTP error")
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 1
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is False

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_socket_error_during_send(self, mock_smtp):
        """Should handle socket errors during email send."""
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = OSError("Network unreachable")
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 2
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="Test",
                html_body="<p>Test</p>"
            )

            assert result is False
            # Should have queued for retry on transient network error
            assert len(retry_queue.get_all()) >= 1


class TestEmailEdgeCases:
    """Tests for email edge cases and boundary conditions."""

    def test_queue_status_with_mixed_entries(self):
        """Should correctly count different entry states."""
        mock_db = Mock()
        retry_queue = EmailRetryQueue()
        email_service = EmailService(mock_db, retry_queue=retry_queue)

        # Add entries with different states
        for i in range(3):
            entry = EmailQueueEntry.create(
                to_email=f"scheduled{i}@example.com",
                subject="Scheduled",
                html_body="<p>Scheduled</p>",
            )
            entry.status = EmailStatus.RETRY_SCHEDULED
            entry.next_retry_at = datetime.utcnow() + timedelta(hours=1)
            retry_queue.add(entry)

        for i in range(2):
            entry = EmailQueueEntry.create(
                to_email=f"failed{i}@example.com",
                subject="Failed",
                html_body="<p>Failed</p>",
            )
            entry.status = EmailStatus.FAILED
            retry_queue.add(entry)

        # Add one ready for retry
        ready_entry = EmailQueueEntry.create(
            to_email="ready@example.com",
            subject="Ready",
            html_body="<p>Ready</p>",
        )
        ready_entry.status = EmailStatus.RETRY_SCHEDULED
        ready_entry.next_retry_at = datetime.utcnow() - timedelta(minutes=5)
        retry_queue.add(ready_entry)

        status = email_service.get_queue_status()

        assert status["total"] == 6
        assert status["pending_retry"] == 1
        assert status["failed"] == 2
        assert status["scheduled"] == 4  # 3 future + 1 past

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_email_with_special_characters_in_subject(self, mock_smtp):
        """Should handle special characters in subject line."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        email_service = EmailService(mock_db)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_enabled = True
            mock_settings.smtp_server = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.email_from_address = "test@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_max_retries = 1
            mock_settings.email_retry_base_delay = 0.01
            mock_settings.email_retry_max_delay = 0.1
            mock_settings.email_retry_exponential_base = 2.0

            # Subject with emoji, unicode, and special chars
            result = email_service._send_email(
                to_email="recipient@test.com",
                subject="🍽️ Your Meal Plan: Rösti & Jalapeño!",
                html_body="<p>Test</p>"
            )

            assert result is True
            assert mock_server.sendmail.called

    @patch('backend.services.email_service.smtplib.SMTP')
    def test_email_with_large_attachment(self, mock_smtp):
        """Should handle large attachments."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        mock_db = Mock()
        email_service = EmailService(mock_db)

        with patch('backend.services.email_service.settings') as mock_settings:
            mock_settings.email_from_address = "sender@test.com"
            mock_settings.email_from_name = "Sender"

            # 1MB attachment
            large_content = b"x" * (1024 * 1024)

            msg = email_service._build_mime_message(
                to_email="recipient@test.com",
                subject="Large Attachment",
                html_body="<p>See attachment</p>",
                attachments=[("large_file.bin", large_content)],
            )

            assert msg.is_multipart()

    def test_backoff_delay_never_negative(self):
        """Backoff delay should never be negative regardless of input."""
        # Test various edge cases
        assert calculate_backoff_delay(0, base_delay=0.1) >= 0
        assert calculate_backoff_delay(100, base_delay=0.1) >= 0
        assert calculate_backoff_delay(0, base_delay=0.0) >= 0

    def test_backoff_delay_at_extreme_attempts(self):
        """Should cap delay even at very high attempt numbers."""
        delay = calculate_backoff_delay(
            attempt=1000,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0
        )
        assert delay == 60.0  # Should be capped at max_delay
