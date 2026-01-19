"""
Fridge management service with database persistence.
"""
from datetime import date
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from backend.db.models import User, FridgeItem as DBFridgeItem
from backend.models.schemas import FridgeItem, FridgeState
from backend.engine.quantity_utils import parse_quantity, combine_quantities


class FridgeService:
    """
    Service for fridge inventory operations.

    Manages user fridge items including adding, updating, removing,
    and tracking freshness/expiration of ingredients.
    """

    def __init__(self, db: Session):
        """
        Initialize the fridge service.

        Args:
            db: SQLAlchemy database session for persistence operations.
        """
        self.db = db

    def get_fridge_state(self, user: User) -> FridgeState:
        """
        Get current fridge state for a user.

        Args:
            user: User to get fridge state for

        Returns:
            FridgeState with all items
        """
        db_items = (
            self.db.query(DBFridgeItem)
            .filter(DBFridgeItem.user_id == user.id)
            .all()
        )

        items = [
            FridgeItem(
                ingredient_name=item.ingredient_name,
                quantity=item.quantity,
                days_remaining=item.days_remaining,
                added_date=item.added_date,
                original_freshness_days=item.original_freshness_days,
            )
            for item in db_items
        ]

        return FridgeState(
            user_id=user.id,
            items=items,
        )

    def add_item(
        self,
        user: User,
        ingredient_name: str,
        quantity: str,
        freshness_days: int,
    ) -> DBFridgeItem:
        """
        Add an item to the fridge. If item exists, combine quantities and use better freshness.

        Args:
            user: User who owns the fridge
            ingredient_name: Name of the ingredient
            quantity: Quantity string (e.g., "500g")
            freshness_days: Days until expiration

        Returns:
            Created or updated FridgeItem
        """
        # Check if item already exists
        existing = (
            self.db.query(DBFridgeItem)
            .filter(
                DBFridgeItem.user_id == user.id,
                DBFridgeItem.ingredient_name == ingredient_name.lower(),
            )
            .first()
        )

        if existing:
            # Combine quantities
            combined_qty = combine_quantities([existing.quantity, quantity])
            # Use the fresher item's freshness (max of the two)
            new_freshness = max(existing.days_remaining, freshness_days)

            existing.quantity = combined_qty
            existing.days_remaining = new_freshness
            existing.original_freshness_days = max(existing.original_freshness_days, freshness_days)

            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new item
        new_item = DBFridgeItem(
            user_id=user.id,
            ingredient_name=ingredient_name.lower(),
            quantity=quantity,
            days_remaining=freshness_days,
            added_date=date.today(),
            original_freshness_days=freshness_days,
        )

        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)

        return new_item

    def add_items_bulk(
        self,
        user: User,
        items: List[dict],
    ) -> List[DBFridgeItem]:
        """
        Add multiple items to the fridge.

        Args:
            user: User who owns the fridge
            items: List of dicts with keys: ingredient_name, quantity, freshness_days

        Returns:
            List of created or updated FridgeItems
        """
        created_items = []
        for item_data in items:
            item = self.add_item(
                user=user,
                ingredient_name=item_data["ingredient_name"],
                quantity=item_data["quantity"],
                freshness_days=item_data["freshness_days"],
            )
            created_items.append(item)

        return created_items

    def update_item(
        self,
        user: User,
        item_id: UUID,
        quantity: Optional[str] = None,
        days_remaining: Optional[int] = None,
    ) -> Optional[DBFridgeItem]:
        """
        Update a fridge item's quantity and/or freshness.

        Args:
            user: User who owns the fridge
            item_id: UUID of the item to update
            quantity: New quantity string (optional)
            days_remaining: New days remaining (optional)

        Returns:
            Updated FridgeItem or None if not found
        """
        item = (
            self.db.query(DBFridgeItem)
            .filter(
                DBFridgeItem.id == item_id,
                DBFridgeItem.user_id == user.id,
            )
            .first()
        )

        if not item:
            return None

        if quantity is not None:
            item.quantity = quantity

        if days_remaining is not None:
            item.days_remaining = days_remaining
            # Update original_freshness_days if new value is higher
            # This keeps the percentage calculation meaningful
            if days_remaining > item.original_freshness_days:
                item.original_freshness_days = days_remaining

        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_item(
        self,
        user: User,
        item_id: UUID,
    ) -> bool:
        """
        Remove an item from the fridge.

        Args:
            user: User who owns the fridge
            item_id: UUID of the item to remove

        Returns:
            True if deleted, False if not found
        """
        item = (
            self.db.query(DBFridgeItem)
            .filter(
                DBFridgeItem.id == item_id,
                DBFridgeItem.user_id == user.id,
            )
            .first()
        )

        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        return True

    def remove_item_by_name(
        self,
        user: User,
        ingredient_name: str,
    ) -> bool:
        """
        Remove an item from the fridge by ingredient name.

        Args:
            user: User who owns the fridge
            ingredient_name: Name of the ingredient to remove

        Returns:
            True if deleted, False if not found
        """
        item = (
            self.db.query(DBFridgeItem)
            .filter(
                DBFridgeItem.user_id == user.id,
                DBFridgeItem.ingredient_name == ingredient_name.lower(),
            )
            .first()
        )

        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        return True

    def decay_freshness(self, user: User, days: int = 1) -> int:
        """
        Decay freshness of all items by specified days.

        Args:
            user: User who owns the fridge
            days: Number of days to decay (default 1)

        Returns:
            Number of items updated
        """
        items = (
            self.db.query(DBFridgeItem)
            .filter(DBFridgeItem.user_id == user.id)
            .all()
        )

        updated_count = 0
        for item in items:
            item.days_remaining = max(0, item.days_remaining - days)
            updated_count += 1

        self.db.commit()
        return updated_count

    def get_expiring_items(
        self,
        user: User,
        days_threshold: int = 2,
    ) -> List[DBFridgeItem]:
        """
        Get items expiring within threshold days.

        Args:
            user: User who owns the fridge
            days_threshold: Number of days threshold

        Returns:
            List of expiring FridgeItems
        """
        return (
            self.db.query(DBFridgeItem)
            .filter(
                DBFridgeItem.user_id == user.id,
                DBFridgeItem.days_remaining > 0,
                DBFridgeItem.days_remaining <= days_threshold,
            )
            .order_by(DBFridgeItem.days_remaining)
            .all()
        )

    def clear_fridge(self, user: User) -> int:
        """
        Clear all items from user's fridge.

        Args:
            user: User who owns the fridge

        Returns:
            Number of items deleted
        """
        count = (
            self.db.query(DBFridgeItem)
            .filter(DBFridgeItem.user_id == user.id)
            .delete()
        )
        self.db.commit()
        return count
