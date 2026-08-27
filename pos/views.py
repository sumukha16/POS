import json
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from django.db.models import Sum

from django.db.models import Q

from datetime import timedelta
from django.utils import timezone
from datetime import datetime

from django.contrib import messages
from .forms import CategoryForm, MenuItemForm

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .models import Category, MenuItem
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
    Setting,
    Category,
    MenuItem,
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
def menu_items_api(request):

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

    items = []

    for item in menu_items:

        items.append({
            "id": item.id,
            "code": item.code or "",
            "name": item.name,
            "price": float(
                Decimal(item.price)
                / Decimal("100")
            ),
            "category_id": item.category.id,
            "category_name": item.category.name,
            "category_type": item.category.category_type,
        })

    return JsonResponse(
        {
            "success": True,
            "items": items,
        }
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
        .prefetch_related("items")
        .order_by("created_at", "id")
    )

    existing_items = []

    for current_round in rounds:

        for item in current_round.items.all():

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
    # Items added directly from
    # Bill Preview.
    #
    # These are NOT sent to kitchen.
    # --------------------------------

    try:

        data = json.loads(
            request.body
        )

    except json.JSONDecodeError:

        data = {}


    bill_only_items_data = (
        data.get(
            "bill_only_items",
            []
        )
    )
    include_tax = bool(
    data.get(
        "include_tax",
        False
    )
)


    bill_only_items = []


    for item_data in bill_only_items_data:

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


        bill_only_items.append({

            "menu_item":
                menu_item,

            "item_name":
                menu_item.name,

            "category_name":
                menu_item.category.name,

            "category_type":
                menu_item.category.category_type,

            "unit_price":
                menu_item.price,

            "quantity":
                quantity,

            "line_total":
                line_total,

        })

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


    for item in bill_only_items:

        subtotal += item["line_total"]


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


    tax_amount = 0


    if include_tax and tax_rate > 0:

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

    date_prefix = int(
        today.strftime("%d%m%y")
    )


    last_bill_today = (
        Bill.objects
        .filter(
            bill_date=today
        )
        .order_by("-bill_number")
        .first()
    )


    if (
        last_bill_today
        and last_bill_today.bill_number >=
            date_prefix * 10000
    ):

        sequence_number = (
            last_bill_today.bill_number
            % 10000
        ) + 1

    else:

        sequence_number = 1


    if sequence_number > 9999:

        return JsonResponse(
            {
                "error":
                    "Daily bill number limit reached."
            },
            status=400,
        )


    next_bill_number = (
        date_prefix * 10000
        + sequence_number
    )


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
            include_tax,

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
    # Bill Preview items
    #
    # These go directly to the bill.
    # They do NOT go to kitchen.
    # --------------------------------

    for item in bill_only_items:

        BillItem.objects.create(

            bill=
                bill,

            menu_item=
                item["menu_item"],

            item_name=
                item["item_name"],

            category_name=
                item["category_name"],

            category_type=
                item["category_type"],

            unit_price=
                item["unit_price"],

            quantity=
                item["quantity"],

            line_total=
                item["line_total"],

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

    search_query = (
        request.GET.get(
            "search",
            ""
        )
        .strip()
    )


    bills = (
        Bill.objects
        .select_related("table")
        .order_by(
            "-bill_date",
            "-bill_number",
        )
    )


    if search_query:

        filters = Q(
            table__name__icontains=
                search_query
        )


        # -------------------------
        # Bill number search
        # -------------------------

        if search_query.isdigit():

            filters |= Q(
                bill_number=
                    int(search_query)
            )


        # -------------------------
        # Date search
        # -------------------------

        date_formats = [
            "%d %b %Y",
            "%d %B %Y",
            "%d %b",
            "%d %B",
            "%Y-%m-%d",
        ]


        parsed_date = None


        for date_format in date_formats:

            try:

                if "%Y" not in date_format:

                    parsed_date = datetime.strptime(
                        search_query,
                        date_format
                    ).replace(
                        year=timezone.localdate().year
                    ).date()

                else:

                    parsed_date = datetime.strptime(
                        search_query,
                        date_format
                    ).date()


                break

            except ValueError:

                continue


        if parsed_date:

            filters |= Q(
                bill_date=
                    parsed_date
            )


        bills = bills.filter(
            filters
        )


    # --------------------------------
    # Group bills by date
    # --------------------------------

    grouped_bills = []


    current_date = None
    current_group = None


    for bill in bills:

        if bill.bill_date != current_date:

            current_date = bill.bill_date


            current_group = {

                "date":
                    bill.bill_date,

                "bills":
                    [],

            }


            grouped_bills.append(
                current_group
            )


        current_group["bills"].append({

            "bill": bill,

            "display_total":
                Decimal(bill.total)
                / Decimal("100"),

            "display_subtotal":
                Decimal(bill.subtotal)
                / Decimal("100"),

            "display_tax":
                Decimal(bill.tax_amount)
                / Decimal("100"),

        })


    return render(
        request,
        "pos/bill_history.html",
        {
            "bill_groups":
                grouped_bills,

            "search_query":
                search_query,
        },
    )

def bill_detail(request, bill_id):

    bill = get_object_or_404(
        Bill.objects.select_related("table"),
        id=bill_id,
    )

    bill_items = (
        BillItem.objects
        .filter(bill=bill)
        .order_by("id")
    )

    food_items = []
    drink_items = []

    food_subtotal = Decimal("0")
    drink_subtotal = Decimal("0")

    for item in bill_items:

        display_item = {
            "item": item,

            "unit_price":
                Decimal(item.unit_price) / Decimal("100"),

            "line_total":
                Decimal(item.line_total) / Decimal("100"),
        }

        if item.category_type == "FOOD":

            food_items.append(display_item)

            food_subtotal += (
                Decimal(item.line_total)
                / Decimal("100")
            )

        else:

            drink_items.append(display_item)

            drink_subtotal += (
                Decimal(item.line_total)
                / Decimal("100")
            )

    subtotal = (
        Decimal(bill.subtotal)
        / Decimal("100")
    )

    tax_amount = (
        Decimal(bill.tax_amount)
        / Decimal("100")
    )

    total = (
        Decimal(bill.total)
        / Decimal("100")
    )

    return render(
        request,
        "pos/bill_detail.html",
        {
            "bill": bill,

            "food_items":
                food_items,

            "drink_items":
                drink_items,

            "food_subtotal":
                food_subtotal,

            "drink_subtotal":
                drink_subtotal,

            "subtotal":
                subtotal,

            "tax_amount":
                tax_amount,

            "total":
                total,
        },
    )

def management_dashboard(request):

    categories = (
        Category.objects
        .order_by(
            "category_type",
            "display_order",
            "name",
        )
    )


    menu_queryset = (
        MenuItem.objects
        .select_related("category")
        .order_by(
            "category__category_type",
            "category__display_order",
            "name",
        )
    )


    management_menu_items = []


    for item in menu_queryset:

        management_menu_items.append({

            "id":
                item.id,

            "name":
                item.name,

            "code":
                item.code or "",

            "price":
                Decimal(item.price)
                / Decimal("100"),

            "is_active":
                item.is_active,

            "category":
                item.category,

        })


    category_form = CategoryForm()

    menu_item_form = MenuItemForm()


    tax_rate_setting = (
        Setting.objects
        .filter(
            key="tax_rate"
        )
        .first()
    )


    tax_rate = Decimal("0")


    if tax_rate_setting:

        try:

            tax_rate = Decimal(
                tax_rate_setting.value
            )

        except (
            TypeError,
            ValueError,
            ArithmeticError,
        ):

            tax_rate = Decimal("0")

        sections = (
            Section.objects
            .order_by(
                "display_order",
                "id",
            )
        )


        management_tables = (
            Table.objects
            .select_related("section")
            .order_by(
                "section__display_order",
                "section__id",
                "display_order",
                "id",
            )
        )

        return render(
        request,
        "pos/management_dashboard.html",
        {
            "management_categories":
                categories,

            "management_menu_items":
                management_menu_items,

            "management_sections":
                sections,

            "management_tables":
                management_tables,

            "category_form":
                category_form,

            "menu_item_form":
                menu_item_form,

            "tax_rate":
                tax_rate,
        },
    )

@require_POST
def management_create_category(request):

    form = CategoryForm(
        request.POST
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Category created successfully.",
        )

    else:

        messages.error(
            request,
            "Could not create category.",
        )

    return redirect(
        "pos:management_dashboard"
    )


@require_POST
def management_toggle_category(
    request,
    category_id,
):

    category = get_object_or_404(
        Category,
        id=category_id,
    )

    category.is_active = (
        not category.is_active
    )

    category.save(
        update_fields=["is_active"]
    )

    return redirect(
        "pos:management_dashboard"
    )


@require_POST
def management_edit_category(
    request,
    category_id,
):

    category = get_object_or_404(
        Category,
        id=category_id,
    )


    data = request.POST.copy()


    # Keep the existing active/inactive status.
    data["is_active"] = (
        "on"
        if category.is_active
        else ""
    )


    form = CategoryForm(
        data,
        instance=category,
    )


    if not form.is_valid():

        return JsonResponse(
            {
                "success": False,

                "error":
                    "Could not update category.",

                "errors":
                    form.errors.get_json_data(),
            },
            status=400,
        )


    updated_category = form.save()


    return JsonResponse(
        {
            "success": True,

            "category": {

                "id":
                    updated_category.id,

                "name":
                    updated_category.name,

                "category_type":
                    updated_category.category_type,

                "display_order":
                    updated_category.display_order,

                "is_active":
                    updated_category.is_active,
            },
        }
    )

@require_POST
def management_create_menu_item(request):

    data = request.POST.copy()

    try:

        price_rupees = Decimal(
            str(
                data.get(
                    "price",
                    "0"
                )
            )
        )

        if price_rupees < 0:
            raise ValueError

        data["price"] = str(
            int(
                price_rupees
                * Decimal("100")
            )
        )

    except (
        TypeError,
        ValueError,
        ArithmeticError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid price.",
            },
            status=400,
        )


    # New menu items are active by default.

    data["is_active"] = "on"


    form = MenuItemForm(
        data
    )


    if not form.is_valid():

        return JsonResponse(
            {
                "success": False,

                "error":
                    "Could not create menu item.",

                "errors":
                    form.errors.get_json_data(),
            },
            status=400,
        )


    item = form.save()


    return JsonResponse(
        {
            "success": True,

            "item": {

                "id":
                    item.id,

                "name":
                    item.name,

                "code":
                    item.code or "",

                "price":
                    float(
                        Decimal(
                            item.price
                        )
                        / Decimal("100")
                    ),

                "category_id":
                    item.category_id,

                "category_name":
                    item.category.name,

                "is_active":
                    item.is_active,
            },
        }
    )

@require_POST
def management_toggle_menu_item(
    request,
    item_id,
):

    item = get_object_or_404(
        MenuItem,
        id=item_id,
    )

    item.is_active = not item.is_active

    item.save(
        update_fields=["is_active"]
    )

    return JsonResponse({
        "success": True,
        "is_active": item.is_active,
    })

@require_POST
def management_edit_menu_item(
    request,
    item_id,
):

    item = get_object_or_404(
        MenuItem,
        id=item_id,
    )


    data = request.POST.copy()


    try:

        price_rupees = Decimal(
            str(
                data.get(
                    "price",
                    "0"
                )
            )
        )

        if price_rupees < 0:
            raise ValueError

        data["price"] = str(
            int(
                price_rupees
                * Decimal("100")
            )
        )

    except (
        TypeError,
        ValueError,
        ArithmeticError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid price.",
            },
            status=400,
        )


   # Keep the existing active/inactive status
    # when editing the menu item.
    data["is_active"] = (
        "on"
        if item.is_active
        else ""
    )


    form = MenuItemForm(
        data,
        instance=item,
    )


    if not form.is_valid():

        return JsonResponse(
            {
                "success": False,

                "error":
                    "Could not update menu item.",

                "errors":
                    form.errors.get_json_data(),
            },
            status=400,
        )


    updated_item = form.save()


    return JsonResponse(
        {
            "success": True,

            "item": {
                "id":
                    updated_item.id,

                "name":
                    updated_item.name,

                "code":
                    updated_item.code or "",

                "price":
                    float(
                        Decimal(
                            updated_item.price
                        )
                        / Decimal("100")
                    ),

                "category_id":
                    updated_item.category_id,

                "category_name":
                    updated_item.category.name,

                "is_active":
                    updated_item.is_active,
            },
        }
    )

@require_POST
def management_save_tax(request):

    setting, created = Setting.objects.get_or_create(
        key="tax_rate",
        defaults={
            "value": "5",
        },
    )

    try:

        tax_rate = Decimal(
            str(
                request.POST.get(
                    "tax_rate",
                    "0"
                )
            )
        )

        if tax_rate < 0 or tax_rate > 100:
            raise ValueError

    except (
        TypeError,
        ValueError,
        ArithmeticError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Enter a valid tax rate between 0 and 100.",
            },
            status=400,
        )


    setting.value = str(tax_rate)
    setting.save()


    return JsonResponse(
        {
            "success": True,
            "tax_rate": float(tax_rate),
        }
    )

@require_POST
def management_create_section(request):

    name = request.POST.get(
        "name",
        ""
    ).strip()

    display_order = request.POST.get(
        "display_order",
        "0"
    )


    if not name:

        return JsonResponse(
            {
                "success": False,
                "error": "Section name is required.",
            },
            status=400,
        )


    try:

        display_order = int(
            display_order
        )

        if display_order < 0:
            raise ValueError

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid display order.",
            },
            status=400,
        )


    section = Section.objects.create(
        name=name,
        display_order=display_order,
        is_active=True,
    )


    return JsonResponse(
        {
            "success": True,

            "section": {
                "id":
                    section.id,

                "name":
                    section.name,

                "display_order":
                    section.display_order,

                "is_active":
                    section.is_active,
            },
        }
    )

@require_POST
def management_edit_section(
    request,
    section_id,
):

    section = get_object_or_404(
        Section,
        id=section_id,
    )


    name = request.POST.get(
        "name",
        ""
    ).strip()

    display_order = request.POST.get(
        "display_order",
        "0"
    )


    if not name:

        return JsonResponse(
            {
                "success": False,
                "error": "Section name is required.",
            },
            status=400,
        )


    try:

        display_order = int(
            display_order
        )

        if display_order < 0:
            raise ValueError

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid display order.",
            },
            status=400,
        )


    section.name = name
    section.display_order = display_order

    section.save(
        update_fields=[
            "name",
            "display_order",
        ]
    )


    return JsonResponse(
        {
            "success": True,

            "section": {
                "id":
                    section.id,

                "name":
                    section.name,

                "display_order":
                    section.display_order,

                "is_active":
                    section.is_active,
            },
        }
    )


@require_POST
def management_toggle_section(
    request,
    section_id,
):

    section = get_object_or_404(
        Section,
        id=section_id,
    )


    section.is_active = (
        not section.is_active
    )


    section.save(
        update_fields=[
            "is_active",
        ]
    )


    return JsonResponse(
        {
            "success": True,

            "is_active":
                section.is_active,
        }
    )


@require_POST
def management_create_table(request):

    name = request.POST.get(
        "name",
        ""
    ).strip()

    section_id = request.POST.get(
        "section"
    )

    display_order = request.POST.get(
        "display_order",
        "0"
    )


    if not name:

        return JsonResponse(
            {
                "success": False,
                "error": "Table name is required.",
            },
            status=400,
        )


    section = get_object_or_404(
        Section,
        id=section_id,
    )


    try:

        display_order = int(
            display_order
        )

        if display_order < 0:
            raise ValueError

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid display order.",
            },
            status=400,
        )


    table = Table.objects.create(
        section=section,
        name=name,
        display_order=display_order,
        status=Table.Status.VACANT,
        is_active=True,
    )


    return JsonResponse(
        {
            "success": True,

            "table": {
                "id":
                    table.id,

                "name":
                    table.name,

                "section_id":
                    table.section_id,

                "section_name":
                    table.section.name,

                "display_order":
                    table.display_order,

                "status":
                    table.status,

                "is_active":
                    table.is_active,
            },
        }
    )

@require_POST
def management_edit_table(
    request,
    table_id,
):

    table = get_object_or_404(
        Table,
        id=table_id,
    )


    name = request.POST.get(
        "name",
        ""
    ).strip()

    section_id = request.POST.get(
        "section"
    )

    display_order = request.POST.get(
        "display_order",
        "0"
    )


    if not name:

        return JsonResponse(
            {
                "success": False,
                "error": "Table name is required.",
            },
            status=400,
        )


    section = get_object_or_404(
        Section,
        id=section_id,
    )


    try:

        display_order = int(
            display_order
        )

        if display_order < 0:
            raise ValueError

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid display order.",
            },
            status=400,
        )


    table.name = name
    table.section = section
    table.display_order = display_order


    table.save(
        update_fields=[
            "name",
            "section",
            "display_order",
        ]
    )


    return JsonResponse(
        {
            "success": True,

            "table": {
                "id":
                    table.id,

                "name":
                    table.name,

                "section_id":
                    table.section_id,

                "section_name":
                    table.section.name,

                "display_order":
                    table.display_order,

                "status":
                    table.status,

                "is_active":
                    table.is_active,
            },
        }
    )

@require_POST
def management_toggle_table(
    request,
    table_id,
):

    table = get_object_or_404(
        Table,
        id=table_id,
    )


    table.is_active = (
        not table.is_active
    )


    table.save(
        update_fields=[
            "is_active",
        ]
    )


    return JsonResponse(
        {
            "success": True,

            "is_active":
                table.is_active,
        }
    )


def management_analytics(request):

    today = timezone.localdate()

    period = request.GET.get(
        "period",
        "week",
    )


    if period == "month":

        start_date = today.replace(
            day=1
        )

    elif period == "year":

        start_date = today.replace(
            month=1,
            day=1,
        )

    else:

        period = "week"

        start_date = (
            today
            - timedelta(
                days=today.weekday()
            )
        )


    bills = Bill.objects.filter(
        status=Bill.Status.PAID,
        bill_date__gte=start_date,
        bill_date__lte=today,
    )


    # ---------------------------------
    # TOTAL REVENUE
    # ---------------------------------

    revenue_paise = bills.aggregate(
            total=Sum("total")
        )["total"] or 0


    # ---------------------------------
    # DRINKS REVENUE
    # ---------------------------------

    drinks_revenue_paise = (
        BillItem.objects
        .filter(
            bill__in=bills,
            category_type="DRINK",
        )
        .aggregate(
            total=Sum("line_total")
        )["total"] or 0
    )


    # ---------------------------------
    # DRINK ITEM-WISE SALES
    # ---------------------------------

    drink_items = (
        BillItem.objects
        .filter(
            bill__in=bills,
            category_type="DRINK",
        )
        .values(
            "menu_item_id",
            "item_name",
        )
        .annotate(
            quantity_sold=Sum(
                "quantity"
            ),
            revenue=Sum(
                "line_total"
            ),
        )
        .order_by(
            "-quantity_sold",
            "item_name",
        )
    )


    management_drink_items = []

    for item in drink_items:

        management_drink_items.append({

            "name":
                item["item_name"],

            "quantity":
                item["quantity_sold"] or 0,

            "revenue":
                (item["revenue"] or 0)
                / 100,

        })


    return JsonResponse(
        {
            "success": True,

            "period":
                period,

            "revenue":
                float(
                    revenue_paise
                    / 100
                ),

            "drinks_revenue":
                float(
                    drinks_revenue_paise
                    / 100
                ),

            "drink_items":
                management_drink_items,
        }
    )
