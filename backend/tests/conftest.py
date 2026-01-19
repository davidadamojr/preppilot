"""
Shared pytest fixtures for PrepPilot backend tests.

This module provides common fixtures for:
- Database sessions (with transaction rollback)
- Test users and authentication
- FastAPI test client
- Factory functions for test data
"""
import os
import pytest
from datetime import date, timedelta
from typing import Generator, Dict
from uuid import uuid4

# Set test environment variables BEFORE importing app modules
# This ensures Settings loads in debug/test mode
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.db.database import Base, get_db
from backend.db.models import User, Recipe, MealPlan, MealSlot, FridgeItem
from backend.auth.utils import hash_password
from backend.auth.jwt import create_access_token
from backend.models.schemas import DietType, PrepStatus, UserRole
from backend.main import app


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite database for testing.

    Uses SQLite for fast, isolated tests without PostgreSQL dependency.
    Each test function gets a fresh database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing.

    Each test gets its own session with automatic cleanup.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with database dependency override.

    The database session is injected into the app, allowing full
    API route testing without a real database connection.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user(db_session) -> User:
    """Create a standard test user.

    Returns a persisted User instance with:
    - email: test@example.com
    - password: testpassword123
    - diet_type: LOW_HISTAMINE
    - role: USER
    """
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        diet_type=DietType.LOW_HISTAMINE,
        dietary_exclusions=[],
        role=UserRole.USER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    """Create an admin test user.

    Returns a persisted User instance with:
    - email: admin@example.com
    - password: adminpassword123
    - diet_type: LOW_HISTAMINE
    - role: ADMIN
    """
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        diet_type=DietType.LOW_HISTAMINE,
        dietary_exclusions=[],
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session) -> User:
    """Create an inactive test user."""
    user = User(
        email="inactive@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Inactive User",
        diet_type=DietType.LOW_HISTAMINE,
        dietary_exclusions=[],
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_with_exclusions(db_session) -> User:
    """Create a test user with dietary exclusions."""
    user = User(
        email="exclusions@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="User With Exclusions",
        diet_type=DietType.FODMAP,
        dietary_exclusions=["peanuts", "tree_nuts", "shellfish"],
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def test_user_token(test_user) -> str:
    """Generate a valid JWT token for the test user."""
    return create_access_token(user_id=test_user.id, role=test_user.role.value)


@pytest.fixture
def auth_headers(test_user_token) -> Dict[str, str]:
    """Create Authorization headers with Bearer token."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_user_token(admin_user) -> str:
    """Generate a valid JWT token for the admin user."""
    return create_access_token(user_id=admin_user.id, role=admin_user.role.value)


@pytest.fixture
def admin_auth_headers(admin_user_token) -> Dict[str, str]:
    """Create Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_user_token}"}


@pytest.fixture
def inactive_user_token(inactive_user) -> str:
    """Generate a token for an inactive user."""
    return create_access_token(user_id=inactive_user.id, role=inactive_user.role.value)


@pytest.fixture
def inactive_auth_headers(inactive_user_token) -> Dict[str, str]:
    """Create Authorization headers for inactive user."""
    return {"Authorization": f"Bearer {inactive_user_token}"}


# ============================================================================
# Recipe Fixtures
# ============================================================================

@pytest.fixture
def test_recipe(db_session) -> Recipe:
    """Create a test recipe."""
    recipe = Recipe(
        name="Test Chicken Bowl",
        diet_tags=["low_histamine"],
        meal_type="dinner",
        ingredients=[
            {"name": "chicken breast", "freshness_days": 3, "quantity": "500g", "category": "protein"},
            {"name": "rice", "freshness_days": 365, "quantity": "1 cup", "category": "grains"},
            {"name": "carrots", "freshness_days": 14, "quantity": "2 medium", "category": "produce"},
        ],
        prep_steps=["Cook rice", "Grill chicken", "Steam carrots", "Combine and serve"],
        prep_time_minutes=30,
        reusability_index=0.8,
        servings=2,
    )
    db_session.add(recipe)
    db_session.commit()
    db_session.refresh(recipe)
    return recipe


@pytest.fixture
def test_recipes(db_session) -> list[Recipe]:
    """Create multiple test recipes for variety testing."""
    recipes = [
        Recipe(
            name="Oatmeal with Berries",
            diet_tags=["low_histamine", "fodmap"],
            meal_type="breakfast",
            ingredients=[
                {"name": "oats", "freshness_days": 180, "quantity": "1 cup", "category": "grains"},
                {"name": "blueberries", "freshness_days": 5, "quantity": "1/2 cup", "category": "produce"},
            ],
            prep_steps=["Cook oats", "Top with berries"],
            prep_time_minutes=10,
            reusability_index=0.5,
            servings=1,
        ),
        Recipe(
            name="Turkey Salad",
            diet_tags=["low_histamine"],
            meal_type="lunch",
            ingredients=[
                {"name": "turkey", "freshness_days": 3, "quantity": "200g", "category": "protein"},
                {"name": "lettuce", "freshness_days": 7, "quantity": "2 cups", "category": "produce"},
            ],
            prep_steps=["Slice turkey", "Prepare salad", "Combine"],
            prep_time_minutes=15,
            reusability_index=0.6,
            servings=1,
        ),
        Recipe(
            name="Salmon Rice Bowl",
            diet_tags=["fodmap"],
            meal_type="dinner",
            ingredients=[
                {"name": "salmon", "freshness_days": 2, "quantity": "300g", "category": "protein"},
                {"name": "rice", "freshness_days": 365, "quantity": "1 cup", "category": "grains"},
            ],
            prep_steps=["Cook rice", "Bake salmon", "Serve"],
            prep_time_minutes=25,
            reusability_index=0.7,
            servings=2,
        ),
    ]
    for recipe in recipes:
        db_session.add(recipe)
    db_session.commit()
    for recipe in recipes:
        db_session.refresh(recipe)
    return recipes


# ============================================================================
# Meal Plan Fixtures
# ============================================================================

@pytest.fixture
def test_meal_plan(db_session, test_user, test_recipe) -> MealPlan:
    """Create a test meal plan with meal slots."""
    start_date = date.today()
    plan = MealPlan(
        user_id=test_user.id,
        diet_type=DietType.LOW_HISTAMINE,
        start_date=start_date,
        end_date=start_date + timedelta(days=6),
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    # Add meal slots for 7 days
    for day_offset in range(7):
        for meal_type in ["breakfast", "lunch", "dinner"]:
            slot = MealSlot(
                meal_plan_id=plan.id,
                recipe_id=test_recipe.id,
                date=start_date + timedelta(days=day_offset),
                meal_type=meal_type,
                prep_status=PrepStatus.PENDING,
            )
            db_session.add(slot)

    db_session.commit()
    db_session.refresh(plan)
    return plan


# ============================================================================
# Fridge Fixtures
# ============================================================================

@pytest.fixture
def test_fridge_items(db_session, test_user) -> list[FridgeItem]:
    """Create test fridge items for the test user."""
    items = [
        FridgeItem(
            user_id=test_user.id,
            ingredient_name="chicken breast",
            quantity="500g",
            days_remaining=2,
            added_date=date.today() - timedelta(days=1),
            original_freshness_days=3,
        ),
        FridgeItem(
            user_id=test_user.id,
            ingredient_name="carrots",
            quantity="6 medium",
            days_remaining=10,
            added_date=date.today(),
            original_freshness_days=14,
        ),
        FridgeItem(
            user_id=test_user.id,
            ingredient_name="milk",
            quantity="1 liter",
            days_remaining=1,
            added_date=date.today() - timedelta(days=6),
            original_freshness_days=7,
        ),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    for item in items:
        db_session.refresh(item)
    return items


@pytest.fixture
def expiring_fridge_items(db_session, test_user) -> list[FridgeItem]:
    """Create fridge items that are about to expire (2 days or less)."""
    items = [
        FridgeItem(
            user_id=test_user.id,
            ingredient_name="salmon",
            quantity="300g",
            days_remaining=1,
            added_date=date.today() - timedelta(days=1),
            original_freshness_days=2,
        ),
        FridgeItem(
            user_id=test_user.id,
            ingredient_name="spinach",
            quantity="1 bag",
            days_remaining=2,
            added_date=date.today() - timedelta(days=3),
            original_freshness_days=5,
        ),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    for item in items:
        db_session.refresh(item)
    return items


# ============================================================================
# Factory Functions (for custom data creation in tests)
# ============================================================================

class UserFactory:
    """Factory for creating User instances with custom attributes."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self._counter = 0

    def create(
        self,
        email: str = None,
        password: str = "testpassword123",
        full_name: str = None,
        diet_type: DietType = DietType.LOW_HISTAMINE,
        dietary_exclusions: list = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
    ) -> User:
        """Create and persist a User with given attributes."""
        self._counter += 1
        if email is None:
            email = f"user{self._counter}@example.com"
        if full_name is None:
            full_name = f"Test User {self._counter}"
        if dietary_exclusions is None:
            dietary_exclusions = []

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            diet_type=diet_type,
            dietary_exclusions=dietary_exclusions,
            role=role,
            is_active=is_active,
        )
        self.db_session.add(user)
        self.db_session.commit()
        self.db_session.refresh(user)
        return user


@pytest.fixture
def user_factory(db_session) -> UserFactory:
    """Provide a UserFactory for creating multiple users in tests."""
    return UserFactory(db_session)


class RecipeFactory:
    """Factory for creating Recipe instances with custom attributes."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self._counter = 0

    def create(
        self,
        name: str = None,
        diet_tags: list = None,
        meal_type: str = "dinner",
        ingredients: list = None,
        prep_steps: list = None,
        prep_time_minutes: int = 30,
        reusability_index: float = 0.7,
        servings: int = 2,
    ) -> Recipe:
        """Create and persist a Recipe with given attributes."""
        self._counter += 1
        if name is None:
            name = f"Test Recipe {self._counter}"
        if diet_tags is None:
            diet_tags = ["low_histamine"]
        if ingredients is None:
            ingredients = [
                {"name": "chicken", "freshness_days": 3, "quantity": "500g", "category": "protein"}
            ]
        if prep_steps is None:
            prep_steps = ["Prepare ingredients", "Cook", "Serve"]

        recipe = Recipe(
            name=name,
            diet_tags=diet_tags,
            meal_type=meal_type,
            ingredients=ingredients,
            prep_steps=prep_steps,
            prep_time_minutes=prep_time_minutes,
            reusability_index=reusability_index,
            servings=servings,
        )
        self.db_session.add(recipe)
        self.db_session.commit()
        self.db_session.refresh(recipe)
        return recipe


@pytest.fixture
def recipe_factory(db_session) -> RecipeFactory:
    """Provide a RecipeFactory for creating multiple recipes in tests."""
    return RecipeFactory(db_session)
