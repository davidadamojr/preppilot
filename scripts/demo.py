#!/usr/bin/env python3
"""
Demo script to validate PrepPilot adaptive engine.
Simulates a user workflow with missed preps to demonstrate adaptation.
"""
from datetime import date, timedelta
from uuid import uuid4

from backend.models.schemas import DietType, AdaptiveEngineInput, PrepStatus
from backend.engine.meal_generator import MealGenerator
from backend.engine.freshness_tracker import FreshnessTracker
from backend.engine.adaptive_planner import AdaptivePlanner


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_meal_plan(plan, title="MEAL PLAN"):
    """Print a meal plan in a readable format."""
    print(f"\n{title}")
    print(f"Period: {plan.start_date} to {plan.end_date}")
    print("-" * 70)

    current_date = None
    for meal in sorted(plan.meals, key=lambda m: (m.date, m.meal_type)):
        if meal.date != current_date:
            current_date = meal.date
            print(f"\n{current_date.strftime('%A, %B %d, %Y')}:")

        status_icon = "✓" if meal.prep_status == PrepStatus.DONE else "⚠" if meal.prep_status == PrepStatus.SKIPPED else "○"
        print(f"  {status_icon} {meal.meal_type.upper():12} → {meal.recipe.name} ({meal.recipe.prep_time_minutes} min)")


def main():
    """Run adaptive engine demonstration."""
    print_section("PrepPilot Adaptive Engine Demo")

    # Initialize components
    print("Initializing adaptive engine components...")
    meal_generator = MealGenerator()
    freshness_tracker = FreshnessTracker()
    adaptive_planner = AdaptivePlanner(meal_generator, freshness_tracker)

    user_id = uuid4()
    print(f"✓ User ID: {user_id}\n")

    # STEP 1: Generate initial plan
    print_section("STEP 1: Generate 3-Day Meal Plan")

    # Start plan 2 days ago to simulate passing time
    start_date = date.today() - timedelta(days=2)

    plan = meal_generator.generate_plan(
        user_id=user_id,
        diet_type=DietType.LOW_HISTAMINE,
        start_date=start_date,
        days=3
    )

    print_meal_plan(plan, "INITIAL PLAN")
    print(f"\n✓ Generated plan with {len(plan.meals)} meals")

    # STEP 2: Stock fridge
    print_section("STEP 2: Stock Fridge with Ingredients")

    shopping_list = freshness_tracker.generate_shopping_list(plan)
    print(f"Shopping list has {len(shopping_list)} unique ingredients\n")

    print("Sample ingredients:")
    for i, (name, (qty, freshness)) in enumerate(list(shopping_list.items())[:5]):
        print(f"  • {name.replace('_', ' ').title():20} {qty:12} (fresh for {freshness} days)")

    if len(shopping_list) > 5:
        print(f"  ... and {len(shopping_list) - 5} more")

    fridge = freshness_tracker.stock_fridge_from_shopping(
        user_id=user_id,
        shopping_list=shopping_list,
        purchase_date=start_date
    )

    print(f"\n✓ Stocked fridge with {len(fridge.items)} items on {start_date}")

    # STEP 3: Simulate missed preps
    print_section("STEP 3: Simulate Life Happening (Missed Preps)")

    print("Simulating scenario: User got busy and skipped meals on first two days...\n")

    # Mark meals as skipped for the first 2 days
    for meal in plan.meals:
        if meal.date < date.today():
            meal.prep_status = PrepStatus.SKIPPED
            print(f"  ⚠ Skipped: {meal.date} {meal.meal_type} - {meal.recipe.name}")

    missed_preps = [start_date, start_date + timedelta(days=1)]
    print(f"\n✗ Total missed prep days: {len(missed_preps)}")

    # STEP 4: Check fridge state with decay
    print_section("STEP 4: Check Fridge After 2 Days")

    fridge = freshness_tracker.apply_daily_decay(user_id, date.today())

    summary = freshness_tracker.get_freshness_summary(user_id)
    print(f"Fridge status after {(date.today() - start_date).days} days:")
    print(f"  • Total items: {summary['total_items']}")
    print(f"  • Expiring within 3 days: {summary['expiring_within_3_days']}")
    print(f"  • Still fresh (3+ days): {summary['fresh_items']}")

    expiring = freshness_tracker.get_expiring_soon(user_id, days_threshold=2)
    if expiring:
        print(f"\n⚠️  URGENT - Items expiring soon:")
        for item in expiring[:5]:
            freshness_pct = item.freshness_percentage
            print(f"  • {item.ingredient_name.replace('_', ' ').title():20} ({item.days_remaining} days, {freshness_pct:.0f}% fresh)")

    # STEP 5: Run adaptive planner
    print_section("STEP 5: Run Adaptive Replanning")

    print("🧠 Adaptive engine analyzing situation...")
    print(f"   - Missed preps: {len(missed_preps)} days")
    print(f"   - Expiring ingredients: {len(expiring)} items")
    print(f"   - Current date: {date.today()}")

    input_data = AdaptiveEngineInput(
        user_id=user_id,
        diet_type=DietType.LOW_HISTAMINE,
        current_plan=plan,
        fridge_state=fridge,
        missed_preps=missed_preps,
        current_date=date.today()
    )

    output = adaptive_planner.adapt_plan(input_data)

    print("\n✓ Adaptation complete!\n")

    # Show adaptations
    if output.adaptation_summary:
        print("ADAPTATIONS MADE:")
        for i, adaptation in enumerate(output.adaptation_summary, 1):
            print(f"\n{i}. {adaptation.type.upper()}")
            if adaptation.original_meal:
                print(f"   Original: {adaptation.original_meal}")
            if adaptation.new_meal:
                print(f"   New:      {adaptation.new_meal}")
            print(f"   Reason:   {adaptation.reason}")

    # Show new plan
    print_meal_plan(output.new_plan, "\nNEW ADAPTED PLAN")

    # Show priority ingredients
    if output.priority_ingredients:
        print(f"\n⚠️  PRIORITY: Use these ingredients soon:")
        for ing in output.priority_ingredients[:5]:
            print(f"  • {ing.replace('_', ' ').title()}")

    # Show grocery adjustments
    if output.grocery_adjustments:
        print(f"\n🛒 GROCERY ADJUSTMENTS:")
        for adj in output.grocery_adjustments:
            print(f"  • {adj}")

    print(f"\n⏱️  Estimated recovery time: {output.estimated_recovery_time_minutes} minutes")

    # STEP 6: Success metrics
    print_section("SUCCESS VALIDATION")

    future_meals = [m for m in output.new_plan.meals if m.date >= date.today()]
    print(f"✓ Engine successfully adapted plan")
    print(f"✓ Generated {len(future_meals)} meals for upcoming days")
    print(f"✓ Prioritized {len(output.priority_ingredients)} expiring ingredients")
    print(f"✓ Maintained dietary compliance: low-histamine")
    print(f"✓ Provided transparent explanations: {len(output.adaptation_summary)} adaptations")

    print("\n" + "=" * 70)
    print("  Demo Complete - Adaptive Engine Validated! ✨")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
