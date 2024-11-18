from django.contrib.auth.views import LogoutView
from django.urls import path, reverse
from . import views


app_name = "exchange"

urlpatterns = [
    path("save-symbols/", views.save_symbols, name="save_symbols"),
    path("cancel-order/<path:symbol>/<int:order_id>/<str:market>/", views.cancel_order, name="cancel_order"),
]
