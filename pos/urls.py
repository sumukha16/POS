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
    path(
        "management/",
        views.management_dashboard,
        name="management_dashboard",
    ),

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
]