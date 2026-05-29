from django.urls import path
from .views import api_health_check
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    CategoryListView, ProductListView, ProductDetailView,
    OrderListView, OrderDetailView, MessageView,PasswordResetRequestView, PasswordResetConfirmView,EmailVerifyView
)

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(),      name='register'),
    path('auth/login/',    LoginView.as_view(),         name='login'),
    path('auth/logout/',   LogoutView.as_view(),        name='logout'),
    path('auth/refresh/',  TokenRefreshView.as_view(),  name='token_refresh'),
    path('auth/profile/',  ProfileView.as_view(),       name='profile'),

    # Catégories
    path('categories/',    CategoryListView.as_view(),  name='categories'),

    # Produits
    path('products/',          ProductListView.as_view(),    name='products'),
    path('products/<int:pk>/', ProductDetailView.as_view(),  name='product-detail'),

    # Commandes
    path('orders/',            OrderListView.as_view(),      name='orders'),
    path('orders/<int:pk>/',   OrderDetailView.as_view(),    name='order-detail'),

    # Messages
    path('messages/',          MessageView.as_view(),        name='messages'),

    #Email
    path('auth/password-reset/',         PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/verify-email/', EmailVerifyView.as_view(), name='verify_email'),

    # Health Check
    path('health/',            api_health_check,             name='api_health_check'),
]