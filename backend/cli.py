"""
CLI interface for PrepPilot adaptive engine demonstration.
"""
import click
import json
from datetime import date, timedelta
from uuid import uuid4
from pathlib import Path

from backend.models.schemas import DietType, AdaptiveEngineInput
from backend.engine.meal_generator import MealGenerator
from backend.engine.freshness_tracker import FreshnessTracker
from backend.engine.adaptive_planner import AdaptivePlanner
from backend.engine.prep_optimizer import PrepOptimizer


# Global state file
STATE_FILE = Path("preppilot_state.json")


class PrepPilotCLI:
    """CLI application state manager."""

    def __init__(self):
        self.meal_generator = MealGenerator()
        self.freshness_tracker = FreshnessTracker()
        self.adaptive_planner = AdaptivePlanner(
            self.meal_generator,
            self.freshness_tracker
        )
        self.prep_optimizer = PrepOptimizer()

        self.user_id = None
        self.current_plan = None

        self.load_state()

    def load_state(self):
        """Load state from file if exists."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    state_data = json.load(f)

                # Restore user_id and plan (simplified for MVP)
                self.user_id = state_data.get('user_id')
                # In full version, would deserialize plan properly
                click.echo("✓ Loaded previous state")
            except Exception as e:
                click.echo(f"Warning: Could not load state: {e}")

    def save_state(self):
        """Save state to file."""
        try:
            state_data = {
                'user_id': str(self.user_id) if self.user_id else None,
                # In full version, would serialize plan
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            click.echo(f"Warning: Could not save state: {e}")


@click.group()
@click.pass_context
def cli(ctx):
    """PrepPilot - Adaptive Meal Prep Engine"""
    ctx.obj = PrepPilotCLI()


@cli.command()
@click.option('--days', default=3, help='Number of days to plan')
@click.pass_obj
def generate(app: PrepPilotCLI, days: int):
    """Generate a new meal plan."""
    click.echo(f"\n🍽️  Generating {days}-day low-histamine meal plan...\n")

    # Create or reuse user ID
    if app.user_id is None:
        app.user_id = uuid4()

    # Generate plan
    plan = app.meal_generator.generate_plan(
        user_id=app.user_id,
        diet_type=DietType.LOW_HISTAMINE,
        start_date=date.today(),
        days=days,
        optimize_for_reuse=True
    )

    app.current_plan = plan

    # Display plan
    click.echo("=" * 60)
    click.echo(f"MEAL PLAN: {plan.start_date} to {plan.end_date}")
    click.echo("=" * 60)

    current_date = None
    for meal in sorted(plan.meals, key=lambda m: (m.date, m.meal_type)):
        if meal.date != current_date:
            current_date = meal.date
            click.echo(f"\n📅 {current_date.strftime('%A, %B %d')}")

        click.echo(f"  {meal.meal_type.upper():12} → {meal.recipe.name}")
        click.echo(f"               ({meal.recipe.prep_time_minutes} min)")

    # Generate shopping list
    shopping_list = app.freshness_tracker.generate_shopping_list(plan)

    click.echo(f"\n\n🛒 SHOPPING LIST ({len(shopping_list)} items)")
    click.echo("-" * 60)

    # Group by category
    categorized = {}
    for name, (qty, freshness) in shopping_list.items():
        # Get category from first recipe that uses this ingredient
        category = "Other"
        for meal in plan.meals:
            for ing in meal.recipe.ingredients:
                if ing.name == name:
                    category = ing.category or "Other"
                    break

        if category not in categorized:
            categorized[category] = []

        categorized[category].append((name, qty, freshness))

    for category in sorted(categorized.keys()):
        click.echo(f"\n{category.upper()}:")
        for name, qty, freshness in sorted(categorized[category]):
            freshness_note = f"(fresh for {freshness} days)" if freshness <= 3 else ""
            click.echo(f"  • {name.replace('_', ' ').title():20} {qty:15} {freshness_note}")

    click.echo("\n✓ Plan generated! Use 'preppilot stock' to add ingredients to fridge.")

    app.save_state()


@cli.command()
@click.pass_obj
def stock(app: PrepPilotCLI):
    """Stock fridge with ingredients from current plan."""
    if app.current_plan is None:
        click.echo("❌ No active plan. Generate a plan first with 'preppilot generate'")
        return

    click.echo("\n📦 Stocking fridge with ingredients from plan...\n")

    # Stock the fridge
    fridge = app.freshness_tracker.stock_fridge_from_plan(
        user_id=app.user_id,
        meal_plan=app.current_plan,
        purchase_date=date.today()
    )

    click.echo(f"✓ Added {len(fridge.items)} ingredients to fridge")

    # Show fridge state
    _display_fridge(fridge)

    app.save_state()


@cli.command()
@click.pass_obj
def fridge(app: PrepPilotCLI):
    """View current fridge state."""
    if app.user_id is None:
        click.echo("❌ No active user. Generate a plan first.")
        return

    fridge = app.freshness_tracker.get_fridge_state(app.user_id)

    if fridge is None or not fridge.items:
        click.echo("\n🧊 Fridge is empty. Use 'preppilot stock' to add ingredients.")
        return

    # Apply decay
    fridge = app.freshness_tracker.apply_daily_decay(app.user_id)

    _display_fridge(fridge)


def _display_fridge(fridge):
    """Helper to display fridge state."""
    click.echo("\n🧊 FRIDGE STATE")
    click.echo("=" * 60)

    # Categorize by freshness
    urgent = fridge.get_expiring_soon(1)
    soon = [i for i in fridge.items if 1 < i.days_remaining <= 2]
    fresh = [i for i in fridge.items if i.days_remaining > 2]

    if urgent:
        click.echo("\n🚨 URGENT (use today!):")
        for item in urgent:
            click.echo(f"  • {item.ingredient_name.replace('_', ' ').title():20} {item.quantity:15} ({item.days_remaining} days)")

    if soon:
        click.echo("\n⚠️  EXPIRING SOON (1-2 days):")
        for item in soon:
            click.echo(f"  • {item.ingredient_name.replace('_', ' ').title():20} {item.quantity:15} ({item.days_remaining} days)")

    if fresh:
        click.echo("\n✓ FRESH (3+ days):")
        for item in fresh:
            click.echo(f"  • {item.ingredient_name.replace('_', ' ').title():20} {item.quantity:15} ({item.days_remaining} days)")

    summary = app.freshness_tracker.get_freshness_summary(fridge.user_id)
    click.echo(f"\nTotal items: {summary['total_items']}")


@cli.command()
@click.argument('meal_date', type=click.DateTime(formats=['%Y-%m-%d']))
@click.argument('meal_type', type=click.Choice(['breakfast', 'lunch', 'dinner']))
@click.argument('status', type=click.Choice(['done', 'skipped']))
@click.pass_obj
def mark_prep(app: PrepPilotCLI, meal_date, meal_type: str, status: str):
    """Mark a meal prep as done or skipped."""
    if app.current_plan is None:
        click.echo("❌ No active plan.")
        return

    target_date = meal_date.date()

    from backend.models.schemas import PrepStatus

    # Find the meal
    found = False
    for meal in app.current_plan.meals:
        if meal.date == target_date and meal.meal_type == meal_type:
            if status == 'done':
                meal.prep_status = PrepStatus.DONE
                # Remove ingredients from fridge
                app.freshness_tracker.remove_used_ingredients(
                    app.user_id,
                    meal.recipe.ingredients
                )
                click.echo(f"✓ Marked {meal_type} on {target_date} as DONE")
                click.echo(f"  Recipe: {meal.recipe.name}")
            else:
                meal.prep_status = PrepStatus.SKIPPED
                click.echo(f"⚠️  Marked {meal_type} on {target_date} as SKIPPED")
                click.echo(f"  Recipe: {meal.recipe.name}")

            found = True
            break

    if not found:
        click.echo(f"❌ No {meal_type} found on {target_date}")

    app.save_state()


@cli.command()
@click.pass_obj
def adapt(app: PrepPilotCLI):
    """Trigger adaptive replanning after missed preps."""
    if app.current_plan is None:
        click.echo("❌ No active plan. Generate a plan first.")
        return

    click.echo("\n🧠 Analyzing plan and triggering adaptive replanning...\n")

    current_date = date.today()

    # Detect missed preps
    missed_preps = app.adaptive_planner.detect_missed_preps(app.current_plan, current_date)

    if not missed_preps:
        click.echo("✓ No missed preps detected. Plan is on track!")
        return

    click.echo(f"⚠️  Detected {len(missed_preps)} missed prep day(s): {', '.join(str(d) for d in missed_preps)}\n")

    # Get fridge state
    fridge = app.freshness_tracker.get_fridge_state(app.user_id)

    # Create adaptive engine input
    input_data = AdaptiveEngineInput(
        user_id=app.user_id,
        diet_type=DietType.LOW_HISTAMINE,
        current_plan=app.current_plan,
        fridge_state=fridge or app.freshness_tracker.create_fridge_state(app.user_id),
        missed_preps=missed_preps,
        current_date=current_date
    )

    # Run adaptive planner
    output = app.adaptive_planner.adapt_plan(input_data)

    # Display results
    click.echo("=" * 60)
    click.echo("ADAPTED PLAN")
    click.echo("=" * 60)

    # Show adaptation summary
    if output.adaptation_summary:
        click.echo("\n📋 CHANGES MADE:")
        for i, adaptation in enumerate(output.adaptation_summary, 1):
            click.echo(f"\n{i}. {adaptation.type.upper()}")
            if adaptation.original_meal:
                click.echo(f"   Original: {adaptation.original_meal}")
            if adaptation.new_meal:
                click.echo(f"   New:      {adaptation.new_meal}")
            click.echo(f"   Reason:   {adaptation.reason}")

    # Show new plan
    click.echo("\n\n📅 NEW MEAL SCHEDULE:")
    current_date_display = None
    for meal in sorted(output.new_plan.meals, key=lambda m: (m.date, m.meal_type)):
        if meal.date != current_date_display:
            current_date_display = meal.date
            click.echo(f"\n{current_date_display.strftime('%A, %B %d')}")

        click.echo(f"  {meal.meal_type.upper():12} → {meal.recipe.name} ({meal.recipe.prep_time_minutes} min)")

    # Show grocery adjustments
    if output.grocery_adjustments:
        click.echo("\n\n🛒 GROCERY ADJUSTMENTS:")
        for adjustment in output.grocery_adjustments:
            click.echo(f"  • {adjustment}")

    # Show priority ingredients
    if output.priority_ingredients:
        click.echo("\n\n⚠️  PRIORITY INGREDIENTS (use soon!):")
        for ingredient in output.priority_ingredients:
            click.echo(f"  • {ingredient.replace('_', ' ').title()}")

    click.echo(f"\n\n⏱️  Estimated recovery time: {output.estimated_recovery_time_minutes} minutes")

    # Update current plan
    app.current_plan = output.new_plan
    app.save_state()

    click.echo("\n✓ Plan adapted successfully!")


@cli.command()
@click.argument('prep_date', type=click.DateTime(formats=['%Y-%m-%d']))
@click.pass_obj
def optimize(app: PrepPilotCLI, prep_date):
    """Show optimized prep sequence for a specific date."""
    if app.current_plan is None:
        click.echo("❌ No active plan. Generate a plan first.")
        return

    target_date = prep_date.date()

    click.echo(f"\n⚙️  Optimizing prep sequence for {target_date.strftime('%A, %B %d')}...\n")

    timeline = app.prep_optimizer.optimize_meal_prep(app.current_plan, target_date)

    if not timeline.steps:
        click.echo(f"No meals planned for {target_date}")
        return

    click.echo("=" * 60)
    click.echo("OPTIMIZED PREP TIMELINE")
    click.echo("=" * 60)

    click.echo(f"\nTotal time: {timeline.total_time_minutes} minutes")
    if timeline.batched_savings_minutes > 0:
        click.echo(f"Time saved through batching: {timeline.batched_savings_minutes} minutes ✨")

    click.echo(f"\n📝 PREP STEPS ({len(timeline.steps)} steps):\n")

    for step in timeline.steps:
        batch_indicator = "🔄" if step.can_batch else "  "
        click.echo(f"{step.step_number:2}. {batch_indicator} {step.action}")
        click.echo(f"      ({step.duration_minutes} min)")


if __name__ == '__main__':
    cli()
