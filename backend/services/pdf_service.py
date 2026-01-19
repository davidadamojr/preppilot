"""
PDF generation service for PrepPilot meal plans and prep timelines.

Uses ReportLab for PDF creation with a clean, kitchen-friendly design.
"""
from datetime import date
from io import BytesIO
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)
from sqlalchemy.orm import Session

from backend.db.models import User, MealPlan
from backend.models.schemas import (
    MealPlan as SchemaMealPlan,
    AdaptiveEngineOutput,
    FridgeState,
    PrepStatus,
)
from backend.services.meal_service import db_meal_plan_to_schema


class PDFService:
    """
    Service for generating PDF documents from meal plans.

    Uses ReportLab to create kitchen-friendly PDF documents including
    meal plan summaries, shopping lists, prep timelines, and catch-up guides.
    """

    # Color palette - calm, kitchen-friendly
    PRIMARY_COLOR = colors.HexColor("#2D5A27")  # Forest green
    SECONDARY_COLOR = colors.HexColor("#6B8E23")  # Olive
    ACCENT_COLOR = colors.HexColor("#F5F5DC")  # Beige background
    URGENT_COLOR = colors.HexColor("#D2691E")  # Chocolate (for urgent items)

    def __init__(self, db: Session):
        """
        Initialize the PDF service.

        Args:
            db: SQLAlchemy database session for loading related data.
        """
        self.db = db
        self._setup_styles()

    def _setup_styles(self) -> None:
        """
        Configure PDF text styles.

        Sets up custom paragraph styles for titles, headings, body text,
        and special formatting like urgent items and adaptation notes.
        """
        self.styles = getSampleStyleSheet()

        # Title style
        self.styles.add(ParagraphStyle(
            'PrepPilotTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.PRIMARY_COLOR,
            spaceAfter=20,
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.PRIMARY_COLOR,
            spaceBefore=12,
            spaceAfter=8,
        ))

        # Day heading
        self.styles.add(ParagraphStyle(
            'DayHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=self.SECONDARY_COLOR,
            spaceBefore=10,
            spaceAfter=6,
        ))

        # Normal body text
        self.styles.add(ParagraphStyle(
            'PrepBody',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
        ))

        # Urgent/highlight text
        self.styles.add(ParagraphStyle(
            'Urgent',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.URGENT_COLOR,
            fontName='Helvetica-Bold',
        ))

        # Adaptation note
        self.styles.add(ParagraphStyle(
            'AdaptationNote',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.SECONDARY_COLOR,
            fontStyle='italic',
            leftIndent=20,
        ))

    def generate_meal_plan_pdf(
        self,
        plan: MealPlan,
        include_shopping_list: bool = True,
        adaptation_notes: Optional[List[str]] = None,
    ) -> bytes:
        """
        Generate a PDF document for a meal plan.

        Args:
            plan: Database MealPlan object
            include_shopping_list: Whether to include ingredient list
            adaptation_notes: Optional list of adaptation explanations

        Returns:
            PDF as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Convert to schema for easier access
        schema_plan = db_meal_plan_to_schema(plan, self.db)

        story = []

        # Title
        story.append(Paragraph("PrepPilot Meal Plan", self.styles['PrepPilotTitle']))

        # Date range
        date_range = f"{schema_plan.start_date.strftime('%B %d')} - {schema_plan.end_date.strftime('%B %d, %Y')}"
        story.append(Paragraph(date_range, self.styles['PrepBody']))
        story.append(Spacer(1, 12))

        # Adaptation notes (if any)
        if adaptation_notes:
            story.append(Paragraph("Plan Updates", self.styles['SectionHeading']))
            for note in adaptation_notes:
                story.append(Paragraph(f"• {note}", self.styles['AdaptationNote']))
            story.append(Spacer(1, 12))

        # Meals by day
        story.append(Paragraph("Daily Meals", self.styles['SectionHeading']))

        # Group meals by date
        meals_by_date = {}
        for meal in schema_plan.meals:
            if meal.date not in meals_by_date:
                meals_by_date[meal.date] = []
            meals_by_date[meal.date].append(meal)

        for meal_date in sorted(meals_by_date.keys()):
            day_meals = meals_by_date[meal_date]
            day_name = meal_date.strftime('%A, %B %d')
            story.append(Paragraph(day_name, self.styles['DayHeading']))

            # Create table for meals
            table_data = [['Meal', 'Recipe', 'Prep Time', 'Status']]
            for meal in sorted(day_meals, key=lambda m: ['breakfast', 'lunch', 'dinner'].index(m.meal_type)):
                status_text = self._format_status(meal.prep_status)
                table_data.append([
                    meal.meal_type.capitalize(),
                    meal.recipe.name,
                    f"{meal.recipe.prep_time_minutes} min",
                    status_text,
                ])

            table = Table(table_data, colWidths=[1.2*inch, 3*inch, 1*inch, 1*inch])
            table.setStyle(self._get_meal_table_style())
            story.append(table)
            story.append(Spacer(1, 8))

        # Shopping list
        if include_shopping_list:
            story.append(PageBreak())
            story.append(Paragraph("Shopping List", self.styles['SectionHeading']))

            shopping_list = self._generate_shopping_list(schema_plan)
            ingredients_by_category = self._group_by_category(shopping_list)

            for category, items in sorted(ingredients_by_category.items()):
                story.append(Paragraph(category.capitalize(), self.styles['DayHeading']))

                list_items = []
                for item_name, quantity in sorted(items.items()):
                    list_items.append(ListItem(
                        Paragraph(f"{item_name}: {quantity}", self.styles['PrepBody']),
                        bulletColor=self.SECONDARY_COLOR,
                    ))

                story.append(ListFlowable(list_items, bulletType='bullet', start='•'))
                story.append(Spacer(1, 6))

        # Prep timeline
        story.append(PageBreak())
        story.append(Paragraph("Prep Timeline", self.styles['SectionHeading']))
        story.append(Paragraph(
            "Batch similar tasks together to save time:",
            self.styles['PrepBody']
        ))
        story.append(Spacer(1, 8))

        timeline = self._generate_prep_timeline(schema_plan)
        for step_group in timeline:
            story.append(Paragraph(
                f"<b>{step_group['action']}</b>",
                self.styles['PrepBody']
            ))
            for detail in step_group['details']:
                story.append(Paragraph(f"  • {detail}", self.styles['PrepBody']))
            story.append(Spacer(1, 6))

        # Build PDF
        doc.build(story)
        return buffer.getvalue()

    def generate_catch_up_pdf(
        self,
        plan: MealPlan,
        adaptation_output: AdaptiveEngineOutput,
        fridge_state: FridgeState,
    ) -> bytes:
        """
        Generate a catch-up PDF after missed preps.

        Args:
            plan: Updated MealPlan
            adaptation_output: Output from adaptive planner
            fridge_state: Current fridge state

        Returns:
            PDF as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story = []

        # Title
        story.append(Paragraph("PrepPilot Catch-Up Plan", self.styles['PrepPilotTitle']))
        story.append(Paragraph(
            "Your plan has been adjusted — here's how to get back on track.",
            self.styles['PrepBody']
        ))
        story.append(Spacer(1, 12))

        # Adaptation summary
        story.append(Paragraph("What Changed", self.styles['SectionHeading']))

        for reason in adaptation_output.adaptation_summary:
            note = f"{reason.affected_date.strftime('%A')}: {reason.reason}"
            if reason.original_meal and reason.new_meal:
                note += f" ({reason.original_meal} → {reason.new_meal})"
            story.append(Paragraph(f"• {note}", self.styles['AdaptationNote']))

        story.append(Spacer(1, 12))

        # Priority ingredients (urgent)
        if adaptation_output.priority_ingredients:
            story.append(Paragraph("Use These First", self.styles['SectionHeading']))
            story.append(Paragraph(
                "These ingredients need to be used soon:",
                self.styles['PrepBody']
            ))

            for ingredient in adaptation_output.priority_ingredients:
                story.append(Paragraph(f"⚠ {ingredient}", self.styles['Urgent']))

            story.append(Spacer(1, 12))

        # Recovery time
        story.append(Paragraph("Recovery Plan", self.styles['SectionHeading']))
        story.append(Paragraph(
            f"Estimated catch-up time: <b>{adaptation_output.estimated_recovery_time_minutes} minutes</b>",
            self.styles['PrepBody']
        ))
        story.append(Spacer(1, 12))

        # Updated meal plan
        schema_plan = db_meal_plan_to_schema(plan, self.db)

        story.append(Paragraph("Updated Meals", self.styles['SectionHeading']))

        # Only show upcoming meals
        today = date.today()
        upcoming_meals = [m for m in schema_plan.meals if m.date >= today]

        meals_by_date = {}
        for meal in upcoming_meals:
            if meal.date not in meals_by_date:
                meals_by_date[meal.date] = []
            meals_by_date[meal.date].append(meal)

        for meal_date in sorted(meals_by_date.keys()):
            day_meals = meals_by_date[meal_date]
            day_name = meal_date.strftime('%A, %B %d')
            story.append(Paragraph(day_name, self.styles['DayHeading']))

            table_data = [['Meal', 'Recipe', 'Prep Time']]
            for meal in sorted(day_meals, key=lambda m: ['breakfast', 'lunch', 'dinner'].index(m.meal_type)):
                table_data.append([
                    meal.meal_type.capitalize(),
                    meal.recipe.name,
                    f"{meal.recipe.prep_time_minutes} min",
                ])

            table = Table(table_data, colWidths=[1.2*inch, 3.5*inch, 1*inch])
            table.setStyle(self._get_meal_table_style())
            story.append(table)
            story.append(Spacer(1, 8))

        # Grocery adjustments
        if adaptation_output.grocery_adjustments:
            story.append(Paragraph("Grocery Changes", self.styles['SectionHeading']))
            for adj in adaptation_output.grocery_adjustments:
                story.append(Paragraph(f"• {adj}", self.styles['PrepBody']))

        doc.build(story)
        return buffer.getvalue()

    def _format_status(self, status: PrepStatus) -> str:
        """
        Format prep status for display.

        Args:
            status: PrepStatus enum value.

        Returns:
            Human-readable status string with icon.
        """
        if status == PrepStatus.DONE:
            return "✓ Done"
        elif status == PrepStatus.SKIPPED:
            return "⊘ Skipped"
        return "○ Pending"

    def _get_meal_table_style(self) -> TableStyle:
        """
        Get table style for meal display.

        Returns:
            TableStyle with consistent formatting for meal tables.
        """
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ])

    def _generate_shopping_list(self, plan: SchemaMealPlan) -> dict:
        """
        Generate aggregated shopping list from meal plan.

        Returns:
            Dict mapping ingredient name to total quantity
        """
        shopping = {}

        for meal in plan.meals:
            for ingredient in meal.recipe.ingredients:
                name = ingredient.name
                if name in shopping:
                    # Simple aggregation - just append quantities
                    shopping[name] = f"{shopping[name]}, {ingredient.quantity}"
                else:
                    shopping[name] = ingredient.quantity

        return shopping

    def _group_by_category(self, shopping_list: dict) -> dict:
        """
        Group shopping list items by category.

        Returns:
            Dict mapping category to dict of items
        """
        # Simple categorization based on common ingredients
        categories = {
            'produce': ['carrot', 'onion', 'garlic', 'lettuce', 'spinach', 'kale',
                       'zucchini', 'cucumber', 'pepper', 'tomato', 'apple', 'pear',
                       'mango', 'blueberry', 'parsley', 'basil', 'thyme', 'oregano',
                       'cilantro', 'mint', 'ginger', 'sweet potato', 'potato', 'broccoli'],
            'protein': ['chicken', 'turkey', 'beef', 'lamb', 'fish', 'salmon', 'cod',
                       'shrimp', 'egg', 'tofu'],
            'dairy': ['milk', 'butter', 'cheese', 'cream', 'yogurt'],
            'grains': ['rice', 'quinoa', 'oat', 'bread', 'pasta', 'flour'],
            'pantry': ['oil', 'vinegar', 'salt', 'honey', 'maple', 'coconut'],
        }

        grouped = {}

        for item, quantity in shopping_list.items():
            item_lower = item.lower()
            assigned_category = 'other'

            for category, keywords in categories.items():
                if any(keyword in item_lower for keyword in keywords):
                    assigned_category = category
                    break

            if assigned_category not in grouped:
                grouped[assigned_category] = {}
            grouped[assigned_category][item] = quantity

        return grouped

    def _generate_prep_timeline(self, plan: SchemaMealPlan) -> List[dict]:
        """
        Generate optimized prep timeline with batched tasks.

        Returns:
            List of step groups with actions and details
        """
        # Group common prep actions across meals
        prep_groups = {
            'wash_and_prep': [],
            'chop_dice': [],
            'marinate': [],
            'preheat': [],
            'cook': [],
        }

        for meal in plan.meals:
            for step in meal.recipe.prep_steps:
                step_lower = step.lower()

                if any(word in step_lower for word in ['wash', 'rinse', 'clean']):
                    prep_groups['wash_and_prep'].append(f"{meal.recipe.name}: {step}")
                elif any(word in step_lower for word in ['chop', 'dice', 'slice', 'mince']):
                    prep_groups['chop_dice'].append(f"{meal.recipe.name}: {step}")
                elif any(word in step_lower for word in ['marinate', 'season', 'rub']):
                    prep_groups['marinate'].append(f"{meal.recipe.name}: {step}")
                elif any(word in step_lower for word in ['preheat', 'heat']):
                    prep_groups['preheat'].append(f"{meal.recipe.name}: {step}")
                else:
                    prep_groups['cook'].append(f"{meal.recipe.name}: {step}")

        # Convert to timeline format
        timeline = []

        action_names = {
            'wash_and_prep': 'Wash & Prep Ingredients',
            'chop_dice': 'Chop & Dice',
            'marinate': 'Marinate & Season',
            'preheat': 'Preheat Oven/Stovetop',
            'cook': 'Cook',
        }

        for group_key in ['wash_and_prep', 'chop_dice', 'marinate', 'preheat', 'cook']:
            if prep_groups[group_key]:
                timeline.append({
                    'action': action_names[group_key],
                    'details': prep_groups[group_key],
                })

        return timeline
