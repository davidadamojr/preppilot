**Goal:** Build the Next.js + Tailwind front-end.

**Prompt:**

Design the **PrepPilot web app** with calm, adaptive UX for real kitchens.

### Main Pages
1. **Plan View:**
   - Shows 3-day rolling plan with visual prep timeline.
   - Buttons: Mark as Done, Skip, Adapt.
   - PDF export option.
2. **Fridge View:**
   - Ingredient inventory with freshness meters.
   - “Use soon” highlighting.
3. **Catch-Up View:**
   - Adaptive suggestions post missed preps.
   - Change explanations and next actions.

### Design Principles
- Minimalist, tablet-friendly layout.
- Large buttons, clear copy, calm palette.
- Microcopy emphasizes encouragement: *“Skipped Tuesday? Let’s adjust.”*
- Use `shadcn/ui` for consistency.

### Integration Targets
- Connect with FastAPI endpoints.
- Use React Query for async data.
- Generate timeline visual with lightweight chart lib (e.g. Recharts).
