"""
Email service for PrepPilot notifications.

Handles sending adaptive plan summaries and reminders to users.
Includes retry logic with exponential backoff for failed deliveries.
"""
import html
import logging
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from enum import Enum
from typing import Optional, List, Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import User, MealPlan
from backend.models.schemas import AdaptiveEngineOutput, FridgeItem
from backend.services.pdf_service import PDFService


logger = logging.getLogger(__name__)


class EmailStatus(str, Enum):
    """Status of an email in the retry queue."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"


@dataclass
class EmailQueueEntry:
    """Represents an email in the retry queue."""
    id: UUID
    to_email: str
    subject: str
    html_body: str
    text_body: Optional[str]
    attachments: Optional[List[tuple]]
    status: EmailStatus
    attempt_count: int
    created_at: datetime
    next_retry_at: Optional[datetime]
    last_error: Optional[str]

    @classmethod
    def create(
        cls,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> "EmailQueueEntry":
        """Create a new queue entry."""
        return cls(
            id=uuid4(),
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            attachments=attachments,
            status=EmailStatus.PENDING,
            attempt_count=0,
            created_at=datetime.utcnow(),
            next_retry_at=None,
            last_error=None,
        )


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
) -> float:
    """
    Calculate delay for exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Multiplier for exponential growth

    Returns:
        Delay in seconds
    """
    delay = base_delay * (exponential_base ** attempt)
    return min(delay, max_delay)


class EmailRetryQueue:
    """
    In-memory queue for failed emails awaiting retry.

    This can be extended to use a persistent store (Redis, database)
    for production deployments requiring durability across restarts.
    """

    def __init__(self):
        self._queue: dict[UUID, EmailQueueEntry] = {}

    def add(self, entry: EmailQueueEntry) -> None:
        """Add an email to the retry queue."""
        self._queue[entry.id] = entry
        logger.info(f"Email queued for retry: {entry.id} to {entry.to_email}")

    def remove(self, entry_id: UUID) -> Optional[EmailQueueEntry]:
        """Remove and return an email from the queue."""
        return self._queue.pop(entry_id, None)

    def get_pending_retries(self) -> List[EmailQueueEntry]:
        """Get emails ready for retry (next_retry_at <= now)."""
        now = datetime.utcnow()
        return [
            entry for entry in self._queue.values()
            if entry.status == EmailStatus.RETRY_SCHEDULED
            and entry.next_retry_at
            and entry.next_retry_at <= now
        ]

    def get_all(self) -> List[EmailQueueEntry]:
        """Get all emails in the queue."""
        return list(self._queue.values())

    def get_failed(self) -> List[EmailQueueEntry]:
        """Get all permanently failed emails."""
        return [
            entry for entry in self._queue.values()
            if entry.status == EmailStatus.FAILED
        ]

    def clear(self) -> int:
        """Clear all entries and return count removed."""
        count = len(self._queue)
        self._queue.clear()
        return count


# Global retry queue instance
email_retry_queue = EmailRetryQueue()


class EmailService:
    """
    Service for sending email notifications to users.

    Handles sending meal plan summaries, adaptation alerts, and expiring item
    notifications. Includes retry logic with exponential backoff for failed deliveries.
    """

    def __init__(self, db: Session, retry_queue: Optional[EmailRetryQueue] = None):
        """
        Initialize the email service.

        Args:
            db: SQLAlchemy database session for persistence operations.
            retry_queue: Optional custom retry queue. Uses global queue if not provided.
        """
        self.db = db
        self._retry_queue = retry_queue or email_retry_queue

    @property
    def retry_queue(self) -> EmailRetryQueue:
        """Access the retry queue."""
        return self._retry_queue

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """
        Create and authenticate SMTP connection.

        Returns:
            Configured SMTP connection with TLS enabled.

        Raises:
            smtplib.SMTPException: If connection or authentication fails.
        """
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()

        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)

        return server

    def _build_mime_message(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> MIMEMultipart:
        """
        Build a MIME message for sending.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            html_body: HTML content of the email.
            text_body: Optional plain text fallback content.
            attachments: Optional list of (filename, bytes) tuples.

        Returns:
            Configured MIMEMultipart message ready for sending.
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings.email_from_name} <{settings.email_from_address}>"
        msg['To'] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))

        msg.attach(MIMEText(html_body, 'html'))

        if attachments:
            for filename, file_bytes in attachments:
                part = MIMEApplication(file_bytes, Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'
                msg.attach(part)

        return msg

    def _attempt_send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Attempt to send an email once.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            msg = self._build_mime_message(
                to_email, subject, html_body, text_body, attachments
            )
            with self._create_smtp_connection() as server:
                server.sendmail(
                    settings.email_from_address,
                    to_email,
                    msg.as_string()
                )
            return True, None
        except smtplib.SMTPRecipientsRefused as e:
            # Don't retry for invalid recipients
            return False, f"Recipient refused: {e}"
        except smtplib.SMTPDataError as e:
            # Message rejected, may be temporary
            return False, f"SMTP data error: {e}"
        except smtplib.SMTPServerDisconnected as e:
            # Connection lost, retry-able
            return False, f"Server disconnected: {e}"
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        attachments: Optional[List[tuple]] = None,
    ) -> bool:
        """
        Send an email to a user with retry logic.

        Uses exponential backoff for transient failures.
        Failed emails after max retries are added to the retry queue.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text fallback (optional)
            attachments: List of (filename, bytes) tuples

        Returns:
            True if sent successfully on first attempt or any retry
        """
        if not settings.email_enabled:
            logger.info(f"Email disabled - would send '{subject}' to {to_email}")
            return True

        max_retries = settings.email_max_retries
        last_error: Optional[str] = None

        for attempt in range(max_retries + 1):
            success, error = self._attempt_send(
                to_email, subject, html_body, text_body, attachments
            )

            if success:
                if attempt > 0:
                    logger.info(
                        f"Email sent to {to_email} on attempt {attempt + 1}: {subject}"
                    )
                else:
                    logger.info(f"Email sent to {to_email}: {subject}")
                return True

            last_error = error
            logger.warning(
                f"Email attempt {attempt + 1}/{max_retries + 1} failed for {to_email}: {error}"
            )

            # Check if this is a permanent failure (don't retry)
            if error and "Recipient refused" in error:
                logger.error(f"Permanent failure for {to_email}: {error}")
                break

            # Wait before next retry (except on last attempt)
            if attempt < max_retries:
                delay = calculate_backoff_delay(
                    attempt,
                    base_delay=settings.email_retry_base_delay,
                    max_delay=settings.email_retry_max_delay,
                    exponential_base=settings.email_retry_exponential_base,
                )
                logger.info(f"Waiting {delay:.1f}s before retry...")
                time.sleep(delay)

        # All retries exhausted - queue for later retry
        logger.error(
            f"Failed to send email to {to_email} after {max_retries + 1} attempts: {last_error}"
        )
        self._queue_for_retry(
            to_email, subject, html_body, text_body, attachments, last_error
        )
        return False

    def _queue_for_retry(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str],
        attachments: Optional[List[tuple]],
        last_error: Optional[str],
    ) -> EmailQueueEntry:
        """Queue a failed email for later retry."""
        entry = EmailQueueEntry.create(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            attachments=attachments,
        )
        entry.status = EmailStatus.RETRY_SCHEDULED
        entry.attempt_count = settings.email_max_retries + 1
        entry.last_error = last_error
        # Schedule next retry with longer delay
        entry.next_retry_at = datetime.utcnow() + timedelta(
            seconds=calculate_backoff_delay(
                entry.attempt_count,
                base_delay=settings.email_retry_base_delay,
                max_delay=settings.email_retry_max_delay * 10,  # Longer for queued
                exponential_base=settings.email_retry_exponential_base,
            )
        )
        self._retry_queue.add(entry)
        return entry

    def process_retry_queue(self) -> dict:
        """
        Process pending emails in the retry queue.

        Returns:
            Dict with counts of processed, succeeded, failed emails
        """
        pending = self._retry_queue.get_pending_retries()
        results = {"processed": 0, "succeeded": 0, "failed": 0}

        for entry in pending:
            results["processed"] += 1
            entry.status = EmailStatus.SENDING
            entry.attempt_count += 1

            success, error = self._attempt_send(
                entry.to_email,
                entry.subject,
                entry.html_body,
                entry.text_body,
                entry.attachments,
            )

            if success:
                entry.status = EmailStatus.SENT
                self._retry_queue.remove(entry.id)
                results["succeeded"] += 1
                logger.info(f"Retry succeeded for {entry.to_email}: {entry.subject}")
            else:
                entry.last_error = error
                # Check if we've exceeded maximum total attempts
                if entry.attempt_count >= settings.email_max_retries * 3:
                    entry.status = EmailStatus.FAILED
                    results["failed"] += 1
                    logger.error(
                        f"Email permanently failed for {entry.to_email}: {error}"
                    )
                else:
                    entry.status = EmailStatus.RETRY_SCHEDULED
                    entry.next_retry_at = datetime.utcnow() + timedelta(
                        seconds=calculate_backoff_delay(
                            entry.attempt_count,
                            base_delay=settings.email_retry_base_delay,
                            max_delay=settings.email_retry_max_delay * 10,
                            exponential_base=settings.email_retry_exponential_base,
                        )
                    )
                    logger.warning(
                        f"Retry {entry.attempt_count} failed for {entry.to_email}, "
                        f"next retry at {entry.next_retry_at}"
                    )

        return results

    def get_queue_status(self) -> dict:
        """Get current status of the retry queue."""
        all_entries = self._retry_queue.get_all()
        return {
            "total": len(all_entries),
            "pending_retry": len(self._retry_queue.get_pending_retries()),
            "failed": len(self._retry_queue.get_failed()),
            "scheduled": len([
                e for e in all_entries
                if e.status == EmailStatus.RETRY_SCHEDULED
            ]),
        }

    def send_adaptation_summary(
        self,
        user: User,
        plan: MealPlan,
        adaptation_output: AdaptiveEngineOutput,
        include_pdf: bool = True,
    ) -> bool:
        """
        Send email with adaptation summary after plan changes.

        Args:
            user: User to send to
            plan: Updated meal plan
            adaptation_output: Adaptive engine output with changes
            include_pdf: Whether to attach catch-up PDF

        Returns:
            True if sent successfully
        """
        subject = "Your PrepPilot meal plan has been updated"

        # Build HTML email
        html_body = self._build_adaptation_email_html(user, adaptation_output)

        # Generate PDF attachment if requested
        attachments = []
        if include_pdf:
            pdf_service = PDFService(self.db)
            from backend.services.fridge_service import FridgeService
            fridge_service = FridgeService(self.db)
            fridge_state = fridge_service.get_fridge_state(user)

            pdf_bytes = pdf_service.generate_catch_up_pdf(
                plan=plan,
                adaptation_output=adaptation_output,
                fridge_state=fridge_state,
            )
            attachments.append(("preppilot_catch_up_plan.pdf", pdf_bytes))

        return self._send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            attachments=attachments if attachments else None,
        )

    def send_expiring_items_alert(
        self,
        user: User,
        expiring_items: List[FridgeItem],
    ) -> bool:
        """
        Send alert about ingredients expiring soon.

        Args:
            user: User to send to
            expiring_items: List of expiring fridge items

        Returns:
            True if sent successfully
        """
        if not expiring_items:
            return True

        subject = f"PrepPilot: {len(expiring_items)} ingredients expiring soon"

        html_body = self._build_expiring_items_email_html(user, expiring_items)

        return self._send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
        )

    def send_weekly_plan_summary(
        self,
        user: User,
        plan: MealPlan,
    ) -> bool:
        """
        Send weekly meal plan summary with PDF attachment.

        Args:
            user: User to send to
            plan: Meal plan

        Returns:
            True if sent successfully
        """
        subject = "Your PrepPilot meal plan is ready"

        # Generate PDF
        pdf_service = PDFService(self.db)
        pdf_bytes = pdf_service.generate_meal_plan_pdf(plan)

        html_body = self._build_weekly_summary_email_html(user, plan)

        return self._send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            attachments=[("preppilot_meal_plan.pdf", pdf_bytes)],
        )

    def _build_adaptation_email_html(
        self,
        user: User,
        adaptation_output: AdaptiveEngineOutput,
    ) -> str:
        """
        Build HTML email for adaptation summary.

        Args:
            user: User to personalize the email for.
            adaptation_output: Adaptive engine output with plan changes.

        Returns:
            HTML string for the email body.
        """
        # Escape user-controlled data to prevent XSS
        user_name = html.escape(user.full_name or user.email.split('@')[0])

        # Build adaptation list
        adaptations_html = ""
        for reason in adaptation_output.adaptation_summary:
            safe_reason = html.escape(reason.reason)
            adaptations_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                    {reason.affected_date.strftime('%A, %b %d')}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                    {safe_reason}
                </td>
            </tr>
            """

        # Build priority ingredients
        priority_html = ""
        if adaptation_output.priority_ingredients:
            items = "".join([f"<li>{html.escape(item)}</li>" for item in adaptation_output.priority_ingredients])
            priority_html = f"""
            <h3 style="color: #D2691E;">Use These First</h3>
            <p>These ingredients need to be used soon:</p>
            <ul>{items}</ul>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2D5A27; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #fff; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #2D5A27; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PrepPilot</h1>
                    <p>Your plan has been updated</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>

                    <p>We noticed you missed some meal prep — no stress! We've adjusted your plan so nothing goes to waste.</p>

                    <div class="highlight">
                        <h3>What Changed</h3>
                        <table>
                            {adaptations_html}
                        </table>
                    </div>

                    {priority_html}

                    <div class="highlight">
                        <p><strong>Estimated catch-up time:</strong> {adaptation_output.estimated_recovery_time_minutes} minutes</p>
                    </div>

                    <p>Check out your updated plan in the attached PDF or open the app to see the details.</p>

                    <p style="text-align: center; margin-top: 20px;">
                        <a href="#" class="btn">Open PrepPilot</a>
                    </p>
                </div>
                <div class="footer">
                    <p>PrepPilot — Plans that adapt to your life</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_expiring_items_email_html(
        self,
        user: User,
        expiring_items: List[FridgeItem],
    ) -> str:
        """
        Build HTML email for expiring items alert.

        Args:
            user: User to personalize the email for.
            expiring_items: List of fridge items expiring soon.

        Returns:
            HTML string for the email body.
        """
        # Escape user-controlled data to prevent XSS
        user_name = html.escape(user.full_name or user.email.split('@')[0])

        items_html = ""
        for item in expiring_items:
            urgency = "🔴" if item.days_remaining <= 1 else "🟡"
            safe_ingredient_name = html.escape(item.ingredient_name)
            safe_quantity = html.escape(item.quantity)
            items_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                    {urgency} {safe_ingredient_name}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                    {safe_quantity}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">
                    {item.days_remaining} day{"s" if item.days_remaining != 1 else ""}
                </td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #D2691E; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #fff; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                table {{ width: 100%; border-collapse: collapse; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Heads Up!</h1>
                    <p>Some ingredients need attention</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>

                    <p>The following ingredients in your fridge are expiring soon:</p>

                    <div class="highlight">
                        <table>
                            <tr style="background: #f5f5f5;">
                                <th style="padding: 8px; text-align: left;">Ingredient</th>
                                <th style="padding: 8px; text-align: left;">Quantity</th>
                                <th style="padding: 8px; text-align: left;">Expires In</th>
                            </tr>
                            {items_html}
                        </table>
                    </div>

                    <p>Open PrepPilot to find recipes that use these ingredients!</p>
                </div>
                <div class="footer">
                    <p>PrepPilot — Plans that adapt to your life</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _build_weekly_summary_email_html(
        self,
        user: User,
        plan: MealPlan,
    ) -> str:
        """
        Build HTML email for weekly plan summary.

        Args:
            user: User to personalize the email for.
            plan: Meal plan to summarize.

        Returns:
            HTML string for the email body.
        """
        # Escape user-controlled data to prevent XSS
        user_name = html.escape(user.full_name or user.email.split('@')[0])

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2D5A27; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px; }}
                .highlight {{ background: #fff; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background: #2D5A27; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>PrepPilot</h1>
                    <p>Your meal plan is ready!</p>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>

                    <p>Your meal plan for <strong>{plan.start_date.strftime('%B %d')} - {plan.end_date.strftime('%B %d')}</strong> is attached.</p>

                    <div class="highlight">
                        <p>Your plan includes:</p>
                        <ul>
                            <li>Daily meal schedule</li>
                            <li>Shopping list grouped by category</li>
                            <li>Optimized prep timeline</li>
                        </ul>
                    </div>

                    <p>Print it out for easy reference in the kitchen!</p>

                    <p style="text-align: center; margin-top: 20px;">
                        <a href="#" class="btn">Open PrepPilot</a>
                    </p>
                </div>
                <div class="footer">
                    <p>PrepPilot — Plans that adapt to your life</p>
                </div>
            </div>
        </body>
        </html>
        """
