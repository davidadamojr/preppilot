"""
SQLAlchemy ORM models for PrepPilot database.
"""
from datetime import date, datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Text,
    ForeignKey, Enum as SQLEnum, Boolean, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from backend.db.database import Base
from backend.models.schemas import AuditAction, DietType, PrepStatus, UserRole


class User(Base):
    """User account with authentication."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    diet_type = Column(SQLEnum(DietType), default=DietType.LOW_HISTAMINE, nullable=False)
    dietary_exclusions = Column(JSON, nullable=False, default=list, server_default='[]')
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False, server_default='user')
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    fridge_items = relationship("FridgeItem", back_populates="user", cascade="all, delete-orphan")


class Recipe(Base):
    """Recipe with ingredients and preparation steps."""
    __tablename__ = "recipes"
    __table_args__ = (
        # GIN index on diet_tags for efficient JSON array containment queries
        # Note: GIN index created via raw SQL in migration (PostgreSQL-specific)
        # Index('ix_recipes_diet_tags_gin', 'diet_tags', postgresql_using='gin'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    diet_tags = Column(JSON, nullable=False)  # List[str]
    meal_type = Column(String(50), nullable=False, index=True)  # breakfast, lunch, dinner
    ingredients = Column(JSON, nullable=False)  # List[Ingredient dict]
    prep_steps = Column(JSON, nullable=False)  # List[str]
    prep_time_minutes = Column(Integer, nullable=False)
    reusability_index = Column(Float, nullable=False)
    servings = Column(Integer, default=2, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    meal_slots = relationship("MealSlot", back_populates="recipe")


class MealPlan(Base):
    """User's meal plan for a date range."""
    __tablename__ = "meal_plans"
    __table_args__ = (
        # Composite index for listing user's plans ordered by creation date
        Index('ix_meal_plans_user_id_created_at', 'user_id', 'created_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    diet_type = Column(SQLEnum(DietType), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="meal_plans")
    meals = relationship("MealSlot", back_populates="meal_plan", cascade="all, delete-orphan")


class MealSlot(Base):
    """A single meal slot within a meal plan."""
    __tablename__ = "meal_slots"
    __table_args__ = (
        # Composite index for querying meals by plan and date
        Index('ix_meal_slots_meal_plan_id_date', 'meal_plan_id', 'date'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_plan_id = Column(UUID(as_uuid=True), ForeignKey("meal_plans.id"), nullable=False, index=True)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    meal_type = Column(String(50), nullable=False)  # breakfast, lunch, dinner
    prep_status = Column(SQLEnum(PrepStatus), default=PrepStatus.PENDING, nullable=False)
    prep_completed_at = Column(DateTime, nullable=True)

    # Relationships
    meal_plan = relationship("MealPlan", back_populates="meals")
    recipe = relationship("Recipe", back_populates="meal_slots")


class FridgeItem(Base):
    """Item in user's fridge inventory."""
    __tablename__ = "fridge_items"
    __table_args__ = (
        # Composite index for expiring items queries (sorted by days_remaining)
        Index('ix_fridge_items_user_id_days_remaining', 'user_id', 'days_remaining'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    ingredient_name = Column(String(255), nullable=False, index=True)
    quantity = Column(String(100), nullable=False)
    days_remaining = Column(Integer, nullable=False)
    added_date = Column(Date, nullable=False)
    original_freshness_days = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="fridge_items")

    @property
    def freshness_percentage(self) -> float:
        """Calculate freshness as percentage (0-100)."""
        if self.original_freshness_days == 0:
            return 0.0
        return (self.days_remaining / self.original_freshness_days) * 100


class AuditLog(Base):
    """Audit log for tracking user actions and changes."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # user, plan, fridge, recipe
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # ID of affected resource
    details = Column(JSON, nullable=True)  # Additional context (old_value, new_value, etc.)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = relationship("User")
