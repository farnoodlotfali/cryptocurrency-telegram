from django.urls import path

from . import views

app_name = "Analyze"

urlpatterns = [
    path("get_user_posts/", views.get_user_posts_view, name="get_user_posts"),
]
