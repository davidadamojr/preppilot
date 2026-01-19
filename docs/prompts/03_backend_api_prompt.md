**Goal:** Implement backend APIs and data flow for adaptive planning.

**Prompt:**

You are building the **FastAPI backend** for PrepPilot.

### Core Endpoints
- `POST /generate_plan` → creates 3-day diet-compliant plan.
- `POST /mark_prep` → marks prep as done/skipped.
- `POST /adapt_plan` → triggers adaptive replan via Adaptive Engine.
- `GET /get_fridge_state` → returns current inventory and freshness decay.

### Data Models
```python
class User(BaseModel):
    id: UUID
    diet_type: str

class Ingredient(BaseModel):
    name: str
    freshness_days: int
    quantity: str

class Recipe(BaseModel):
    name: str
    diet_tags: list[str]
    ingredients: list[Ingredient]
    prep_time: int
    steps: list[str]
    reusability_index: float

class MealPlan(BaseModel):
    user_id: UUID
    start_date: date
    meals: list[Recipe]
    schedule: dict
```

### Business Logic
- Maintain `plan_state` per user.
- On missed prep, call Adaptive Engine → persist `new_plan`.
- Update fridge freshness daily.

**Additional Features:**
- Integrate with Supabase or Neon Postgres.
- Use Pydantic for schema validation.
- Include automated testing for adaptive logic.
