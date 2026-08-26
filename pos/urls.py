from django.urls import path
from . import sw
from . import views


app_name = "pos"


urlpatterns = [

    path(
        "",
        views.table_screen,
        name="table_screen",
    ),

    path(
        "table/<int:table_id>/",
        views.order_screen,
        name="order_screen",
    ),

    path(
        "table/<int:table_id>/send-to-kitchen/",
        views.send_to_kitchen,
        name="send_to_kitchen",
    ),

    path(
        "table/<int:table_id>/current-order/",
        views.current_order,
        name="current_order",
    ),

    path(
        "table/<int:table_id>/cancel-order/",
        views.cancel_order,
        name="cancel_order",
    ),

    path(
        "table/<int:table_id>/generate-bill/",
        views.generate_bill,
        name="generate_bill",
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
        "sw.js",
        sw.service_worker,
        name="service_worker",
    ),


    # =================================
    # MANAGEMENT
    # =================================

    path(
        "management/",
        views.management_dashboard,
        name="management_dashboard",
    ),


    # =================================
    # CATEGORY MANAGEMENT
    # =================================

    path(
        "management/menu/category/create/",
        views.management_create_category,
        name="management_create_category",
    ),

    path(
        "management/menu/category/<int:category_id>/toggle/",
        views.management_toggle_category,
        name="management_toggle_category",
    ),

    path(
        "management/menu/category/<int:category_id>/edit/",
        views.management_edit_category,
        name="management_edit_category",
    ),


    # =================================
    # MENU ITEM MANAGEMENT
    # =================================

    path(
        "management/menu/item/create/",
        views.management_create_menu_item,
        name="management_create_menu_item",
    ),

    path(
        "management/menu/item/<int:item_id>/toggle/",
        views.management_toggle_menu_item,
        name="management_toggle_menu_item",
    ),

    path(
        "management/menu/item/<int:item_id>/edit/",
        views.management_edit_menu_item,
        name="management_edit_menu_item",
    ),


    # =================================
    # MENU API
    # =================================

    path(
        "menu-items/",
        views.menu_items_api,
        name="menu_items_api",
    ),

    path(
        "management/tax/save/",
        views.management_save_tax,
        name="management_save_tax",
    ),

    # =================================
    # SECTION MANAGEMENT
    # =================================

    path(
        "management/table/section/create/",
        views.management_create_section,
        name="management_create_section",
    ),

    path(
        "management/table/section/<int:section_id>/edit/",
        views.management_edit_section,
        name="management_edit_section",
    ),

    path(
        "management/table/section/<int:section_id>/toggle/",
        views.management_toggle_section,
        name="management_toggle_section",
    ),


    # =================================
    # TABLE MANAGEMENT
    # =================================

    path(
        "management/table/create/",
        views.management_create_table,
        name="management_create_table",
    ),

    path(
        "management/table/<int:table_id>/edit/",
        views.management_edit_table,
        name="management_edit_table",
    ),

    path(
        "management/table/<int:table_id>/toggle/",
        views.management_toggle_table,
        name="management_toggle_table",
    ),

    path(
        "management/analytics/",
        views.management_analytics,
        name="management_analytics",
    ),
]