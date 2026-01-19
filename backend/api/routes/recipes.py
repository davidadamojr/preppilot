"""
Recipe API routes with admin CRUD operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

from backend.db.database import get_db
from backend.db.models import User, Recipe as DBRecipe
from backend.api.dependencies import get_current_user, get_current_admin_user
from backend.utils.sanitization import SanitizedStr, SanitizedStrList
from backend.config import settings

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


# Response schemas
class IngredientResponse(BaseModel):
    """Ingredient in a recipe."""
    name: str
    quantity: str
    freshness_days: int
    category: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "chicken breast",
                    "quantity": "500g",
                    "freshness_days": 3,
                    "category": "protein"
                }
            ]
        }
    }


class RecipeResponse(BaseModel):
    """Recipe response."""
    id: UUID
    name: str
    diet_tags: List[str]
    meal_type: str
    ingredients: List[dict]
    prep_steps: List[str]
    prep_time_minutes: int
    reusability_index: float
    servings: int

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Grilled Chicken Salad",
                    "diet_tags": ["low_histamine", "gluten_free"],
                    "meal_type": "lunch",
                    "ingredients": [
                        {"name": "chicken breast", "quantity": "200g", "freshness_days": 3, "category": "protein"},
                        {"name": "mixed greens", "quantity": "100g", "freshness_days": 5, "category": "vegetable"},
                        {"name": "olive oil", "quantity": "2 tbsp", "freshness_days": 365, "category": "oil"}
                    ],
                    "prep_steps": [
                        "Season chicken with salt and herbs",
                        "Grill chicken for 6-8 minutes per side",
                        "Let rest for 5 minutes, then slice",
                        "Toss greens with olive oil",
                        "Top with sliced chicken"
                    ],
                    "prep_time_minutes": 25,
                    "reusability_index": 0.7,
                    "servings": 2
                }
            ]
        }
    }


class RecipeListResponse(BaseModel):
    """Paginated recipe list response."""
    recipes: List[RecipeResponse]
    total: int
    page: int
    page_size: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recipes": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "Grilled Chicken Salad",
                            "diet_tags": ["low_histamine"],
                            "meal_type": "lunch",
                            "ingredients": [{"name": "chicken breast", "quantity": "200g", "freshness_days": 3}],
                            "prep_steps": ["Season chicken", "Grill", "Serve"],
                            "prep_time_minutes": 25,
                            "reusability_index": 0.7,
                            "servings": 2
                        }
                    ],
                    "total": 42,
                    "page": 1,
                    "page_size": 20
                }
            ]
        }
    }


class RecipeSearchResponse(BaseModel):
    """Response for recipe search by ingredient."""
    ingredient: str
    matching_recipes: List[RecipeResponse]
    count: int
    total: int
    page: int
    page_size: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ingredient": "chicken",
                    "matching_recipes": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "name": "Grilled Chicken Salad",
                            "diet_tags": ["low_histamine"],
                            "meal_type": "lunch",
                            "ingredients": [{"name": "chicken breast", "quantity": "200g", "freshness_days": 3}],
                            "prep_steps": ["Season", "Grill", "Serve"],
                            "prep_time_minutes": 25,
                            "reusability_index": 0.7,
                            "servings": 2
                        }
                    ],
                    "count": 1,
                    "total": 8,
                    "page": 1,
                    "page_size": 20
                }
            ]
        }
    }


@router.get("", response_model=RecipeListResponse)
async def list_recipes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        default=settings.pagination_default_page_size,
        ge=1,
        le=settings.pagination_max_page_size,
        description="Items per page",
    ),
    meal_type: Optional[str] = Query(None, description="Filter by meal type: breakfast, lunch, dinner"),
    diet_tag: Optional[str] = Query(None, description="Filter by diet tag"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of available recipes.

    Supports filtering by meal type and diet tag.
    """
    query = db.query(DBRecipe)

    # Apply filters
    if meal_type:
        query = query.filter(DBRecipe.meal_type == meal_type.lower())

    if diet_tag:
        # Use string matching for SQLite compatibility in tests
        # For PostgreSQL, JSONB contains would be more efficient but this works for both
        query = query.filter(
            func.lower(cast(DBRecipe.diet_tags, String)).like(f'%"{diet_tag.lower()}"%')
        )

    # Get total count
    total = query.count()

    # Paginate
    skip = (page - 1) * page_size
    recipes = query.offset(skip).limit(page_size).all()

    return RecipeListResponse(
        recipes=[
            RecipeResponse(
                id=recipe.id,
                name=recipe.name,
                diet_tags=recipe.diet_tags,
                meal_type=recipe.meal_type,
                ingredients=recipe.ingredients,
                prep_steps=recipe.prep_steps,
                prep_time_minutes=recipe.prep_time_minutes,
                reusability_index=recipe.reusability_index,
                servings=recipe.servings,
            )
            for recipe in recipes
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific recipe by ID.
    """
    recipe = db.query(DBRecipe).filter(DBRecipe.id == recipe_id).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        diet_tags=recipe.diet_tags,
        meal_type=recipe.meal_type,
        ingredients=recipe.ingredients,
        prep_steps=recipe.prep_steps,
        prep_time_minutes=recipe.prep_time_minutes,
        reusability_index=recipe.reusability_index,
        servings=recipe.servings,
    )


@router.get("/search/by-ingredient", response_model=RecipeSearchResponse)
async def search_recipes_by_ingredient(
    ingredient: str = Query(..., min_length=2, description="Ingredient name to search for"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        default=settings.pagination_default_page_size,
        ge=1,
        le=settings.pagination_max_page_size,
        description="Items per page",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search recipes that contain a specific ingredient.

    Useful for using up expiring ingredients.
    Uses database-level filtering for efficient querying.
    """
    # Use PostgreSQL JSON containment to filter at database level
    # Cast ingredients JSON to text and use case-insensitive search
    search_pattern = f"%{ingredient.lower()}%"
    query = db.query(DBRecipe).filter(
        func.lower(cast(DBRecipe.ingredients, String)).like(search_pattern)
    )

    # Get total count
    total = query.count()

    # Paginate
    skip = (page - 1) * page_size
    recipes = query.offset(skip).limit(page_size).all()

    matching_recipes = [
        RecipeResponse(
            id=recipe.id,
            name=recipe.name,
            diet_tags=recipe.diet_tags,
            meal_type=recipe.meal_type,
            ingredients=recipe.ingredients,
            prep_steps=recipe.prep_steps,
            prep_time_minutes=recipe.prep_time_minutes,
            reusability_index=recipe.reusability_index,
            servings=recipe.servings,
        )
        for recipe in recipes
    ]

    return RecipeSearchResponse(
        ingredient=ingredient,
        matching_recipes=matching_recipes,
        count=len(matching_recipes),
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# Admin CRUD Operations
# ============================================================================

class IngredientCreate(BaseModel):
    """Ingredient data for recipe creation."""
    name: SanitizedStr = Field(..., min_length=1, description="Ingredient name")
    quantity: SanitizedStr = Field(..., min_length=1, description="Quantity (e.g., '500g', '2 cups')")
    freshness_days: int = Field(..., ge=1, description="Days until ingredient expires")
    category: Optional[SanitizedStr] = Field(None, description="Category (protein, vegetable, herb, etc.)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "chicken breast",
                    "quantity": "500g",
                    "freshness_days": 3,
                    "category": "protein"
                }
            ]
        }
    }


class RecipeCreate(BaseModel):
    """Request to create a new recipe."""
    name: SanitizedStr = Field(..., min_length=1, max_length=255, description="Recipe name")
    diet_tags: SanitizedStrList = Field(..., min_length=1, description="Compatible diet types")
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$", description="Meal type")
    ingredients: List[IngredientCreate] = Field(..., min_length=1, description="List of ingredients")
    prep_steps: SanitizedStrList = Field(..., min_length=1, description="Ordered preparation steps")
    prep_time_minutes: int = Field(..., ge=1, description="Total prep time in minutes")
    reusability_index: float = Field(..., ge=0.0, le=1.0, description="Ingredient reusability score (0-1)")
    servings: int = Field(default=2, ge=1, description="Number of servings")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Herb Roasted Chicken",
                    "diet_tags": ["low_histamine", "gluten_free"],
                    "meal_type": "dinner",
                    "ingredients": [
                        {"name": "chicken thighs", "quantity": "4 pieces", "freshness_days": 3, "category": "protein"},
                        {"name": "rosemary", "quantity": "2 tbsp", "freshness_days": 7, "category": "herb"},
                        {"name": "olive oil", "quantity": "3 tbsp", "freshness_days": 365, "category": "oil"}
                    ],
                    "prep_steps": [
                        "Preheat oven to 400°F (200°C)",
                        "Mix herbs with olive oil",
                        "Rub chicken with herb mixture",
                        "Roast for 35-40 minutes until golden"
                    ],
                    "prep_time_minutes": 45,
                    "reusability_index": 0.6,
                    "servings": 4
                }
            ]
        }
    }


class RecipeUpdate(BaseModel):
    """Request to update a recipe (all fields optional)."""
    name: Optional[SanitizedStr] = Field(None, min_length=1, max_length=255)
    diet_tags: Optional[SanitizedStrList] = Field(None, min_length=1)
    meal_type: Optional[str] = Field(None, pattern="^(breakfast|lunch|dinner|snack)$")
    ingredients: Optional[List[IngredientCreate]] = Field(None, min_length=1)
    prep_steps: Optional[SanitizedStrList] = Field(None, min_length=1)
    prep_time_minutes: Optional[int] = Field(None, ge=1)
    reusability_index: Optional[float] = Field(None, ge=0.0, le=1.0)
    servings: Optional[int] = Field(None, ge=1)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Herb Roasted Chicken",
                    "prep_time_minutes": 50,
                    "servings": 6
                }
            ]
        }
    }


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Recipe 'Herb Roasted Chicken' deleted successfully"
                }
            ]
        }
    }


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    recipe: RecipeCreate,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Create a new recipe.

    **Admin only**: Requires admin role.
    """
    # Check for duplicate recipe name
    existing = db.query(DBRecipe).filter(
        func.lower(DBRecipe.name) == recipe.name.lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A recipe with this name already exists",
        )

    # Convert ingredients to dict format for JSON storage
    ingredients_data = [ing.model_dump() for ing in recipe.ingredients]

    new_recipe = DBRecipe(
        name=recipe.name,
        diet_tags=recipe.diet_tags,
        meal_type=recipe.meal_type.lower(),
        ingredients=ingredients_data,
        prep_steps=recipe.prep_steps,
        prep_time_minutes=recipe.prep_time_minutes,
        reusability_index=recipe.reusability_index,
        servings=recipe.servings,
    )

    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)

    return RecipeResponse(
        id=new_recipe.id,
        name=new_recipe.name,
        diet_tags=new_recipe.diet_tags,
        meal_type=new_recipe.meal_type,
        ingredients=new_recipe.ingredients,
        prep_steps=new_recipe.prep_steps,
        prep_time_minutes=new_recipe.prep_time_minutes,
        reusability_index=new_recipe.reusability_index,
        servings=new_recipe.servings,
    )


@router.put("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(
    recipe_id: UUID,
    recipe_update: RecipeUpdate,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update a recipe.

    **Admin only**: Requires admin role.
    Only updates fields that are provided (non-None).
    """
    recipe = db.query(DBRecipe).filter(DBRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    # Check for duplicate name if name is being updated
    if recipe_update.name is not None and recipe_update.name.lower() != recipe.name.lower():
        existing = db.query(DBRecipe).filter(
            func.lower(DBRecipe.name) == recipe_update.name.lower(),
            DBRecipe.id != recipe_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A recipe with this name already exists",
            )

    # Update only provided fields
    if recipe_update.name is not None:
        recipe.name = recipe_update.name
    if recipe_update.diet_tags is not None:
        recipe.diet_tags = recipe_update.diet_tags
    if recipe_update.meal_type is not None:
        recipe.meal_type = recipe_update.meal_type.lower()
    if recipe_update.ingredients is not None:
        recipe.ingredients = [ing.model_dump() for ing in recipe_update.ingredients]
    if recipe_update.prep_steps is not None:
        recipe.prep_steps = recipe_update.prep_steps
    if recipe_update.prep_time_minutes is not None:
        recipe.prep_time_minutes = recipe_update.prep_time_minutes
    if recipe_update.reusability_index is not None:
        recipe.reusability_index = recipe_update.reusability_index
    if recipe_update.servings is not None:
        recipe.servings = recipe_update.servings

    db.commit()
    db.refresh(recipe)

    return RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        diet_tags=recipe.diet_tags,
        meal_type=recipe.meal_type,
        ingredients=recipe.ingredients,
        prep_steps=recipe.prep_steps,
        prep_time_minutes=recipe.prep_time_minutes,
        reusability_index=recipe.reusability_index,
        servings=recipe.servings,
    )


@router.delete("/{recipe_id}", response_model=MessageResponse)
async def delete_recipe(
    recipe_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete a recipe.

    **Admin only**: Requires admin role.
    Warning: This will fail if the recipe is referenced by meal plans.
    """
    recipe = db.query(DBRecipe).filter(DBRecipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    # Check if recipe is in use by any meal slots
    if recipe.meal_slots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete recipe: it is referenced by existing meal plans",
        )

    db.delete(recipe)
    db.commit()

    return MessageResponse(message=f"Recipe '{recipe.name}' deleted successfully")
