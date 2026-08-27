from django.urls import path

from . import views


app_name = "admin_panel"


urlpatterns = [
    path(
        "login/",
        views.admin_login,
        name="login",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "users/",
        views.user_management,
        name="user_management",
    ),

    path(
        "logout/",
        views.admin_logout,
        name="logout",
    ),

    path(
        "categories/",
        views.categories,
        name="categories",
    ),

    path(
        "categories/add/",
        views.category_add,
        name="category_add",
    ),

    path(
        "categories/<int:category_id>/edit/",
        views.category_edit,
        name="category_edit",
    ),

    path(
        "categories/<int:category_id>/toggle/",
        views.category_toggle,
        name="category_toggle",
    ),

    path(
    "menu/",
    views.menu_items,
    name="menu_items",
    ),

    path(
        "menu/add/",
        views.menu_item_add,
        name="menu_item_add",
    ),

    path(
        "menu/<int:item_id>/edit/",
        views.menu_item_edit,
        name="menu_item_edit",
    ),

    path(
        "menu/<int:item_id>/toggle/",
        views.menu_item_toggle,
        name="menu_item_toggle",
    ),

    path(
        "settings/",
        views.settings_page,
        name="settings",
    ),

    path(
        "sections/",
        views.sections,
        name="sections",
    ),

    path(
        "sections/add/",
        views.section_add,
        name="section_add",
    ),

    path(
        "sections/<int:section_id>/edit/",
        views.section_edit,
        name="section_edit",
    ),

    path(
        "sections/<int:section_id>/toggle/",
        views.section_toggle,
        name="section_toggle",
    ),

    path(
        "tables/",
        views.tables,
        name="tables",
    ),

    path(
        "tables/add/",
        views.table_add,
        name="table_add",
    ),

    path(
        "tables/<int:table_id>/edit/",
        views.table_edit,
        name="table_edit",
    ),

    path(
        "tables/<int:table_id>/toggle/",
        views.table_toggle,
        name="table_toggle",
    ),

    path(
        "bills/",
        views.bill_history,
        name="bill_history",
    ),

    path(
        "bills/<int:bill_id>/",
        views.bill_detail,
        name="bill_detail",
    ),
    path(
        "bills/<int:bill_id>/cancel/",
        views.cancel_bill,
        name="cancel_bill",
    ),

    path(
        "cancelled-bills/",
        views.cancelled_bill_history,
        name="cancelled_bill_history",
    ),
]
