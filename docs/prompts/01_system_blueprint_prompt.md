## 01_SYSTEM_BLUEPRINT_PROMPT.md

**Goal:** Establish the full architectural vision and design ethos for PrepPilot.

**Prompt:**

You are building **PrepPilot**, an AI-powered meal planning and prep optimization platform that adapts to the user’s schedule, ingredient freshness, and dietary constraints.

### Core Product Intent
> To make diet-compliant cooking effortless, efficient, and resilient when real life gets in the way.

PrepPilot’s unique differentiator is its **adaptive prep engine**: when a user misses a cooking or prep session, the system intelligently reschedules, substitutes ingredients, or simplifies meals — keeping them compliant and on track.

### Key Principles
1. **Adaptive First** – every plan should flex around the user’s time and fridge state.
2. **Flow Over Features** – clarity and calm UX trump complexity.
3. **Real-World Awareness** – every plan accounts for perishability, prep fatigue, and leftovers.

### Core Components
- **Diet-Aware Recipe Engine**: Curated recipes tagged with dietary rules and freshness lifespans.
- **Prep Sequence Optimizer**: Generates efficient timelines by batching ingredients and steps.
- **Adaptive Scheduler**: Reacts to missed or delayed preps with simplified fallback plans.
- **Fridge Tracker**: Tracks ingredient freshness and usage over time.
- **PDF/Calendar Integration**: Printable timelines and optional calendar sync.

### Architecture Overview
```
Frontend: Next.js + Tailwind (shadcn/ui)
Backend: FastAPI (Python)
Database: Postgres (Supabase/Neon)
Background Jobs: Celery or cron
PDF Generation: reportlab
Deployment: Vercel + Fly.io
```

### MVP Success Metric
✅ 70% of users who miss a prep still complete an adapted meal within 48 hours.

### Deliverables
- Adaptive meal planner with UI for plan/fridge/catch-up views.
- Working backend with adaptive logic.
- Real user flow: skip prep → get adapted plan → cook simplified meal.
