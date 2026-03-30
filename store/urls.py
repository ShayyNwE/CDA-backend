from django.urls import path
from . import views
from .views import api_health_check
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, ProfileView,
    CategoryListView, ProductListView, ProductDetailView,
    OrderListView, OrderDetailView
)

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(),  name='register'),
    path('auth/login/',    LoginView.as_view(),     name='login'),
    path('auth/refresh/',  TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/',  ProfileView.as_view(),   name='profile'),

    # Catégories
    path('categories/',    CategoryListView.as_view(), name='categories'),

    # Produits
    path('products/',      ProductListView.as_view(),       name='products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),

    # Commandes
    path('orders/',        OrderListView.as_view(),          name='orders'),
    path('orders/<int:pk>/', OrderDetailView.as_view(),      name='order-detail'),

    # Health Check
    path('health/', api_health_check, name='api_health_check'),

    # Panier
    path('cart/',                          views.get_cart,          name='api_get_cart'),
    path('cart/add/',                      views.add_to_cart,       name='api_add_to_cart'),
    path('cart/update/<int:item_id>/',     views.update_cart_item,  name='api_update_cart_item'),
    path('cart/remove/<int:item_id>/',     views.remove_cart_item,  name='api_remove_cart_item'),
]