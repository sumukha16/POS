import json
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from django.db.models import Sum, Count


from .models import (
    Bill,
    CancelledItem,
    CancelledOrder,
    Category,
    MenuItem,
    Round,
    RoundItem,
    Section,
    Table,
    BillItem,
    Setting
)


def table_screen(request):

    sections = (
        Section.objects
        .filter(is_active=True)
        .prefetch_related("tables")
        .order_by(
            "display_order",
            "name",
        )
    )

    categories = (
        Category.objects
        .filter(is_active=True)
        .order_by(
            "display_order",
            "name",
        )
    )

    menu_items = (
        MenuItem.objects
        .filter(is_active=True)
        .select_related("category")
        .order_by(
            "category__display_order",
            "category__name",
            "name",
        )
    )

    # Convert stored paise to rupees
    # for displaying in the POS.
    menu_display_items = []

    for item in menu_items:

        menu_display_items.append({
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "price": item.price / 100,
            "category_id": item.category.id,
            "category_name": item.category.name,
            "category_type": item.category.category_type,
        })

    # -------------------------------
    # Tax settings for bill preview
    # -------------------------------

    tax_enabled_setting = (
        Setting.objects
        .filter(key="tax_enabled")
        .first()
    )

    tax_rate_setting = (
        Setting.objects
        .filter(key="tax_rate")
        .first()
    )


    tax_enabled = False
    tax_rate = Decimal("0")


    if tax_enabled_setting:

        tax_enabled = (
            str(
                tax_enabled_setting.value
            ).lower()
            in [
                "true",
                "1",
                "yes",
                "on",
            ]
        )


    if tax_rate_setting:

        try:

            tax_rate = Decimal(
                str(
                    tax_rate_setting.value
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            tax_rate = Decimal("0")

    return render(
    request,
    "pos/table_screen.html",
    {
        "sections": sections,

        "categories": categories,

        "menu_items": menu_display_items,

        "tax_enabled":
            tax_enabled,

        "tax_rate":
            tax_rate,
    },
)

@require_GET
def current_order(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
        is_active=True,
    )

    # Find the latest bill for this table.
    latest_bill = (
        Bill.objects
        .filter(table=table)
        .order_by("-paid_at")
        .first()
    )

    rounds = Round.objects.filter(
        table=table
    )

    # If this table has already been billed,
    # only use rounds created after that bill.
    if latest_bill:

        rounds = rounds.filter(
            created_at__gt=latest_bill.paid_at
        )


    rounds = rounds.order_by(
        "created_at",
        "id",
    )


    # Get RoundItems directly.
    #
    # We intentionally do NOT use:
    #
    #     rounditem_set
    #
    # because your RoundItem model doesn't
    # expose that reverse accessor.

    round_items = (
        RoundItem.objects
        .filter(
            round__in=rounds
        )
        .order_by(
            "round__created_at",
            "id",
        )
    )


    items = {}


    for round_item in round_items:

        item_id = str(
            round_item.menu_item_id
        )


        if item_id not in items:

            items[item_id] = {

                "id":
                    round_item.menu_item_id,

                "name":
                    round_item.item_name,

                "price":
                    round_item.unit_price / 100,

                "type":
                    round_item.category_type,

                "quantity":
                    0,

            }


        items[item_id]["quantity"] += (
            round_item.quantity
        )


    return JsonResponse({

        "success": True,

        "table_id":
            table.id,

        "table_name":
            table.name,

        "items":
            list(items.values()),

    })

def order_screen(request, table_id):
    table = get_object_or_404(
        Table,
        id=table_id,
        is_active=True,
    )

    categories = (
        Category.objects
        .filter(is_active=True)
        .order_by("display_order", "name")
    )

    menu_items = (
        MenuItem.objects
        .filter(is_active=True)
        .select_related("category")
        .order_by(
            "category__display_order",
            "category__name",
            "name",
        )
    )

    # Existing rounds for this table.
    rounds = (
        Round.objects
        .filter(table=table)
        .prefetch_related("rounditem_set")
        .order_by("created_at", "id")
    )

    existing_items = []

    for current_round in rounds:

        for item in current_round.rounditem_set.all():

            existing_items.append(
                {
                    "id": item.menu_item_id,
                    "name": item.item_name,
                    "price": float(item.unit_price),
                    "type": item.category_type,
                    "quantity": item.quantity,
                }
            )

    return render(
        request,
        "pos/order_screen.html",
        {
            "table": table,
            "categories": categories,
            "menu_items": menu_items,
            "existing_items": existing_items,
        },
    )

@require_POST
@transaction.atomic
def send_to_kitchen(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
        is_active=True,
    )

    try:
        data = json.loads(
            request.body
        )
    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON.",
            },
            status=400,
        )


    items = data.get("items", [])


    if not items:

        return JsonResponse(
            {
                "success": False,
                "error": "No items selected.",
            },
            status=400,
        )


    # Create a new round.
    current_round = Round.objects.create(
        table=table
    )


    created_items = []


    for item_data in items:

        try:
            menu_item_id = int(
                item_data["menu_item_id"]
            )

            quantity = int(
                item_data["quantity"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            continue


        if quantity <= 0:
            continue


        menu_item = get_object_or_404(
            MenuItem.objects.select_related(
                "category"
            ),
            id=menu_item_id,
            is_active=True,
        )


        line_total = (
            menu_item.price
            * quantity
        )


        round_item = RoundItem.objects.create(

            round=current_round,

            menu_item=menu_item,

            item_name=menu_item.name,

            category_name=menu_item.category.name,

            category_type=menu_item.category.category_type,

            unit_price=menu_item.price,

            quantity=quantity,

            line_total=line_total,

        )


        created_items.append(
            {
                "id": round_item.id,
                "name": round_item.item_name,
                "quantity": round_item.quantity,
            }
        )


    if not created_items:

        # Don't leave an empty round.
        current_round.delete()

        return JsonResponse(
            {
                "success": False,
                "error": "No valid items were selected.",
            },
            status=400,
        )


    # A table with an active round is occupied.
    table.status = Table.Status.OCCUPIED
    table.save(
        update_fields=["status"]
    )


    return JsonResponse(
        {
            "success": True,
            "round_id": current_round.id,
            "items": created_items,
        }
    )


@require_POST
@transaction.atomic
def cancel_order(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
        is_active=True,
    )

    # Find the latest paid bill.
    latest_bill = (
        Bill.objects
        .filter(table=table)
        .order_by("-paid_at")
        .first()
    )

    # Current rounds for this table.
    rounds = Round.objects.filter(
        table=table
    )

    # Don't cancel rounds that belong
    # to an already completed bill.
    if latest_bill:

        rounds = rounds.filter(
            created_at__gt=latest_bill.paid_at
        )

    round_items = (
        RoundItem.objects
        .filter(
            round__in=rounds
        )
        .order_by("id")
    )

    if not round_items.exists():

        return JsonResponse(
            {
                "success": False,
                "error": "There is no active order to cancel.",
            },
            status=400,
        )

    # Create cancellation record.
    cancelled_order = (
        CancelledOrder.objects.create(
            table=table
        )
    )

    # Copy every current order item
    # into the cancellation history.
    for item in round_items:

        CancelledItem.objects.create(

            cancelled_order=cancelled_order,

            menu_item=item.menu_item,

            item_name=item.item_name,

            unit_price=item.unit_price,

            quantity=item.quantity,

        )

    # Remove the active rounds.
    rounds.delete()

    # Table is now available.
    table.status = Table.Status.VACANT

    table.save(
        update_fields=["status"]
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Order cancelled successfully.",
        }
    )


@require_POST
@transaction.atomic
def generate_bill(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
        is_active=True,
    )

    # --------------------------------
    # Find latest completed bill
    # --------------------------------

    latest_bill = (
        Bill.objects
        .filter(table=table)
        .order_by("-paid_at")
        .first()
    )


    # --------------------------------
    # Get current rounds
    # --------------------------------

    rounds = Round.objects.filter(
        table=table
    )


    # Don't include rounds that
    # already belong to a previous bill.

    if latest_bill:

        rounds = rounds.filter(
            created_at__gt=latest_bill.paid_at
        )


    # --------------------------------
    # Get current order items
    # --------------------------------

    round_items = (
        RoundItem.objects
        .filter(
            round__in=rounds
        )
        .order_by(
            "round__created_at",
            "id",
        )
    )


    if not round_items.exists():

        return JsonResponse(
            {
                "success": False,
                "error":
                    "There is no active order to bill.",
            },
            status=400,
        )


    # --------------------------------
    # Calculate subtotal
    # --------------------------------

    subtotal = 0

    for item in round_items:

        subtotal += item.line_total


    # --------------------------------
    # Read tax settings
    # --------------------------------

    tax_setting = (
        Setting.objects
        .filter(
            key="tax_enabled"
        )
        .first()
    )


    rate_setting = (
        Setting.objects
        .filter(
            key="tax_rate"
        )
        .first()
    )


    # Default values

    tax_enabled = False

    tax_rate = 0


    # --------------------------------
    # Tax enabled
    # --------------------------------

    if tax_setting:

        tax_enabled = (
            str(
                tax_setting.value
            ).lower()
            in [
                "true",
                "1",
                "yes",
                "on",
            ]
        )


    # --------------------------------
    # Tax rate
    # --------------------------------

    if rate_setting:

        try:

            tax_rate = Decimal(
                rate_setting.value
            )

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ):

            tax_rate = Decimal("0")


    # --------------------------------
    # Calculate tax
    # --------------------------------

    tax_amount = 0


    if tax_enabled and tax_rate > 0:

        tax_amount = int(
            Decimal(subtotal)
            * tax_rate
            / Decimal("100")
        )


    # --------------------------------
    # Grand total
    # --------------------------------

    total = (
        subtotal
        + tax_amount
    )


    # --------------------------------
    # Next bill number
    # --------------------------------

    today = timezone.localdate()

    last_bill_today = (
        Bill.objects
        .filter(
            bill_date=today
        )
        .order_by("-bill_number")
        .first()
    )


    if last_bill_today:

        next_bill_number = (
            last_bill_today.bill_number + 1
        )

    else:

        next_bill_number = 1


    # --------------------------------
    # Create Bill
    # --------------------------------

    bill = Bill.objects.create(

        bill_number=
            next_bill_number,

        bill_date=
            today,

        table=
            table,

        subtotal=
            subtotal,

        tax_enabled=
            tax_enabled,

        tax_rate=
            tax_rate,

        tax_amount=
            tax_amount,

        total=
            total,

        status=
            Bill.Status.PAID,

    )


    # --------------------------------
    # Create Bill Items
    # --------------------------------

    for item in round_items:

        BillItem.objects.create(

            bill=
                bill,

            menu_item=
                item.menu_item,

            item_name=
                item.item_name,

            category_name=
                item.category_name,

            category_type=
                item.category_type,

            unit_price=
                item.unit_price,

            quantity=
                item.quantity,

            line_total=
                item.line_total,

        )


    # --------------------------------
    # Remove active rounds
    # --------------------------------

    rounds.delete()


    # --------------------------------
    # Make table vacant
    # --------------------------------

    table.status = (
        Table.Status.VACANT
    )

    table.save(
        update_fields=["status"]
    )


    # --------------------------------
    # Response
    # --------------------------------

    return JsonResponse(
        {
            "success": True,

            "bill_id":
                bill.id,

            "bill_number":
                bill.bill_number,

            "subtotal":
                subtotal / 100,

            "tax_enabled":
                tax_enabled,

            "tax_rate":
                float(tax_rate),

            "tax_amount":
                tax_amount / 100,

            "total":
                total / 100,
        }
    )

def bill_history(request):

    bills = (
        Bill.objects
        .select_related("table")
        .order_by("-bill_number")
    )

    return render(
        request,
        "pos/bill_history.html",
        {
            "bills": bills,
        },
    )

def bill_detail(request, bill_id):

    bill = get_object_or_404(
        Bill.objects.select_related("table"),
        id=bill_id,
    )

    items = (
        BillItem.objects
        .filter(bill=bill)
        .order_by("id")
    )

    food_items = []
    drink_items = []

    food_subtotal = 0
    drink_subtotal = 0

    for item in items:

        if item.category_type == "FOOD":

            food_items.append(item)

            food_subtotal += item.line_total

        else:

            drink_items.append(item)

            drink_subtotal += item.line_total

    return render(
        request,
        "pos/bill_detail.html",
        {
            "bill": bill,

            "hotel_name":
                "HOTEL VARAAD INTERNATIONAL",

            "food_items":
                food_items,

            "drink_items":
                drink_items,

            "food_subtotal":
                food_subtotal,

            "drink_subtotal":
                drink_subtotal,
        },
    )



def dashboard(request):

    today = timezone.localdate()

    # -----------------------------
    # Today's bills
    # -----------------------------

    todays_bills = (
        Bill.objects
        .filter(
            bill_date=today
        )
        .order_by("-bill_number")
    )


    # -----------------------------
    # Paid / Cancelled
    # -----------------------------

    paid_bills = todays_bills.filter(
        status=Bill.Status.PAID
    )

    cancelled_bills = todays_bills.filter(
        status=Bill.Status.CANCELLED
    )


    # -----------------------------
    # Today's sales
    # -----------------------------

    sales_data = (
        paid_bills.aggregate(
            total=Sum("total")
        )
    )

    today_sales = (
        sales_data["total"]
        or 0
    )


    # -----------------------------
    # Tax collected
    # -----------------------------

    tax_data = (
        paid_bills.aggregate(
            total=Sum("tax_amount")
        )
    )

    today_tax = (
        tax_data["total"]
        or 0
    )


    # -----------------------------
    # Food / Drinks sales
    # -----------------------------

    paid_items = (
        BillItem.objects
        .filter(
            bill__in=paid_bills
        )
    )


    food_data = (
        paid_items
        .filter(
            category_type="FOOD"
        )
        .aggregate(
            total=Sum("line_total")
        )
    )

    food_sales = (
        food_data["total"]
        or 0
    )


    drink_data = (
        paid_items
        .filter(
            category_type="DRINK"
        )
        .aggregate(
            total=Sum("line_total")
        )
    )

    drink_sales = (
        drink_data["total"]
        or 0
    )


    return render(
        request,
        "pos/dashboard.html",
        {
            "today": today,

            "today_sales":
                today_sales,

            "today_tax":
                today_tax,

            "food_sales":
                food_sales,

            "drink_sales":
                drink_sales,

            "total_bills":
                todays_bills.count(),

            "paid_bills":
                paid_bills.count(),

            "cancelled_bills":
                cancelled_bills.count(),

            "recent_bills":
                todays_bills[:10],
        },
    )