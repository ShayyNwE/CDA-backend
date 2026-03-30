from django.contrib import admin
from django.urls import path, include
from store.views import get_slider_products

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('store.urls')),
    path('api/products/slider/', get_slider_products),
]