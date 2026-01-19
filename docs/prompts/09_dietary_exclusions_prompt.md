**Goal:** Add user-controlled ingredient and food-category exclusions (e.g., exclude all seafood, dairy, nuts) across meal generation, adaptive replanning, grocery lists, and prep sequences.


**Prompt:**


You are implementing the **Dietary Exclusion System** for PrepPilot — a cross‑cutting feature that ensures users can exclude specific foods, ingredients, or entire categories from all generated meal plans.


### 🎯 Core Objectives
1. Allow users to exclude individual ingredients or entire food categories.
2. Ensure exclusions apply everywhere: meal generation, adaptive replanning, fallback meals, grocery lists, and prep sequences.
3. Exclusions override diet defaults (e.g., low‑histamine + no seafood).
4. Provide clear explanations when substitutions or changes occur.
5. Maintain graceful behavior when exclusions become highly restrictive.


### 🧩 Functional Requirements


#### 1. User Exclusion Model
```json
{
"user_id": "uuid",
"excluded_ingredients": ["salmon", "shrimp"],
"excluded_categories": ["seafood", "shellfish"]
}
```


Users may select:
- Ingredient-level exclusions
- Category-level exclusions
- Free-text exclusions


#### 2. Category Taxonomy
Define hierarchical groups (example):
```json
{
"seafood": ["salmon", "tuna", "shrimp", "cod", "mussels"],
"nightshades": ["tomato", "pepper", "eggplant", "paprika"],
"dairy": ["milk", "cheese", "butter"],
"nuts": ["almonds", "cashews", "walnuts"]
}
```


#### 3. Meal Generator Integration
- Filter out recipes containing excluded ingredients or categories.
- If a recipe is almost valid, attempt substitution using the substitution graph.
- If no compliant recipe exists, fall back to simplified meals.


#### 4. Adaptive Engine Integration
- Adaptive replanning must fully respect exclusions.
- Fallback meals must also be exclusion-safe.
- If exclusions create a narrow pool, return helpful guidance.


#### 5. Prep Sequence & Grocery List Integration
- No excluded ingredients should appear in shopping lists or prep instructions.
- Ingredient tracker should hide excluded items and adjust freshness logic accordingly.


### 🔁 Behavioral Logic
1. Load user exclusions.
2. Filter recipe pool accordingly.
3. Apply substitutions where available.
4. If recipes become too restrictive, offer guidance.
5. Always generate a human-readable explanation.


### 🧪 Validation Criteria
- No excluded ingredients appear in any plan, list, or sequence.
- Adaptive replanning still returns a valid plan.
- Substitutions and omissions are explained clearly.
- System behaves gracefully when exclusions are very restrictive.


### ✳️ Final Guidance
- **Correctness is absolute:** excluded items must never appear.
- **Transparency:** always explain exclusion-driven changes.
- **Completeness:** exclusions propagate through generation, adaptation, prep, grocery lists, and freshness logic.
- **Graceful handling:** maintain usability even when few recipes remain.
- **Extensibility:** taxonomy must support future categories (soy-free, grain-free, etc.).