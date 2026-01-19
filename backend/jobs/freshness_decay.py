"""
Background job for daily freshness decay.

This job runs once per day to decay the freshness of all fridge items
for all users.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
import logging

from backend.db.database import SessionLocal
from backend.db.models import User, FridgeItem
from backend.config import settings
from backend.services.email_service import EmailService
from backend.services.fridge_service import FridgeService
from backend.models.schemas import FridgeItem as FridgeItemSchema

logger = logging.getLogger(__name__)


def decay_all_fridge_items():
    """
    Decay freshness for all fridge items across all users.

    This function:
    1. Gets all users
    2. For each user, decays their fridge items by 1 day
    3. Logs the results
    """
    db: Session = SessionLocal()

    try:
        logger.info("Starting daily freshness decay job...")

        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()

        total_items_updated = 0
        users_processed = 0

        for user in users:
            # Get all fridge items for this user
            items = db.query(FridgeItem).filter(FridgeItem.user_id == user.id).all()

            if not items:
                continue

            items_updated = 0
            for item in items:
                # Decay freshness by 1 day
                item.days_remaining = max(0, item.days_remaining - 1)
                items_updated += 1

            total_items_updated += items_updated
            users_processed += 1

            logger.info(f"Decayed {items_updated} items for user {user.email}")

        # Commit all changes
        db.commit()

        logger.info(
            f"Freshness decay job completed. "
            f"Processed {users_processed} users, updated {total_items_updated} items."
        )

    except Exception as e:
        logger.error(f"Error in freshness decay job: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def remove_expired_items():
    """
    Remove items that have expired (days_remaining = 0 for more than 7 days).

    This is a cleanup job to prevent the database from growing indefinitely.
    """
    db: Session = SessionLocal()

    try:
        logger.info("Starting expired items cleanup job...")

        # Delete items with 0 days remaining
        # In a real system, you might want to keep them for a grace period
        deleted_count = db.query(FridgeItem).filter(
            FridgeItem.days_remaining == 0
        ).delete(synchronize_session=False)

        db.commit()

        logger.info(f"Removed {deleted_count} expired items from database.")

    except Exception as e:
        logger.error(f"Error in expired items cleanup job: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def send_expiring_item_alerts():
    """
    Send email alerts to users with ingredients expiring within 2 days.

    This job runs daily to remind users about soon-to-expire ingredients.
    """
    if not settings.email_enabled:
        logger.info("Email disabled - skipping expiring item alerts")
        return

    db: Session = SessionLocal()

    try:
        logger.info("Starting expiring item alerts job...")

        users = db.query(User).filter(User.is_active == True).all()
        emails_sent = 0

        email_service = EmailService(db)
        fridge_service = FridgeService(db)

        for user in users:
            # Get items expiring within 2 days
            expiring_items = fridge_service.get_expiring_items(user, days_threshold=2)

            if not expiring_items:
                continue

            # Convert to schema
            schema_items = [
                FridgeItemSchema(
                    ingredient_name=item.ingredient_name,
                    quantity=item.quantity,
                    days_remaining=item.days_remaining,
                    added_date=item.added_date,
                    original_freshness_days=item.original_freshness_days,
                )
                for item in expiring_items
            ]

            # Send email
            if email_service.send_expiring_items_alert(user, schema_items):
                emails_sent += 1
                logger.info(f"Sent expiring items alert to {user.email}")

        logger.info(f"Expiring item alerts job completed. Sent {emails_sent} emails.")

    except Exception as e:
        logger.error(f"Error in expiring item alerts job: {str(e)}")
        raise
    finally:
        db.close()


def setup_scheduler() -> BackgroundScheduler:
    """
    Set up the background scheduler with daily freshness decay job.

    Returns:
        Configured scheduler instance
    """
    scheduler = BackgroundScheduler()

    # Schedule freshness decay job to run daily at configured hour (default midnight)
    scheduler.add_job(
        decay_all_fridge_items,
        trigger=CronTrigger(hour=settings.freshness_decay_hour, minute=0),
        id='freshness_decay',
        name='Daily freshness decay',
        replace_existing=True,
    )

    logger.info(
        f"Scheduled freshness decay job to run daily at "
        f"{settings.freshness_decay_hour}:00"
    )

    # Optional: Schedule cleanup job to run weekly on Sunday at 2 AM
    scheduler.add_job(
        remove_expired_items,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='expired_items_cleanup',
        name='Weekly expired items cleanup',
        replace_existing=True,
    )

    logger.info("Scheduled expired items cleanup job to run weekly on Sunday at 2:00 AM")

    # Schedule expiring item email alerts to run daily at 8 AM
    scheduler.add_job(
        send_expiring_item_alerts,
        trigger=CronTrigger(hour=8, minute=0),
        id='expiring_item_alerts',
        name='Daily expiring item alerts',
        replace_existing=True,
    )

    logger.info("Scheduled expiring item alerts job to run daily at 8:00 AM")

    return scheduler


def start_scheduler():
    """
    Start the background scheduler.

    Only starts if ENABLE_BACKGROUND_JOBS is True in settings.
    """
    if not settings.enable_background_jobs:
        logger.info("Background jobs are disabled in settings")
        return None

    scheduler = setup_scheduler()
    scheduler.start()

    logger.info("Background scheduler started successfully")

    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler):
    """
    Stop the background scheduler gracefully.

    Args:
        scheduler: The scheduler instance to stop
    """
    if scheduler:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")
