from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views


app_name = "exchange"


urlpatterns = [
    path("save-symbols/", views.save_symbols, name="save_symbols"),
    path(
        "cancel-order/<str:symbol>/<int:order_id>/<str:market>/",
        views.cancel_order,
        name="cancel_order",
    ),
]
