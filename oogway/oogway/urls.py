from django.contrib import admin
from django.urls import include, path

from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('analyze/', include('PostAnalyzer.urls')),
    path('panel/', include('Panel.urls')),
    path('exchange/', include('exchange.urls')),
    path('admin/', admin.site.urls),
]

urlpatterns += static( settings.STATIC_URL, document_root = settings.STATIC_ROOT)
