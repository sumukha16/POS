from django.urls import path, include
from django.contrib import admin
from django.shortcuts import redirect


def home(request):
    if request.user.is_authenticated:
        return redirect("pos:table_screen")

    return redirect("admin_panel:login")


urlpatterns = [
    path("", home, name="home"),

    path(
        "django-admin/",
        admin.site.urls,
    ),

    path(
        "admin-panel/",
        include("admin_panel.urls"),
    ),

    path(
        "pos/",
        include("pos.urls"),
    ),
]