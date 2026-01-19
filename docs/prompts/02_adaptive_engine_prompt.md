## 02_ADAPTIVE_ENGINE_PROMPT.md

**Goal:** Build the adaptive intelligence — the “brain” that replans when a prep is missed.

**Prompt:**

You are building the **Adaptive Engine** for PrepPilot — the system that monitors prep activity and adjusts future plans.

### Responsibilities
1. Detect missed or delayed preps.
2. Replan upcoming meals intelligently based on:
   - Ingredient freshness windows.
   - Meal dependencies (e.g., pre-chopped ingredients).
   - User energy/time constraints.
3. Preserve continuity — don’t regenerate from scratch.
4. Produce a new 3-day rolling plan + grocery delta.

### Input Schema
```json
{
  "user_id": "uuid",
  "diet_type": "low_histamine",
  "plan": { ... },
  "fridge": { "chicken": 2, "parsley": 1 },
  "missed_preps": ["2025-10-20"],
  "calendar": { ... }
}
```

### Output Schema
```json
{
  "new_plan": {...},
  "adaptation_summary": [
    "Skipped Tuesday prep — reused chicken in Thursday stir fry.",
    "Parsley expiring — added to quick soup recipe."
  ],
  "grocery_adjustments": ["Buy lemons", "Skip onions"]
}
```

### Core Algorithm (Conceptual)
1. Compare `missed_preps` vs. `plan`.
2. Identify unprepared ingredients; check freshness.
3. Generate substitutions or simplified meals.
4. Prioritize perishable items for next available day.
5. Return updated schedule + rationale.

### Key Rules
- Favor continuity: re-use existing meals when possible.
- Prefer simplification over regeneration.
- Always explain changes to the user (transparency).

**MVP Validation:** The adaptive engine should successfully replan for a missed prep while maintaining dietary compliance and ingredient reuse.
