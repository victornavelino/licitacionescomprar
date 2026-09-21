from django.urls import path

from . import views

app_name = "pliegos"

urlpatterns = [
    path("pliegos/", views.pliegos_proxima_apertura, name="proxima-apertura"),
    path(
        "pliegos/json/",
        views.pliegos_proxima_apertura_json,
        name="proxima-apertura-json",
    ),
]
