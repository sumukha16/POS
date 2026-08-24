from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Max

from .models import (
    Bill,
    BillItem,
    RoundItem,
    Setting,
    Table,
    CancelledItem,
    CancelledOrder,
    Round,
)


def get_setting(key, default=None):
    """
    Get a setting value from the database.
    """

    setting = Setting.objects.filter(key=key).first()

    if setting is None:
        return default

    return setting.value


def get_bool_setting(key, default=False):
    """
    Convert a stored setting value into True/False.
    """

    value = get_setting(key)

    if value is None:
        return default

    return value.lower() in {
        "true",
        "1",
        "yes",
        "on",
    }


def get_decimal_setting(key, default=Decimal("0")):
    """
    Convert a stored setting into Decimal.
    """

    value = get_setting(key)

    if value is None:
        return default

    return Decimal(value)


def get_next_bill_number():
    """
    Get the next sequential bill number.

    Example:

    No bills yet -> 1
    Last bill 1  -> 2
    Last bill 2  -> 3
    """

    last_bill_number = (
        Bill.objects.aggregate(
            max_number=Max("bill_number")
        )["max_number"]
    )

    if last_bill_number is None:
        return 1

    return last_bill_number + 1


@transaction.atomic
def create_bill_for_table(table_id):
    """
    Generate a bill for the table.

    This operation:

    1. Gets all active rounds.
    2. Gets all round items.
    3. Merges identical menu items.
    4. Calculates subtotal.
    5. Reads tax settings.
    6. Calculates tax.
    7. Creates the Bill.
    8. Creates BillItems.
    9. Deletes active rounds.
    10. Makes the table VACANT.

    Everything happens inside one database transaction.
    """

    # Lock the table during this operation.
    table = (
        Table.objects
        .select_for_update()
        .get(id=table_id)
    )

    # Make sure the table actually has an active order.
    if table.status != Table.Status.OCCUPIED:
        raise ValueError(
            "Cannot create a bill for a vacant table."
        )

    # Get all active round items for this table.
    round_items = (
        RoundItem.objects
        .filter(round__table=table)
        .select_related(
            "menu_item",
            "round",
        )
        .order_by("round__created_at", "id")
    )

    if not round_items.exists():
        raise ValueError(
            "Cannot create a bill because the table has no items."
        )

    # ---------------------------------------------------------
    # MERGE ITEMS
    # ---------------------------------------------------------

    merged_items = {}

    for item in round_items:

        menu_item_id = item.menu_item_id

        if menu_item_id not in merged_items:

            merged_items[menu_item_id] = {
                "menu_item": item.menu_item,
                "item_name": item.item_name,
                "category_name": item.category_name,
                "category_type": item.category_type,
                "unit_price": item.unit_price,
                "quantity": 0,
            }

        merged_items[menu_item_id]["quantity"] += item.quantity

    # ---------------------------------------------------------
    # CALCULATE SUBTOTAL
    # ---------------------------------------------------------

    subtotal = 0

    for item in merged_items.values():

        item["line_total"] = (
            item["unit_price"] *
            item["quantity"]
        )

        subtotal += item["line_total"]

    # ---------------------------------------------------------
    # TAX
    # ---------------------------------------------------------

    tax_enabled = get_bool_setting(
        "tax_enabled",
        default=False,
    )

    tax_rate = get_decimal_setting(
        "tax_rate",
        default=Decimal("0"),
    )

    tax_amount = 0

    if tax_enabled and tax_rate > 0:

        tax_value = (
            Decimal(subtotal) *
            tax_rate /
            Decimal("100")
        )

        tax_value = tax_value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )

        tax_amount = int(tax_value)

    total = subtotal + tax_amount

    # ---------------------------------------------------------
    # BILL NUMBER
    # ---------------------------------------------------------

    bill_number = get_next_bill_number()

    # ---------------------------------------------------------
    # CREATE BILL
    # ---------------------------------------------------------

    bill = Bill.objects.create(
        bill_number=bill_number,
        table=table,
        subtotal=subtotal,
        tax_enabled=tax_enabled,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
    )

    # ---------------------------------------------------------
    # CREATE BILL ITEMS
    # ---------------------------------------------------------

    bill_items = []

    for item in merged_items.values():

        bill_items.append(
            BillItem(
                bill=bill,
                menu_item=item["menu_item"],
                item_name=item["item_name"],
                category_name=item["category_name"],
                category_type=item["category_type"],
                unit_price=item["unit_price"],
                quantity=item["quantity"],
                line_total=item["line_total"],
            )
        )

    BillItem.objects.bulk_create(bill_items)

    # ---------------------------------------------------------
    # CLEAR ACTIVE ROUNDS
    # ---------------------------------------------------------

    round_ids = (
        round_items
        .values_list("round_id", flat=True)
        .distinct()
    )

    # Deleting the rounds automatically deletes
    # their RoundItems because RoundItem uses
    # on_delete=models.CASCADE.
    from .models import Round

    Round.objects.filter(
        id__in=round_ids
    ).delete()

    # ---------------------------------------------------------
    # VACATE TABLE
    # ---------------------------------------------------------

    table.status = Table.Status.VACANT
    table.save(update_fields=["status"])

    return bill


@transaction.atomic
def cancel_order_for_table(table_id):
    """
    Cancel the active order for a table.

    Steps:
    1. Lock the table.
    2. Verify that the table is occupied.
    3. Get all active round items.
    4. Create a CancelledOrder record.
    5. Copy all active items into CancelledItem records.
    6. Delete the active rounds.
    7. Make the table vacant.

    Everything happens inside one transaction.
    """

    # Lock the table while cancellation is happening.
    table = (
        Table.objects
        .select_for_update()
        .get(id=table_id)
    )

    # The table must have an active order.
    if table.status != Table.Status.OCCUPIED:
        raise ValueError(
            "Cannot cancel an order for a vacant table."
        )

    # Get all active round items.
    round_items = (
        RoundItem.objects
        .filter(round__table=table)
        .select_related("menu_item")
    )

    if not round_items.exists():
        raise ValueError(
            "Cannot cancel because the table has no items."
        )

    # Create cancellation history.
    cancelled_order = CancelledOrder.objects.create(
        table=table
    )

    # Copy the active items into cancellation history.
    cancelled_items = []

    for item in round_items:
        cancelled_items.append(
            CancelledItem(
                cancelled_order=cancelled_order,
                menu_item=item.menu_item,
                item_name=item.item_name,
                unit_price=item.unit_price,
                quantity=item.quantity,
            )
        )

    CancelledItem.objects.bulk_create(cancelled_items)

    # Get the rounds belonging to this table.
    round_ids = (
        round_items
        .values_list("round_id", flat=True)
        .distinct()
    )

    # RoundItem uses CASCADE, so deleting the rounds
    # also deletes their RoundItems.
    Round.objects.filter(
        id__in=round_ids
    ).delete()

    # Finally make the table available.
    table.status = Table.Status.VACANT
    table.save(update_fields=["status"])

    return cancelled_order


# ---------------------------------------------------------------
# RECEIPT--------------------------------------------------------
# ---------------------------------------------------------------


def format_receipt_money(paise):
    """
    Convert paise to rupees for receipt output.
    """

    value = Decimal(str(paise or 0))

    return f"{value / Decimal('100'):.2f}"


def build_receipt(bill):
    """
    Build the printable text for a historical bill.

    This function only reads the bill.
    It does NOT create or modify a bill.
    """

    items = list(
        bill.items.all().order_by(
            "category_type",
            "category_name",
            "item_name",
        )
    )

    food_items = [
        item
        for item in items
        if item.category_type == "FOOD"
    ]

    drink_items = [
        item
        for item in items
        if item.category_type == "DRINK"
    ]

    food_subtotal = sum(
        item.line_total
        for item in food_items
    )

    drink_subtotal = sum(
        item.line_total
        for item in drink_items
    )

    lines = []

    # Header
    lines.append("NEXOVA")
    lines.append("DUPLICATE BILL")
    lines.append("")

    lines.append(
        f"Bill No: {bill.bill_number}"
    )

    lines.append(
        f"Table: {bill.table.name}"
    )

    if bill.paid_at:

        lines.append(
            "Date/Time: "
            + bill.paid_at.strftime(
                "%d/%m/%Y %I:%M %p"
            )
        )

    lines.append("")
    lines.append("-" * 32)

    # Food
    if food_items:

        lines.append("FOOD")
        lines.append("-" * 32)

        for item in food_items:

            lines.append(
                item.item_name
            )

            lines.append(
                f"  Rate: "
                f"{format_receipt_money(item.unit_price)}  "
                f"Qty: {item.quantity}  "
                f"Amt: "
                f"{format_receipt_money(item.line_total)}"
            )

        lines.append("-" * 32)

        lines.append(
            f"Food Subtotal: "
            f"{format_receipt_money(food_subtotal)}"
        )

        lines.append("")

    # Drinks
    if drink_items:

        lines.append("DRINKS")
        lines.append("-" * 32)

        for item in drink_items:

            lines.append(
                item.item_name
            )

            lines.append(
                f"  Rate: "
                f"{format_receipt_money(item.unit_price)}  "
                f"Qty: {item.quantity}  "
                f"Amt: "
                f"{format_receipt_money(item.line_total)}"
            )

        lines.append("-" * 32)

        lines.append(
            f"Drinks Subtotal: "
            f"{format_receipt_money(drink_subtotal)}"
        )

        lines.append("")

    # Overall totals
    lines.append("-" * 32)

    lines.append(
        f"Subtotal: "
        f"{format_receipt_money(bill.subtotal)}"
    )

    if bill.tax_enabled:

        lines.append(
            f"Tax ({bill.tax_rate}%): "
            f"{format_receipt_money(bill.tax_amount)}"
        )

    lines.append("-" * 32)

    lines.append(
        f"Grand Total: "
        f"{format_receipt_money(bill.total)}"
    )

    lines.append("")
    lines.append("Thank You")
    lines.append("Visit Again")
    lines.append("")

    return "\n".join(lines)