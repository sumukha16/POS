from django.core.files.storage import filesystem
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from pos.models import (
    Bill,
    Category,
    MenuItem,
    Section,
    Table,
    Setting,
)

from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render

from pos.middleware import SERVER_INSTANCE_ID


def admin_login(request):

    if request.user.is_authenticated:
        return redirect("pos:table_screen")

    error = None

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None and user.is_active:

            login(
                request,
                user
            )

            # Mark this session as belonging
            # to the current POS server instance.
            request.session[
                "pos_server_instance_id"
            ] = SERVER_INSTANCE_ID

            request.session.save()

            return redirect(
                "pos:table_screen"
            )

        error = "Invalid username or password."

    return render(
        request,
        "admin_panel/login.html",
        {
            "error": error,
        },
    )


@login_required
def dashboard(request):

    today = timezone.localdate()

    active_sections = Section.objects.filter(
        is_active=True
    ).count()

    active_tables = Table.objects.filter(
        is_active=True
    ).count()

    occupied_tables = Table.objects.filter(
        is_active=True,
        status=Table.Status.OCCUPIED,
    ).count()

    vacant_tables = Table.objects.filter(
        is_active=True,
        status=Table.Status.VACANT,
    ).count()

    active_categories = Category.objects.filter(
        is_active=True
    ).count()

    active_menu_items = MenuItem.objects.filter(
        is_active=True
    ).count()

    today_bills = Bill.objects.filter(
        bill_date=today,
        status=Bill.Status.PAID,
    )

    today_bill_count = today_bills.count()

    today_revenue = sum(
        bill.total
        for bill in today_bills
    )
    context = {
        "active_sections": active_sections,
        "active_tables": active_tables,
        "occupied_tables": occupied_tables,
        "vacant_tables": vacant_tables,
        "active_categories": active_categories,
        "active_menu_items": active_menu_items,
        "today_bill_count": today_bill_count,
        "today_revenue": today_revenue,
    }

    return render(
        request,
        "admin_panel/dashboard.html",
        context,
    )
@login_required
def categories(request):

    category_list = Category.objects.all()

    return render(
        request,
        "admin_panel/categories.html",
        {
            "categories": category_list,
        },
    )


@login_required
def category_add(request):

    error = None

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        category_type = request.POST.get(
            "category_type",
            "",
        )

        if not name:
            error = "Category name is required."

        elif category_type not in {
            Category.CategoryType.FOOD,
            Category.CategoryType.DRINK,
        }:
            error = "Invalid category type."

        elif Category.objects.filter(
            name__iexact=name
        ).exists():
            error = "A category with this name already exists."

        else:

            Category.objects.create(
                name=name,
                category_type=category_type,
            )

            return redirect(
                "admin_panel:categories"
            )

    return render(
        request,
        "admin_panel/category_form.html",
        {
            "error": error,
            "category": None,
        },
    )


@login_required
def category_edit(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id,
    )

    error = None

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        category_type = request.POST.get(
            "category_type",
            "",
        )

        if not name:
            error = "Category name is required."

        elif category_type not in {
            Category.CategoryType.FOOD,
            Category.CategoryType.DRINK,
        }:
            error = "Invalid category type."

        elif Category.objects.filter(
            name__iexact=name
        ).exclude(
            id=category.id
        ).exists():
            error = "A category with this name already exists."

        else:

            category.name = name
            category.category_type = category_type
            category.save(
                update_fields=[
                    "name",
                    "category_type",
                ]
            )

            return redirect(
                "admin_panel:categories"
            )

    return render(
        request,
        "admin_panel/category_form.html",
        {
            "error": error,
            "category": category,
        },
    )


@login_required
def category_toggle(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id,
    )

    category.is_active = not category.is_active

    category.save(
        update_fields=["is_active"]
    )

    return redirect(
        "admin_panel:categories"
    )



@login_required
def menu_items(request):

    items = MenuItem.objects.select_related(
        "category"
    ).order_by(
        "category__display_order",
        "name",
    )

    return render(
        request,
        "admin_panel/menu_items.html",
        {
            "items": items,
        },
    )


@login_required
def menu_item_add(request):

    categories = Category.objects.filter(
        is_active=True
    ).order_by(
        "display_order",
        "name",
    )

    error = None

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        code = request.POST.get(
            "code",
            "",
        ).strip().upper()

        price_text = request.POST.get(
            "price",
            "",
        ).strip()

        category_id = request.POST.get(
            "category",
            "",
        )

        # -----------------------------
        # Validate name
        # -----------------------------

        if not name:

            error = "Item name is required."

        # -----------------------------
        # Validate code
        # -----------------------------

        elif not code:

            error = "Item code is required."

        elif MenuItem.objects.filter(
            code__iexact=code
        ).exists():

            error = "A menu item with this code already exists."

        # -----------------------------
        # Validate category
        # -----------------------------

        elif not category_id:

            error = "Please select a category."

        else:

            category = Category.objects.filter(
                id=category_id,
                is_active=True,
            ).first()

            if category is None:

                error = "Invalid category."

            # -----------------------------
            # Validate price
            # -----------------------------

            else:

                try:

                    price_rupees = float(
                        price_text
                    )

                    if price_rupees < 0:

                        error = (
                            "Price cannot be negative."
                        )

                    else:

                        price_paise = round(
                            price_rupees * 100
                        )

                except (
                    ValueError,
                    TypeError,
                ):

                    error = "Enter a valid price."

        # -----------------------------
        # Create item
        # -----------------------------

        if error is None:

            MenuItem.objects.create(
                category=category,
                name=name,
                price=price_paise,
                code=code,
            )

            return redirect(
                "admin_panel:menu_items"
            )

    return render(
        request,
        "admin_panel/menu_item_form.html",
        {
            "error": error,
            "item": None,
            "categories": categories,
        },
    )


@login_required
def menu_item_edit(request, item_id):

    item = get_object_or_404(
        MenuItem,
        id=item_id,
    )

    categories = Category.objects.filter(
        is_active=True
    ).order_by(
        "display_order",
        "name",
    )

    error = None

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        code = request.POST.get(
            "code",
            "",
        ).strip().upper()

        price_text = request.POST.get(
            "price",
            "",
        ).strip()

        category_id = request.POST.get(
            "category",
            "",
        )

        # -----------------------------
        # Validate name
        # -----------------------------

        if not name:

            error = "Item name is required."

        # -----------------------------
        # Validate code
        # -----------------------------

        elif not code:

            error = "Item code is required."

        elif MenuItem.objects.filter(
            code__iexact=code
        ).exclude(
            id=item.id
        ).exists():

            error = "A menu item with this code already exists."

        # -----------------------------
        # Validate category
        # -----------------------------

        elif not category_id:

            error = "Please select a category."

        else:

            category = Category.objects.filter(
                id=category_id,
                is_active=True,
            ).first()

            if category is None:

                error = "Invalid category."

            else:

                # -----------------------------
                # Validate price
                # -----------------------------

                try:

                    price_rupees = float(
                        price_text
                    )

                    if price_rupees < 0:

                        error = (
                            "Price cannot be negative."
                        )

                    else:

                        price_paise = round(
                            price_rupees * 100
                        )

                except (
                    ValueError,
                    TypeError,
                ):

                    error = "Enter a valid price."

        # -----------------------------
        # Update item
        # -----------------------------

        if error is None:

            item.name = name
            item.code = code
            item.price = price_paise
            item.category = category

            item.save(
                update_fields=[
                    "name",
                    "code",
                    "price",
                    "category",
                ]
            )

            return redirect(
                "admin_panel:menu_items"
            )

    return render(
        request,
        "admin_panel/menu_item_form.html",
        {
            "error": error,
            "item": item,
            "categories": categories,
            "price_rupees": item.price / 100,
        },
    )


@login_required
def menu_item_toggle(request, item_id):

    item = get_object_or_404(
        MenuItem,
        id=item_id,
    )

    item.is_active = not item.is_active

    item.save(
        update_fields=["is_active"]
    )

    return redirect(
        "admin_panel:menu_items"
    )

@login_required
def settings_page(request):

    tax_enabled_setting = Setting.objects.filter(
        key="tax_enabled"
    ).first()

    tax_rate_setting = Setting.objects.filter(
        key="tax_rate"
    ).first()

    tax_enabled = (
        tax_enabled_setting is not None
        and tax_enabled_setting.value.lower()
        in {"true", "1", "yes", "on"}
    )

    tax_rate = (
        tax_rate_setting.value
        if tax_rate_setting
        else "0"
    )

    error = None
    success = None

    if request.method == "POST":

        tax_enabled = (
            request.POST.get("tax_enabled") == "on"
        )

        tax_rate = request.POST.get(
            "tax_rate",
            "0",
        ).strip()

        try:

            tax_rate_value = float(tax_rate)

            if tax_rate_value < 0:
                error = "Tax rate cannot be negative."

        except ValueError:

            error = "Enter a valid tax rate."

        if error is None:

            Setting.objects.update_or_create(
                key="tax_enabled",
                defaults={
                    "value": (
                        "true"
                        if tax_enabled
                        else "false"
                    )
                },
            )

            Setting.objects.update_or_create(
                key="tax_rate",
                defaults={
                    "value": tax_rate,
                },
            )

            success = "Settings saved successfully."

    return render(
        request,
        "admin_panel/settings.html",
        {
            "tax_enabled": tax_enabled,
            "tax_rate": tax_rate,
            "error": error,
            "success": success,
        },
    )

@login_required
def sections(request):

    section_list = Section.objects.all().order_by(
        "display_order",
        "name",
    )

    return render(
        request,
        "admin_panel/sections.html",
        {
            "sections": section_list,
        },
    )


@login_required
def section_add(request):

    error = None

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        display_order = request.POST.get(
            "display_order",
            "0",
        ).strip()

        if not name:

            error = "Section name is required."

        elif Section.objects.filter(
            name__iexact=name
        ).exists():

            error = "A section with this name already exists."

        else:

            try:

                display_order = int(
                    display_order
                )

                if display_order < 0:
                    error = (
                        "Display order cannot be negative."
                    )

            except ValueError:

                error = "Display order must be a number."

        if error is None:

            Section.objects.create(
                name=name,
                display_order=display_order,
            )

            return redirect(
                "admin_panel:sections"
            )

    return render(
        request,
        "admin_panel/section_form.html",
        {
            "error": error,
            "section": None,
        },
    )


@login_required
def section_edit(request, section_id):

    section = get_object_or_404(
        Section,
        id=section_id,
    )

    error = None

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        display_order = request.POST.get(
            "display_order",
            "0",
        ).strip()

        if not name:

            error = "Section name is required."

        elif Section.objects.filter(
            name__iexact=name
        ).exclude(
            id=section.id
        ).exists():

            error = "A section with this name already exists."

        else:

            try:

                display_order = int(
                    display_order
                )

                if display_order < 0:
                    error = (
                        "Display order cannot be negative."
                    )

            except ValueError:

                error = "Display order must be a number."

        if error is None:

            section.name = name
            section.display_order = display_order

            section.save(
                update_fields=[
                    "name",
                    "display_order",
                ]
            )

            return redirect(
                "admin_panel:sections"
            )

    return render(
        request,
        "admin_panel/section_form.html",
        {
            "error": error,
            "section": section,
        },
    )


@login_required
def section_toggle(request, section_id):

    section = get_object_or_404(
        Section,
        id=section_id,
    )

    section.is_active = not section.is_active

    section.save(
        update_fields=["is_active"]
    )

    return redirect(
        "admin_panel:sections"
    )

@login_required
def tables(request):

    table_list = (
        Table.objects
        .select_related("section")
        .order_by(
            "section__display_order",
            "display_order",
            "name",
        )
    )

    return render(
        request,
        "admin_panel/tables.html",
        {
            "tables": table_list,
        },
    )


@login_required
def table_add(request):

    sections = Section.objects.filter(
        is_active=True
    ).order_by(
        "display_order",
        "name",
    )

    error = None

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        display_order = request.POST.get(
            "display_order",
            "0",
        ).strip()

        section_id = request.POST.get(
            "section",
            "",
        )

        # -----------------------------
        # Validate name
        # -----------------------------

        if not name:

            error = "Table name is required."

        # -----------------------------
        # Validate section
        # -----------------------------

        elif not section_id:

            error = "Please select a section."

        else:

            section = Section.objects.filter(
                id=section_id,
                is_active=True,
            ).first()

            if section is None:

                error = "Invalid section."

        # -----------------------------
        # Validate display order
        # -----------------------------

        if error is None:

            try:

                display_order = int(
                    display_order
                )

                if display_order < 0:

                    error = (
                        "Display order cannot be negative."
                    )

            except ValueError:

                error = (
                    "Display order must be a number."
                )

        # -----------------------------
        # Check duplicate table name
        # -----------------------------

        if error is None:

            if Table.objects.filter(
                name__iexact=name
            ).exists():

                error = (
                    "A table with this name already exists."
                )

        # -----------------------------
        # Create table
        # -----------------------------

        if error is None:

            Table.objects.create(
                section=section,
                name=name,
                display_order=display_order,
                status=Table.Status.VACANT,
            )

            return redirect(
                "admin_panel:tables"
            )

    return render(
        request,
        "admin_panel/table_form.html",
        {
            "error": error,
            "table": None,
            "sections": sections,
        },
    )


@login_required
def table_edit(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
    )

    sections = Section.objects.filter(
        is_active=True
    ).order_by(
        "display_order",
        "name",
    )

    error = None

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        display_order = request.POST.get(
            "display_order",
            "0",
        ).strip()

        section_id = request.POST.get(
            "section",
            "",
        )

        # -----------------------------
        # Validate name
        # -----------------------------

        if not name:

            error = "Table name is required."

        # -----------------------------
        # Validate section
        # -----------------------------

        elif not section_id:

            error = "Please select a section."

        else:

            section = Section.objects.filter(
                id=section_id,
                is_active=True,
            ).first()

            if section is None:

                error = "Invalid section."

        # -----------------------------
        # Validate display order
        # -----------------------------

        if error is None:

            try:

                display_order = int(
                    display_order
                )

                if display_order < 0:

                    error = (
                        "Display order cannot be negative."
                    )

            except ValueError:

                error = (
                    "Display order must be a number."
                )

        # -----------------------------
        # Check duplicate name
        # -----------------------------

        if error is None:

            if Table.objects.filter(
                name__iexact=name
            ).exclude(
                id=table.id
            ).exists():

                error = (
                    "A table with this name already exists."
                )

        # -----------------------------
        # Update table
        # -----------------------------

        if error is None:

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

            return redirect(
                "admin_panel:tables"
            )

    return render(
        request,
        "admin_panel/table_form.html",
        {
            "error": error,
            "table": table,
            "sections": sections,
        },
    )


@login_required
def table_toggle(request, table_id):

    table = get_object_or_404(
        Table,
        id=table_id,
    )

    table.is_active = not table.is_active

    table.save(
        update_fields=["is_active"]
    )

    return redirect(
        "admin_panel:tables"
    )
@login_required
def bill_history(request):

    bills = Bill.objects.filter(
        status=Bill.Status.PAID
    ).order_by(
            "-paid_at",
            "-bill_number",
        )

    return render(
        request,
        "admin_panel/bill_history.html",
        {
            "bills": bills,
        },
    )


@login_required
def bill_detail(request, bill_id):

    bill = get_object_or_404(
        Bill,
        id=bill_id,
    )

    bill_items = bill.items.all().order_by(
        "category_name",
        "item_name",
    )

    food_items = bill_items.filter(
        category_type="FOOD"
    )

    drink_items = bill_items.filter(
        category_type="DRINK"
    )

    food_subtotal = sum(
        item.line_total
        for item in food_items
    )

    drink_subtotal = sum(
        item.line_total
        for item in drink_items
    )

    return render(
        request,
        "admin_panel/bill_detail.html",
        {
            "bill": bill,
            "food_items": food_items,
            "drink_items": drink_items,
            "food_subtotal": food_subtotal,
            "drink_subtotal": drink_subtotal,
        },
    )

@login_required
def cancel_bill(request, bill_id):

    bill = get_object_or_404(
        Bill,
        id=bill_id,
    )

    # Only POST is allowed for cancellation.
    if request.method != "POST":
        return redirect(
            "admin_panel:bill_detail",
            bill_id=bill.id,
        )

    # Prevent cancelling an already cancelled bill.
    if bill.status == Bill.Status.CANCELLED:
        return redirect(
            "admin_panel:bill_detail",
            bill_id=bill.id,
        )

    # Change the bill status.
    bill.status = Bill.Status.CANCELLED

    bill.save(
        update_fields=["status"]
    )

    # Once the bill is cancelled,
    # the table becomes vacant.
    table = bill.table

    table.status = Table.Status.VACANT

    table.save(
        update_fields=["status"]
    )

    return redirect(
        "admin_panel:cancelled_bill_history"
    )


@login_required
def cancelled_bill_history(request):

    bills = Bill.objects.filter(
        status=Bill.Status.CANCELLED
    ).select_related(
        "table"
    ).order_by(
        "-bill_number"
    )

    return render(
        request,
        "admin_panel/cancelled_bill_history.html",
        {
            "bills": bills,
        },
    )


@login_required
def admin_logout(request):

    logout(request)

    return redirect("admin_panel:login")