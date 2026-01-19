"""
Utility functions for parsing and combining ingredient quantities.
Handles various quantity formats and unit conversions.
"""
import re
from typing import Tuple, Optional
from fractions import Fraction


# Common unit conversions to grams/ml (for standardization)
UNIT_CONVERSIONS = {
    # Weight
    'g': 1.0,
    'gram': 1.0,
    'grams': 1.0,
    'kg': 1000.0,
    'kilogram': 1000.0,
    'kilograms': 1000.0,
    'oz': 28.35,
    'ounce': 28.35,
    'ounces': 28.35,
    'lb': 453.59,
    'pound': 453.59,
    'pounds': 453.59,

    # Volume
    'ml': 1.0,
    'milliliter': 1.0,
    'milliliters': 1.0,
    'l': 1000.0,
    'liter': 1000.0,
    'liters': 1000.0,
    'cup': 236.59,
    'cups': 236.59,
    'tbsp': 14.79,
    'tablespoon': 14.79,
    'tablespoons': 14.79,
    'tsp': 4.93,
    'teaspoon': 4.93,
    'teaspoons': 4.93,

    # Count
    'piece': 1.0,
    'pieces': 1.0,
    'whole': 1.0,
    'item': 1.0,
    'items': 1.0,
    'clove': 1.0,
    'cloves': 1.0,
    'bunch': 1.0,
    'bunches': 1.0,
    'sprig': 1.0,
    'sprigs': 1.0,
    'stalk': 1.0,
    'stalks': 1.0,
    'head': 1.0,
    'heads': 1.0,
    'fillet': 1.0,
    'fillets': 1.0,
    'large': 1.0,
    'medium': 1.0,
    'small': 1.0,
}


def parse_quantity(quantity_str: str) -> Tuple[float, str, str]:
    """
    Parse a quantity string into amount, unit, and original string.

    Examples:
        "500g" -> (500.0, "g", "500g")
        "2 cups" -> (2.0, "cups", "2 cups")
        "1/2 cup" -> (0.5, "cup", "1/2 cup")
        "1 large" -> (1.0, "large", "1 large")
        "2-3 medium" -> (2.5, "medium", "2-3 medium")

    Args:
        quantity_str: String representation of quantity

    Returns:
        Tuple of (amount, unit, original_string)
    """
    original = quantity_str.strip()
    text = original.lower()

    # Pattern: optional number/fraction + optional unit
    # Examples: "500g", "2 cups", "1/2 cup", "1-2 medium"
    pattern = r'([\d/.]+(?:-[\d/.]+)?)\s*([a-z]+)?'
    match = re.match(pattern, text)

    if not match:
        # If no number found, treat as "1 unit" or default to the whole string
        return (1.0, text, original)

    amount_str = match.group(1)
    unit = match.group(2) if match.group(2) else 'unit'

    # Parse amount (handles fractions and ranges)
    try:
        if '-' in amount_str:
            # Range like "2-3" -> take average
            parts = amount_str.split('-')
            low = float(Fraction(parts[0]))
            high = float(Fraction(parts[1]))
            amount = (low + high) / 2.0
        else:
            # Single value or fraction
            amount = float(Fraction(amount_str))
    except:
        amount = 1.0

    return (amount, unit, original)


def normalize_to_base_unit(amount: float, unit: str) -> Tuple[float, str]:
    """
    Normalize quantity to base unit (grams for weight, ml for volume, count for items).

    Args:
        amount: Numeric amount
        unit: Unit string

    Returns:
        Tuple of (normalized_amount, base_unit)
    """
    unit_lower = unit.lower().strip()

    # Determine base unit category
    if unit_lower in ['g', 'gram', 'grams', 'kg', 'kilogram', 'kilograms', 'oz', 'ounce', 'ounces', 'lb', 'pound', 'pounds']:
        # Weight -> grams
        conversion = UNIT_CONVERSIONS.get(unit_lower, 1.0)
        return (amount * conversion, 'g')

    elif unit_lower in ['ml', 'milliliter', 'milliliters', 'l', 'liter', 'liters', 'cup', 'cups', 'tbsp', 'tablespoon', 'tablespoons', 'tsp', 'teaspoon', 'teaspoons']:
        # Volume -> ml
        conversion = UNIT_CONVERSIONS.get(unit_lower, 1.0)
        return (amount * conversion, 'ml')

    else:
        # Count-based or descriptive (piece, bunch, clove, etc.)
        return (amount, 'count')


def can_combine_quantities(unit1: str, unit2: str) -> bool:
    """
    Check if two units can be combined.

    Args:
        unit1: First unit
        unit2: Second unit

    Returns:
        True if units are compatible for combining
    """
    # Normalize both to base units and check if they match
    _, base1 = normalize_to_base_unit(1.0, unit1)
    _, base2 = normalize_to_base_unit(1.0, unit2)

    return base1 == base2


def combine_quantities(qty1: str, qty2: str) -> str:
    """
    Combine two quantity strings if compatible.

    Args:
        qty1: First quantity string
        qty2: Second quantity string

    Returns:
        Combined quantity string, or qty1 + " + " + qty2 if incompatible
    """
    amount1, unit1, orig1 = parse_quantity(qty1)
    amount2, unit2, orig2 = parse_quantity(qty2)

    if not can_combine_quantities(unit1, unit2):
        # Can't combine - return concatenation
        return f"{orig1} + {orig2}"

    # Normalize both to base unit and combine
    norm_amount1, base_unit = normalize_to_base_unit(amount1, unit1)
    norm_amount2, _ = normalize_to_base_unit(amount2, unit2)

    total = norm_amount1 + norm_amount2

    # Format output nicely
    if base_unit == 'g':
        if total >= 1000:
            return f"{total/1000:.1f}kg"
        else:
            return f"{int(total)}g"
    elif base_unit == 'ml':
        if total >= 1000:
            return f"{total/1000:.1f}L"
        elif total < 1:
            return f"{total*1000:.1f}tsp"
        else:
            return f"{int(total)}ml"
    else:  # count
        if total == int(total):
            return f"{int(total)} {unit1}"
        else:
            return f"{total:.1f} {unit1}"


def reduce_quantity(quantity: str, fraction: float = 0.5) -> str:
    """
    Reduce a quantity by a fraction (for partial use).

    Args:
        quantity: Quantity string
        fraction: Fraction to reduce by (0.5 = use half, leave half)

    Returns:
        Reduced quantity string
    """
    amount, unit, original = parse_quantity(quantity)

    remaining = amount * (1 - fraction)

    if remaining <= 0:
        return "0"

    # Format output
    if unit in ['g', 'gram', 'grams']:
        return f"{int(remaining)}g"
    elif unit in ['ml', 'milliliter', 'milliliters']:
        return f"{int(remaining)}ml"
    elif remaining == int(remaining):
        return f"{int(remaining)} {unit}"
    else:
        return f"{remaining:.1f} {unit}"
