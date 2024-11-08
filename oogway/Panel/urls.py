from django.contrib.auth.views import LogoutView
from django.urls import path
from django.conf.urls import (
handler400, handler403, handler404, handler500
)
from . import views

app_name = "Panel"

handler404 = 'Panel.views.custom_404_view'

urlpatterns = [
    # auth
    path("login/", views.CustomLoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="/panel/login"), name="logout"),


    path("channels/", views.channel_list, name="channel_list"),
    path("channels/<int:channel_id>/", views.channel_detail, name="channel_detail"),
    path("posts/", views.post_list, name="post_list"),
    path("", views.home, name="home"),
    path("symbol/", views.get_symbols, name="symbol"),
    path("predict/", views.get_predicts, name="predict"),
    path("predict/<int:post_id>/", views.predict_detail, name="predict_detail"),
    path("market/", views.get_markets, name="market"),
    path("settings/", views.get_settings, name="settings"),
    path("predict-stat/", views.get_predicts_stat, name="predict_stat"),
    path("channel-stat/", views.get_channels_stat, name="channel_stat"),
    path("settings/update", views.update_settings, name="update_settings"),
    path("change-channel-trade/<int:channel_id>", views.change_channel_trade, name="change_channel_trade"),
    path("change-predict-status/<int:predict_id>/<str:status>/", views.change_predict_status, name="change_predict_status"),

    # charts
    path("chart/channel-stat-per-month-chart/", views.channel_stat_per_month_chart, name="channel_stat_per_month_chart"),
    path("chart/channel-stat-total-chart/", views.channel_stat_total_chart, name="channel_stat_total_chart"),

    # test
    path("advance/", views.advance_test, name="advance_test"),   
    path("widgets/", views.widgets_test, name="widgets_test"),   
    path("charts/", views.charts_test, name="charts_test"),
    path("validation/", views.validation_test, name="validation_test"),

]
