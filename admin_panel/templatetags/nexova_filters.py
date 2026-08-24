from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def money(value):

    if value is None:
        return "0.00"

    try:
        value = Decimal(str(value))
        return f"{value / Decimal('100'):.2f}"

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return "0.00"