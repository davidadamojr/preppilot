# Role
You are an expert Senior Frontend Developer and Conversion Rate Optimization (CRO) specialist.

# Goal
Build a high-fidelity "Fake Door" pretotype landing page for a SaaS concept for PrepPilot.
The goal is to validate interest in a Low-Histamine Meal Planner by collecting emails for a waitlist.

# Tech Stack requirements
- Framework: Next.js 14 (App Router)
- Styling: Tailwind CSS
- Icons: Lucide React
- Components: Shadcn UI (or similar clean aesthetic)
- Animation: Framer Motion (subtle entrance animations only)
- Deployment target: Vercel

The tech stack should preferably match what already exists.

# Design Aesthetic
- **Tone:** Clinical, trustworthy, modern, calm.
- **Color Palette:**
  - Primary: Sage Green (signifying freshness/health).
  - Accent: Alert Orange (used sparingly for "Expiration" visual metaphors).
  - Background: Clean White/Off-White.
- **Typography:** Sans-serif, highly readable (Inter or similar).

# Page Structure & Copy (Strict Implementation)

## 1. Navbar
- Logo: "PrepPilot" (Simple text or icon)
- Right side: "Join Beta" button (Scroll to Hero).

## 2. Hero Section (Above the Fold)
- **Badge:** "Finally: A Meal Planner for Histamine Intolerance"
- **Headline:** "Cook Fresh. Stay Safe."
- **Subheadline:** "The first meal planner that tracks **ingredient age** in real-time. We prioritize your recipes based on what's in your fridge, so you use food before histamine levels rise."
- **Primary CTA:** Input field [Enter email address] + Button [Request Early Access].
- **Social Proof:** "Smart inventory tracking for Low-Histamine & MAST diets."

## 3. The Problem Section (Pain Agitation)
- **Title:** "The Invisible Timer in Your Fridge."
- **3 Cards:**
  1. **Icon:** ShoppingBag. **Title:** "Ingredients Age Quickly." **Text:** "High-protein foods like fish and meat build histamine the longer they sit raw."
  2. **Icon:** AlertTriangle. **Title:** "Waste & Fear." **Text:** "Throwing out food because you 'aren't sure' if it's safe anymore is expensive and stressful."
  3. **Icon:** CalendarClock. **Title:** "Poor Planning." **Text:** "Buying fresh food but cooking it 3 days later is a recipe for a flare-up."

## 4. The Solution/Feature Section
- **Title:** "Just-in-Time Meal Planning."
- **Feature 1 (The Hook):** "Smart Ingredient Tracking." Description: "Log your groceries, and PrepPilot monitors their age. It alerts you to cook high-risk items (meat/fish) first."
- **Feature 2:** "Freshness-Based Recipes." Description: "The algorithm suggests meals based on what needs to be used *today*, not a random schedule."
- **Feature 3:** "Strict Exclusion Filters." Description: "Filter for Low-Histamine, Gluten-Free, Dairy-Free, and 18+ other allergens simultaneously."

## 5. The "How It Works" (Visual Concept)
- Create a visual representation (using CSS/Divs) of a "Digital Pantry List."
- Show items like "Fresh Salmon" with a timer saying "Use within 12 hours" and "Zucchini" saying "Safe for 3 days."
- Caption: "Prioritize your cooking based on safety."

## 6. Footer
- Simple copyright.
- "PrepPilot is a concept in development."

# Functional Requirements
1. **The Form:** The email capture form must be functional.
   - Use a simple state to handle submission.
   - On Submit: Show a loading spinner for 1.5s.
   - On Success: Replace form with a Success Message: "You're on the list! We'll notify you when the ingredient tracker is live."
   - (Optional) Console log the email so I can hook it up to a backend later.
2. **Responsiveness:** Must look perfect on Mobile (stack columns) and Desktop.

# Output
Please write the full code. If multiple files are needed, structure them clearly. Focus on the `page.tsx` and `layout.tsx`.

Also, create a suite of branding images i.e., logos, og-images, social media images, favicons, etc.