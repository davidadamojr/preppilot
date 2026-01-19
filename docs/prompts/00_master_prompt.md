Here’s the **best possible Claude Code prompt** to guide development of **PrepPilot**, the *adaptive meal prep autopilot* that dynamically adjusts to missed preps and changing schedules — starting with low-histamine diets but extensible to others.

This prompt emphasizes **architecture clarity**, **UX excellence**, and **incremental deliverability** — leaving the coding specifics to Claude Code’s judgment.

---

## 🧠 Claude Code MVP Prompt — *PrepPilot: Adaptive Meal Prep Engine*

You are building **PrepPilot**, an AI-powered meal planning and prep optimization web app.
The goal is to make meal prep **efficient, adaptive, and diet-aware**, starting with low-histamine diets.

---

### 🎯 **Product Purpose**

PrepPilot helps users who follow restrictive diets (starting with *low-histamine*) plan, cook, and adapt their weekly meals.
Unlike static meal planners, PrepPilot intelligently adjusts meal plans when users **miss prep days**, **delay cooking**, or **have leftover ingredients**.

It acts like a kitchen autopilot:

> “You skipped Tuesday’s prep? No problem — here’s how to catch up tonight with what’s still fresh.”

---

### 🧩 **Core Capabilities to Build**

#### 1. **Diet-Aware Meal Generator**

* Generate meal plans based on a user’s diet profile (starting with low-histamine).
* Each recipe includes: name, ingredients, prep steps, prep time, and freshness lifespan per ingredient.
* Output a 3-day meal plan with breakfast, lunch, dinner, and optional snacks.
* Tag each recipe with a “reusability index” to prioritize shared ingredients.

#### 2. **Prep Sequence Optimizer**

* Group and order cooking/prep steps across meals to minimize total prep time.
  Example: “Chop onions once for 3 meals,” or “Bake all sweet potatoes at once.”
* Output should include a **timeline view** and **printable PDF** of steps.
* Reuse ingredients intelligently (minimize waste, maximize freshness).

#### 3. **Adaptive Meal Scheduler**

* Maintain a schedule model: `{date, meals_planned, prep_done, ingredients_remaining}`.
* Detect when a prep is skipped or delayed.
* Automatically re-sequence future plans:

  * Prioritize perishables.
  * Suggest fallback simplified meals (“one-pan recovery mode”).
  * Adjust grocery list accordingly.
* Display adaptation transparently to user (“Wednesday’s prep skipped → simplified Thursday plan”).

#### 4. **Ingredient + Freshness Tracker**

* Track current inventory of ingredients and their remaining freshness days.
* Decay freshness daily and alert when an item needs to be used soon.
* Allow manual updates (“mark ingredient used,” “add new ingredient”).

#### 5. **User-Facing Features**

* **Dashboard Tabs:**

  1. **Plan View:** Active schedule, prep timeline, and progress tracker.
  2. **Fridge View:** Ingredient inventory with freshness countdown.
  3. **Catch-Up View:** Adaptive suggestions after missed preps.
* **Actions:** Mark a meal as done/skipped, regenerate plan, print adaptive PDF.
* **Calendar Sync:** Optional link to Google Calendar for prep reminders.

---

### 🧱 **Tech Stack (Recommended)**

* **Frontend:** Next.js + Tailwind CSS

  * Focus on clean, calm design optimized for kitchen/tablet use.
  * Use shadcn/ui components where suitable.
* **Backend:** FastAPI (Python)

  * Expose REST endpoints:

    * `/generate_plan`
    * `/mark_prep`
    * `/get_fridge_state`
    * `/adapt_plan`
  * Use SQLAlchemy ORM with Postgres (or Supabase).
  * Recipe data stored as structured JSON with tags and metadata.
* **Background Jobs:** Celery or lightweight cron tasks for freshness decay + notifications.
* **PDF Generator:** `reportlab` — weekly plan + prep timeline printable output.
* **Auth:** Clerk or Supabase Auth (minimal friction).
* **Deployment:**

  * Frontend on Vercel
  * Backend on Fly.io or Render
  * DB on Supabase or Neon.tech

---

### 🧭 **Architecture Guidance**

* Treat recipes as composable building blocks with metadata:

  ```json
  {
    "name": "Herbed Chicken Bowl",
    "diet_tags": ["low_histamine"],
    "ingredients": [
      {"name": "chicken_thighs", "freshness_days": 3, "quantity": "500g"},
      {"name": "parsley", "freshness_days": 2, "quantity": "1 bunch"}
    ],
    "prep_steps": ["Chop parsley", "Marinate chicken", "Bake for 25 min"],
    "prep_time_minutes": 40,
    "reusability_index": 0.8
  }
  ```
* Keep the “adaptive logic” modular:

  * Core algorithm: `adapt_plan(previous_plan, missed_day, fridge_state)`
  * Returns: updated schedule, simplified meals, and new shopping list.
* Store user-specific states in one canonical object:

  ```json
  {
    "user_id": "uuid",
    "diet_type": "low_histamine",
    "plan": {...},
    "fridge": {...},
    "calendar": {...}
  }
  ```
* Build the adaptive layer with **state diffs** (compare planned vs. actual), not full regeneration.
* Prioritize data transparency — show users *why* changes happened (“we replaced salmon with turkey due to freshness”).

---

### 🔁 **User Experience Priorities**

* **Flow > Features.** Every screen should move user from “uncertainty” → “clarity.”
* Use calm color palettes, large touch targets, and readable print layouts.
* Default to 3-day plans for fast iteration; allow 7-day upgrade later.
* Use progressive disclosure: first, generate → then customize → then adapt.
* Provide meaningful microcopy:

  * “You skipped yesterday’s prep — here’s a faster catch-up version.”
  * “These carrots are about to expire — we’ll use them tonight.”

---

### 📈 **Metrics & Validation**

* Track:

  * Number of generated plans
  * Meals skipped vs. completed
  * Adaptations successfully followed through
* **MVP success metric:**
  70% of users who miss a prep still complete an adapted meal within 48 hours.

---

### 🧪 **Development Phases**

#### Phase 1 — Local Engine Prototype

* Build the recipe engine + adaptive logic in isolation (CLI).
* Produce 3-day PDF output from sample user JSON.

#### Phase 2 — Backend API

* Wrap adaptive logic in FastAPI endpoints.
* Implement database models for recipes, users, and fridge items.

#### Phase 3 — Frontend UX

* Build dashboard with tabs for Plan, Fridge, and Catch-Up.
* Add “skip” and “adapt” buttons that trigger backend logic.

#### Phase 4 — Beta Polish

* Add email reminders (“missed prep detected”).
* Polish PDF layout and timeline visualizations.
* Deploy to production and onboard 10 low-histamine beta users.

---

### 💡 **Stretch Goals (Post-MVP)**

* Expand to other diets: FODMAP, fructose-free, AIP, gluten-free.
* Personalized prep-time learning — the system estimates your real prep speed.
* Social plan sharing (“send my adaptive plan to a friend”).
* AI voice agent (“I skipped tonight — what can I cook instead?”).

---

### ✅ **Design Ethos**

* “Plans that adapt to your life — and your diet.”
* The product should feel like *relief*: fewer decisions, less guilt, more flow.
* Treat adaptation as a superpower, not a failure.

---

**Your task:**
Implement the PrepPilot MVP according to this architecture and UX vision.
Focus on delivering a clean, adaptive experience first; do not overbuild.
Leave complex AI features (LLM meal generation, NLP ingredient parsing) for post-MVP.
Deliver a production-ready app that a solo founder can launch and test within 4–6 weeks.

