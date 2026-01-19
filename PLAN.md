# Parallel Task Scheduling with LLM-Powered Step Parsing

## Overview

Enhance the prep timeline optimizer with:
1. **Configurable LLM-based step parsing** - Extract structured data (action_type, ingredient, equipment, is_passive, phase) for intelligent scheduling
2. **Improved batching via semantic normalization** - LLM normalizes action types and ingredients for better batch grouping
3. **Parallel task scheduling** - Schedule prep tasks during passive cooking time
4. **Hybrid list UI** - Tablet-friendly visualization with parallel task callouts

**Configuration Model:**
- LLM parsing is **primary** when enabled (feature flag + API key configured)
- Heuristics are **fallback** on LLM failure or when disabled
- Failures are **logged** for observability

---

## How LLM Improves Both Batching and Parallel Scheduling

The LLM parsing step extracts normalized data that improves **both** optimizations:

```
Raw Recipe Steps
       ↓
┌──────────────────────────────────────────────────────────┐
│              LLM Step Parsing (or Heuristic)             │
│                                                          │
│  Extracts for each step:                                 │
│  • action_type (normalized): "dice" → "chop"             │
│  • ingredient (normalized): "tart green apple" → "apple" │
│  • equipment: "oven" | "stovetop" | "prep_area"          │
│  • is_passive: true for simmer, rest, marinate           │
│  • phase: "prep" | "cooking" | "finishing"               │
│  • duration_minutes: estimated time                      │
│  • can_batch: combinable with similar steps              │
└──────────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────────┐
│                   1. BATCHING                            │
│                                                          │
│  Uses normalized action_type + ingredient to group:      │
│  • "Dice onion" + "Chop garlic" → both have action_type  │
│    "chop" → batched as "Chop onion and garlic"           │
│  • "Rinse lettuce" + "Wash cucumber" → both have         │
│    action_type "wash" → batched as "Wash vegetables"     │
│                                                          │
│  Result: Fewer, combined steps                           │
└──────────────────────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────────────┐
│              2. PARALLEL SCHEDULING                      │
│                                                          │
│  Uses equipment + is_passive to identify opportunities:  │
│  • Passive steps (simmer, roast, rest) can have tasks    │
│    scheduled during them                                 │
│  • Prep area tasks run during passive cooking time       │
│  • Equipment conflicts prevent overlap (two oven tasks)  │
│                                                          │
│  Result: Reduced wall-clock time                         │
└──────────────────────────────────────────────────────────┘
       ↓
Optimized Timeline with Time Savings
```

---

## Current State

The existing `PrepOptimizer` batches identical tasks using **keyword matching**:
- "Chop onion" + "Chop garlic" → batched (same keyword "chop")
- "Dice onion" + "Chop garlic" → NOT batched (different keywords)

**Limitations:**
- Misses semantic equivalents ("dice" = "chop" = "mince")
- No ingredient normalization ("tart green apple" ≠ "apple")
- No parallel scheduling (all steps run sequentially)

---

## Goals

1. **LLM Step Parsing**: Extract normalized action types, ingredients, equipment, and phase
2. **Improved Batching**: Use normalized values for semantic grouping
3. **Parallel Scheduling**: Schedule prep tasks during passive cooking time
4. **Equipment Tracking**: Prevent conflicts (e.g., two oven tasks)
5. **Hybrid List Visualization**: Tablet-friendly UI with parallel task callouts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PrepOptimizer                          │
│                           │                                 │
│              ┌────────────┴────────────┐                   │
│              ▼                         ▼                   │
│   ┌─────────────────┐       ┌─────────────────────┐       │
│   │ HeuristicParser │◄──────│    LLMStepParser    │       │
│   │ (keyword-based) │       │  - OpenAI GPT-4     │       │
│   │                 │       │  - Semantic normals │       │
│   │                 │       │  - Caching layer    │       │
│   │                 │       │  - Fallback on error│       │
│   └─────────────────┘       └─────────────────────┘       │
│              │                         │                   │
│              └────────────┬────────────┘                   │
│                           ▼                                 │
│              ┌─────────────────────────┐                   │
│              │  Batching Algorithm     │                   │
│              │  (uses normalized data) │                   │
│              └─────────────────────────┘                   │
│                           │                                 │
│                           ▼                                 │
│              ┌─────────────────────────┐                   │
│              │  Parallel Scheduler     │                   │
│              │  (uses equipment/phase) │                   │
│              └─────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Model Changes

### ParsedPrepStep (new dataclass)

```python
@dataclass
class ParsedPrepStep:
    # Normalized values for improved batching
    action_type: str                    # Normalized: "dice" → "chop", "rinse" → "wash"
    ingredient: Optional[str]           # Normalized: "tart green apple" → "apple"
    can_batch: bool                     # True if combinable with similar steps

    # Values for parallel scheduling
    equipment: Literal["oven", "stovetop", "prep_area", "hands_free"]
    is_passive: bool                    # True = no attention needed (simmer, rest)
    phase: Literal["prep", "cooking", "finishing"]
    duration_minutes: int               # Estimated time

    # Metadata
    raw_step: str                       # Original text
    parse_source: Literal["llm", "heuristic"]
```

### PrepStep schema additions

```python
class PrepStep(BaseModel):
    # ... existing fields ...
    equipment: Optional[str] = None     # NEW: "oven", "stovetop", "prep_area", "hands_free"
    is_passive: bool = False            # NEW: True if step doesn't require attention
    phase: Optional[str] = None         # NEW: "prep", "cooking", "finishing"
    parallel_tasks: List[PrepStep] = [] # NEW: Tasks that can run during this step
```

### ParallelPrepTimeline (new schema)

```python
class ParallelPrepTimeline(BaseModel):
    total_time_minutes: int           # Wall-clock time with parallelization
    sequential_time_minutes: int      # Time if done sequentially (for comparison)
    time_saved_minutes: int           # Savings from batching + parallelization
    batching_savings_minutes: int     # Savings from batching alone
    parallel_savings_minutes: int     # Savings from parallel scheduling alone
    steps: List[PrepStep]             # Steps with parallel_tasks populated
    prep_date: date
```

---

## LLM Semantic Normalization for Batching

### Action Type Normalization

The LLM normalizes semantically equivalent actions to a canonical form:

| Raw Action | Normalized `action_type` |
|------------|--------------------------|
| dice, mince, cube, julienne | `chop` |
| rinse, clean | `wash` |
| sauté, pan-fry, stir-fry | `fry` |
| whisk, beat, fold | `mix` |
| bake, roast | `roast` |

### Ingredient Normalization

The LLM normalizes ingredient descriptions:

| Raw Ingredient | Normalized `ingredient` |
|----------------|------------------------|
| "tart green apple" | `apple` |
| "fresh eggs" | `eggs` |
| "boneless skinless chicken breast" | `chicken breast` |
| "medium yellow onion" | `onion` |

### Batching Improvement Example

**Before (keyword heuristics):**
```
Steps from 2 recipes:
1. "Dice the onion finely"           → action="dice", NOT batched
2. "Chop garlic"                     → action="chop", NOT batched
3. "Rinse the lettuce"               → action="rinse", NOT batched
4. "Wash cucumber thoroughly"        → action="wash", NOT batched

Result: 4 separate steps
```

**After (LLM semantic normalization):**
```
Steps from 2 recipes:
1. "Dice the onion finely"           → action_type="chop" ─┐
2. "Chop garlic"                     → action_type="chop" ─┴→ "Chop onion and garlic"
3. "Rinse the lettuce"               → action_type="wash" ─┐
4. "Wash cucumber thoroughly"        → action_type="wash" ─┴→ "Wash lettuce and cucumber"

Result: 2 batched steps (saved 2 steps)
```

---

## Equipment Categories

| Category | Examples | Constraint |
|----------|----------|------------|
| `oven` | Roast, bake, preheat | One use at a time |
| `stovetop` | Simmer, sauté, boil | Multiple burners available |
| `prep_area` | Chop, mix, grate, peel | Requires hands-on attention |
| `hands_free` | Rest, marinate, cool | No attention needed - parallelizable |

---

## LLM Prompt Design

### System Prompt
```
You are a culinary assistant that analyzes recipe preparation steps.
Extract structured information to help optimize cooking schedules.

IMPORTANT: Normalize action types and ingredients to canonical forms:
- Actions: "dice", "mince", "cube" → "chop"; "rinse", "clean" → "wash"
- Ingredients: Remove adjectives like "fresh", "tart", "medium" unless essential
```

### User Prompt (with real examples from recipes)
```
Recipe: Coconut Cardamom Rice Pudding with Stewed Apple
Total prep time: 25 minutes

Parse each step and extract:
- action_type: Primary action NORMALIZED (chop, wash, mix, roast, simmer, etc.)
- ingredient: Main ingredient NORMALIZED (remove adjectives like "fresh", "tart")
- duration_minutes: Estimated time
- equipment: "oven" | "stovetop" | "prep_area" | "hands_free"
- is_passive: true if no attention needed
- can_batch: true if combinable with similar steps across recipes
- phase: "prep" | "cooking" | "finishing"

Steps:
1. Rinse rice thoroughly.
2. Combine rice with water and a pinch of salt.
3. Bring rice to a boil over high heat, then reduce to low and simmer for 15 minutes.
4. Crack cardamom pods to expose seeds.
5. Heat coconut milk in a separate pan over medium-low heat with the cardamom and maple syrup until steaming.
6. Peel and cube the tart green apple.
7. Add apple to the coconut milk and simmer until soft but not mushy.
8. Stir the rice into the infused milk mixture.
9. Cook for another 5 minutes to meld textures.
10. Serve warm.
```

### Expected LLM Output
```json
{
  "parsed_steps": [
    {"step_index": 0, "action_type": "wash", "ingredient": "rice", "duration_minutes": 2, "equipment": "prep_area", "is_passive": false, "can_batch": true, "phase": "prep"},
    {"step_index": 1, "action_type": "combine", "ingredient": "rice", "duration_minutes": 1, "equipment": "prep_area", "is_passive": false, "can_batch": false, "phase": "prep"},
    {"step_index": 2, "action_type": "simmer", "ingredient": "rice", "duration_minutes": 15, "equipment": "stovetop", "is_passive": true, "can_batch": false, "phase": "cooking"},
    {"step_index": 3, "action_type": "crack", "ingredient": "cardamom", "duration_minutes": 1, "equipment": "prep_area", "is_passive": false, "can_batch": true, "phase": "prep"},
    {"step_index": 4, "action_type": "heat", "ingredient": "coconut milk", "duration_minutes": 5, "equipment": "stovetop", "is_passive": false, "can_batch": false, "phase": "cooking"},
    {"step_index": 5, "action_type": "chop", "ingredient": "apple", "duration_minutes": 3, "equipment": "prep_area", "is_passive": false, "can_batch": true, "phase": "prep"},
    {"step_index": 6, "action_type": "simmer", "ingredient": "apple", "duration_minutes": 5, "equipment": "stovetop", "is_passive": true, "can_batch": false, "phase": "cooking"},
    {"step_index": 7, "action_type": "stir", "ingredient": "rice", "duration_minutes": 1, "equipment": "stovetop", "is_passive": false, "can_batch": false, "phase": "cooking"},
    {"step_index": 8, "action_type": "cook", "ingredient": null, "duration_minutes": 5, "equipment": "stovetop", "is_passive": true, "can_batch": false, "phase": "cooking"},
    {"step_index": 9, "action_type": "serve", "ingredient": null, "duration_minutes": 1, "equipment": "prep_area", "is_passive": false, "can_batch": false, "phase": "finishing"}
  ]
}
```

### Step Complexity Examples from Actual Recipes

| Step Type | Example | Parsing Challenge |
|-----------|---------|-------------------|
| Simple | "Rinse rice thoroughly." | Normalize "rinse" → "wash" |
| Timed passive | "Simmer for 15 minutes." | Detect passive, extract time |
| Equipment-specific | "Heat coconut oil in a cast iron skillet over medium-high heat (about 375°F)" | Detect stovetop, ignore temperature |
| Hands-free | "Let batter rest for 10 minutes" | Detect passive wait time |
| Multi-action | "Peel and cube the tart green apple." | Normalize "cube" → "chop", ingredient → "apple" |
| Commentary | "The stewed apple provides the ACID to balance the rich, fatty coconut milk." | Skip or mark as finishing/serve |
| Compound | "Brown meatballs on all sides in the hot oil (FAT adds flavor and texture)." | Ignore parenthetical, extract core action |

---

## Parallel Scheduling Algorithm

### Scheduling Rules

1. **Passive steps** (simmer, rest, roast) can have parallel tasks
2. **Prep area tasks** (chop, mix, season) can run during passive time
3. **Equipment conflicts** prevent parallel scheduling (two oven tasks)
4. **Within-recipe order** is preserved (step 2 after step 1)

### Algorithm

```python
def optimize_parallel(self, meal_plan: MealPlan, prep_date: date) -> ParallelPrepTimeline:
    """
    1. Parse all steps using StepParser (LLM or heuristic)
    2. Batch steps using normalized action_type + ingredient
    3. Identify passive steps (is_passive=True)
    4. For each passive step, find prep_area tasks that fit within its duration
    5. Assign those tasks as parallel_tasks
    6. Calculate time savings (batching + parallelization)
    """
```

---

## Frontend: Hybrid List UI

### Design Rationale

Tablet and touch-friendly visualization that:
- Uses full-width tappable cards for each step
- Shows parallel task opportunities as nested callouts
- Works in both portrait and landscape
- Uses standard list semantics for accessibility

### Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Today's Prep Timeline                            50 min    │
│ ✨ Saved 20 min (5 batching + 15 parallel scheduling)      │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 1. Preheat oven to 400°F                         5 min ││
│ └─────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 2. Season chicken with herbs                     3 min ││
│ └─────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 3. Chop onion and garlic (batched)               5 min ││
│ └─────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 4. Roast chicken                                40 min ││
│ │                                                         ││
│ │  ┌───────────────────────────────────────────────────┐ ││
│ │  │ 💡 While roasting (hands-free):                   │ ││
│ │  │                                                   │ ││
│ │  │   ☐ Wash lettuce and cucumber      3 min        │ ││
│ │  │   ☐ Mix salad dressing             3 min        │ ││
│ │  │   ☐ Toss salad                     2 min        │ ││
│ │  └───────────────────────────────────────────────────┘ ││
│ └─────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 5. Rest meat                                     5 min ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```
PrepTimelineDialog
├── TimelineHeader (total time, savings breakdown)
├── TimelinePhase (prep)
│   └── StepCard[]
│       └── ParallelTaskCallout (if has parallel_tasks)
├── TimelinePhase (cooking)
│   └── StepCard[]
│       └── ParallelTaskCallout
└── TimelinePhase (finishing)
    └── StepCard[]
```

---

## Feature Flag & Configuration

### Feature Flag
```python
# backend/features/flags.py
Feature.LLM_STEP_PARSING = "llm_step_parsing"
# Default: False (disabled)
```

### Config Settings
```python
# backend/config.py
openai_api_key: Optional[str] = None
openai_model: str = "gpt-4o"
openai_timeout_seconds: int = 30
openai_temperature: float = 0.1
step_parsing_cache_ttl_hours: int = 24
```

### Environment Variables
```bash
FEATURE_LLM_STEP_PARSING=true
OPENAI_API_KEY=sk-...
```

---

## Caching Strategy

- **Key**: `hash(recipe_id + step_text)`
- **TTL**: 24 hours (configurable)
- **Storage**: In-memory dict (upgrade to Redis for multi-worker)
- **Batch optimization**: Parse all recipe steps in single LLM call

---

## Fallback Logic

```python
def parse_step(self, step: str, context: dict) -> ParsedPrepStep:
    # 1. Check cache
    cached = self.cache.get(cache_key)
    if cached:
        return cached

    # 2. Try LLM
    try:
        result = self._call_llm(step, context)
        self.cache.set(cache_key, result)
        return result
    except Exception as e:
        # 3. Log and fallback
        logger.warning(f"LLM parsing failed: {e}")
        return self.heuristic_parser.parse_step(step, context)
```

---

## API Changes

### Updated Endpoint

```
GET /api/plans/{plan_id}/prep-timeline?prep_date={date}&parallel=true
```

When `parallel=true`:
- Returns `ParallelPrepTimeline` with `parallel_tasks` populated
- Calculates time savings from both batching and parallelization

### Response Example

```json
{
  "total_time_minutes": 50,
  "sequential_time_minutes": 70,
  "time_saved_minutes": 20,
  "batching_savings_minutes": 5,
  "parallel_savings_minutes": 15,
  "steps": [
    {
      "step_number": 3,
      "action": "Chop onion and garlic",
      "duration_minutes": 5,
      "equipment": "prep_area",
      "is_passive": false,
      "phase": "prep",
      "source_recipes": ["Roast Chicken", "Salad"]
    },
    {
      "step_number": 4,
      "action": "Roast chicken",
      "duration_minutes": 40,
      "equipment": "oven",
      "is_passive": true,
      "phase": "cooking",
      "parallel_tasks": [
        {"action": "Wash lettuce and cucumber", "duration_minutes": 3},
        {"action": "Mix salad dressing", "duration_minutes": 3},
        {"action": "Toss salad", "duration_minutes": 2}
      ]
    }
  ],
  "prep_date": "2025-01-15"
}
```

---

## Implementation Phases

### Phase 1: Foundation (Backend) - COMPLETED
1. Create `backend/engine/parsing/` module - DONE
2. Add `LLM_STEP_PARSING` feature flag - DONE
3. Add OpenAI config settings - DONE
4. Implement `ParsedPrepStep` dataclass - DONE

**Files created:**
- `backend/engine/parsing/__init__.py`
- `backend/engine/parsing/models.py` (ParsedPrepStep, Equipment, Phase)
- `backend/engine/parsing/protocol.py` (StepParser protocol)
- `backend/engine/parsing/factory.py` (create_step_parser factory)
- `backend/clients/__init__.py`
- `backend/clients/openai_client.py` (OpenAIClient wrapper)

**Files modified:**
- `backend/features/flags.py` (added LLM_STEP_PARSING flag)
- `backend/config.py` (added OpenAI config settings)
- `backend/requirements.txt` (added openai>=1.10.0)
- `.env` and `.env.example` (added OpenAI env vars)

### Phase 2: Parsers (Backend) - COMPLETED
1. Extract heuristic logic to `HeuristicStepParser` - DONE
2. Add equipment/passive/phase detection - DONE
3. Implement `OpenAIClient` wrapper - DONE
4. Implement `LLMStepParser` with caching and fallback - DONE
5. Implement `StepParserFactory` - DONE

**Files created:**
- `backend/engine/parsing/heuristic.py` (comprehensive keyword-based parser)
- `backend/engine/parsing/llm.py` (LLM parser with caching and fallback)
- `backend/engine/parsing/cache.py` (in-memory cache with TTL)

### Phase 3: Enhanced Batching (Backend) - COMPLETED
1. Update batching algorithm to use normalized `action_type` and `ingredient` - DONE
2. Update `PrepStep` schema with new fields - DONE
3. Refactor `PrepOptimizer` to use parser - DONE

**Files modified:**
- `backend/models/schemas.py` (added EquipmentType, CookingPhase enums; updated PrepStep with equipment, is_passive, phase, parallel_tasks; added ParallelPrepTimeline)
- `backend/engine/prep_optimizer.py` (refactored to use step parser, added optimize_parallel method)

### Phase 4: Parallel Scheduling (Backend) - COMPLETED
1. Add `optimize_parallel()` method to `PrepOptimizer` - DONE
2. Implement parallel task assignment algorithm - DONE
3. Update API endpoint for `parallel=true` - DONE

**Files modified:**
- `backend/api/routes/plans.py` (added parallel query parameter to prep-timeline endpoint)

### Phase 5: Frontend UI - COMPLETED
1. Add TypeScript types for `ParallelPrepTimeline` - DONE
2. Update `prep-timeline-dialog.tsx` with hybrid list UI - DONE
3. Add `StepCard` and `ParallelTaskCallout` components - DONE (integrated into dialog)
4. Add phase grouping and savings breakdown - DONE

**Files modified:**
- `frontend/src/types/index.ts` (added EquipmentType, CookingPhase, ParallelPrepTimeline; updated PrepStep with new fields)
- `frontend/src/lib/api.ts` (added parallel parameter to getPrepTimeline)
- `frontend/src/components/dashboard/prep-timeline-dialog.tsx` (complete redesign with parallel mode toggle, phase badges, and parallel task callouts)

### Phase 6: Testing - COMPLETED
1. Unit tests for parsers (semantic normalization) - DONE
2. Unit tests for batching (with normalized values) - DONE
3. Unit tests for parallel scheduling - DONE
4. Integration tests for API - (Covered by existing test_plans_routes.py)
5. Frontend component tests - (To be added as needed)

**Files created:**
- `backend/tests/test_step_parsing.py` (44 tests for HeuristicStepParser, cache, and ParsedPrepStep)
- `backend/tests/test_prep_optimizer.py` (21 tests for batching, parallel scheduling, and edge cases)

**Test results:** 65 tests passing

---

## Implementation Complete

All 6 phases have been successfully implemented. The parallel task scheduling feature with LLM-powered step parsing is now ready for use.

---

## File Changes Summary

### Files to Create

| File | Purpose |
|------|---------|
| `backend/engine/parsing/__init__.py` | Module init |
| `backend/engine/parsing/models.py` | `ParsedPrepStep` dataclass |
| `backend/engine/parsing/protocol.py` | `StepParser` Protocol interface |
| `backend/engine/parsing/heuristic.py` | Refactored heuristic parser with equipment/phase detection |
| `backend/engine/parsing/llm.py` | LLM parser with semantic normalization, caching, fallback |
| `backend/engine/parsing/cache.py` | In-memory cache for parsed steps |
| `backend/engine/parsing/factory.py` | Factory function based on feature flag |
| `backend/clients/__init__.py` | Module init |
| `backend/clients/openai_client.py` | OpenAI API wrapper with retry logic |
| `backend/tests/test_step_parsing.py` | Unit tests for parsers |

### Files to Modify

| File | Changes |
|------|---------|
| `backend/features/flags.py` | Add `LLM_STEP_PARSING` feature flag |
| `backend/config.py` | Add OpenAI configuration settings |
| `backend/models/schemas.py` | Add `equipment`, `is_passive`, `phase`, `parallel_tasks` fields to `PrepStep` |
| `backend/engine/prep_optimizer.py` | Use parser factory, update batching to use normalized values, add `optimize_parallel()` |
| `backend/api/routes/plans.py` | Add `parallel=true` query parameter |
| `backend/requirements.txt` | Add `openai>=1.10.0` |
| `frontend/src/types/index.ts` | Add TypeScript types for `ParallelPrepTimeline` |
| `frontend/src/components/dashboard/prep-timeline-dialog.tsx` | Update to hybrid list UI with parallel callouts |

---

## Testing Strategy

### Unit Tests

1. **Semantic Normalization**
   - "Dice onion" → action_type="chop"
   - "Rinse lettuce" → action_type="wash"
   - "tart green apple" → ingredient="apple"

2. **Batching with Normalized Values**
   - "Dice onion" + "Chop garlic" → batched (both action_type="chop")
   - "Rinse lettuce" + "Wash cucumber" → batched (both action_type="wash")

3. **Equipment Detection**
   - "Roast at 400°F" → equipment="oven"
   - "Simmer for 15 minutes" → equipment="stovetop", is_passive=true

4. **Parallel Scheduling**
   - Prep task + simmer → parallel (prep during simmer)
   - Two oven tasks → sequential (equipment conflict)

5. **Time Calculation**
   - Verify batching_savings + parallel_savings = time_saved

### Integration Tests

1. Full timeline generation with real recipe data
2. API endpoint returns valid `ParallelPrepTimeline`
3. Frontend renders hybrid list without errors

---

## Success Criteria

1. **Batching Accuracy**: LLM normalization catches 90%+ of semantic equivalents
2. **Parallel Scheduling**: 15-30% additional time savings beyond batching
3. **Reliability**: <5% fallback rate due to LLM errors
4. **Performance**: Cached responses <10ms, LLM <5s (p95)
5. **Cost**: <$0.01 per recipe (amortized with caching)

---

## Dependencies

```
openai>=1.10.0
```

---

## Example Output

For two recipes on the same day:

**Input:**
- Recipe A: Roast Chicken (preheat, season, roast 40min, rest)
- Recipe B: Salad (dice onion, chop lettuce, rinse cucumber, mix dressing, toss)

**Without LLM (keyword heuristics):**
```
1. Preheat oven                    5 min
2. Season chicken                  3 min
3. Dice onion                      3 min  ← NOT batched (different keyword)
4. Chop lettuce                    3 min  ← NOT batched
5. Rinse cucumber                  2 min  ← NOT batched (different keyword)
6. Roast chicken                  40 min
7. Mix dressing                    3 min
8. Toss salad                      2 min
9. Rest meat                       5 min

Total: 66 min (sequential)
Batching savings: 0 min
Parallel savings: 0 min
```

**With LLM (semantic normalization + parallel scheduling):**
```
1. Preheat oven                    5 min
2. Season chicken                  3 min
3. Chop onion and lettuce          4 min  ← BATCHED (both action_type="chop")
4. Wash cucumber                   2 min  ← action_type="wash"
5. Roast chicken                  40 min
   └── While roasting:
       • Mix dressing              3 min  ← PARALLEL
       • Toss salad                2 min  ← PARALLEL
6. Rest meat                       5 min

Total: 54 min (wall-clock)
Batching savings: 2 min (combined chop steps)
Parallel savings: 10 min (tasks during roast)
Total saved: 12 min
```
