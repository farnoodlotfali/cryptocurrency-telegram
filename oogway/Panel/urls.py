from django.contrib.auth.views import LogoutView
from django.urls import path
from django.conf.urls import (
handler400, handler403, handler404, handler500
)
from . import views

app_name = "Panel"

handler404 = 'Panel.views.custom_404_view'

urlpatterns = [
    path(
        "login/",
        views.CustomLoginView.as_view(template_name="login.html"),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("channels/", views.channel_list, name="channel_list"),


    path("channels/<int:channel_id>/", views.channel_detail, name="channel_detail"),
    path("posts/", views.post_list, name="post_list"),
    path("posts/<int:post_id>/", views.post_detail, name="post_detail"),
    path("", views.home, name="home"),
    path("symbol/", views.get_symbols, name="symbol"),
    path("predict/", views.get_predicts, name="predict"),
    path("market/", views.get_markets, name="market"),
    path("settings/", views.get_settings, name="settings"),
    path("statistic/", views.get_statistic, name="statistic"),
    path("settings/update", views.update_settings, name="update_settings"),
    path(
        "change-channel-trade/<int:channel_id>",
        views.change_channel_trade,
        name="change_channel_trade",
    ),
    path("change-predict-status/<int:predict_id>/<str:status>/", views.change_predict_status, name="change_predict_status"),

    # api
    path("get-posts-api/", views.get_posts_api, name="get_posts_api"),
    path("get-symbol-api/", views.get_symbols_api, name="get_symbols_api"),
    path(
        "cancel-order-api/<str:symbol>/<int:order_id>/<str:market>/",
        views.cancel_order,
        name="cancel_order",
    ),

    # charts
    path("chart/predict-status/", views.predict_status_chart, name="chart_predict_status"),
    path("chart/channel-criteria/", views.criteria_chart_for_channel, name="chart_channel_criteria"),
    path("chart/tp-index/", views.tp_index_chart, name="tp_index_chart"),
    path("chart/channel-predict-status/", views.channel_predict_status_chart, name="channel_predict_status_chart"),

    # test
    path("advance/", views.advance_test, name="advance_test"),   
    path("widgets/", views.widgets_test, name="widgets_test"),   
    path("charts/", views.charts_test, name="charts_test"),
    path("validation/", views.validation_test, name="validation_test"),
    path("test/", views.getPhoneNumberAndCode, name="test"),


]
