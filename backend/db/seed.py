"""
Seed database with initial data (recipes).
"""
import json
from pathlib import Path
from sqlalchemy.orm import Session
import uuid

from backend.db.database import SessionLocal, create_tables
from backend.db.models import Recipe


def load_recipes_from_json() -> list[dict]:
    """Load recipes from the JSON file."""
    recipes_path = Path(__file__).parent.parent / "data" / "low_histamine_recipes.json"
    with open(recipes_path, "r") as f:
        data = json.load(f)
    return data["recipes"]


def seed_recipes(db: Session) -> int:
    """
    Seed recipes into the database.

    Returns:
        Number of recipes added.
    """
    # Check if recipes already exist
    existing_count = db.query(Recipe).count()
    if existing_count > 0:
        print(f"Database already has {existing_count} recipes. Skipping seed.")
        return 0

    recipes_data = load_recipes_from_json()
    added = 0

    for recipe_data in recipes_data:
        # Create Recipe model instance
        recipe = Recipe(
            id=uuid.uuid4(),
            name=recipe_data["name"],
            diet_tags=recipe_data["diet_tags"],
            meal_type=recipe_data["meal_type"],
            ingredients=recipe_data["ingredients"],  # Store as JSON
            prep_steps=recipe_data["prep_steps"],
            prep_time_minutes=recipe_data["prep_time_minutes"],
            reusability_index=recipe_data["reusability_index"],
            servings=recipe_data.get("servings", 2),
        )
        db.add(recipe)
        added += 1

    db.commit()
    return added


def main():
    """Main seed function."""
    print("Creating database tables...")
    create_tables()

    print("Seeding recipes...")
    db = SessionLocal()
    try:
        count = seed_recipes(db)
        print(f"✅ Successfully seeded {count} recipes!")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
