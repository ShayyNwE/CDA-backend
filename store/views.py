import logging
import uuid
from django.db import transaction
from django.db.models import F
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.http import JsonResponse

from .models import User, Category, Product, Order, OrderDetails, Message
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    ProductSerializer, OrderSerializer, MessageSerializer
)

logger = logging.getLogger(__name__)


def api_health_check(request):
    return JsonResponse({"status": "ok", "message": "Le Back Django répond bien !"})


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes   = [AnonRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes   = [LoginThrottle]

    def post(self, request):
        email    = request.data.get('email')
        password = request.data.get('password')

        error_response = Response(
            {'error': 'Identifiants invalides'},
            status=status.HTTP_401_UNAUTHORIZED
        )

        if not email or not password:
            return error_response

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response

        if not user.check_password(password):
            return error_response

        if not user.is_active:
            return Response({'error': 'Compte désactivé'}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Token de rafraîchissement requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"Logout réussi : {request.user.email}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TokenError:
            return Response(
                {'error': 'Token invalide ou déjà révoqué'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"user": serializer.data, "orders": []})

    def update(self, request, *args, **kwargs):
        data = request.data.copy()
        data.pop('roles', None)
        data.pop('is_staff', None)
        data.pop('is_superuser', None)
        kwargs['partial'] = kwargs.get('partial', False)
        serializer = self.get_serializer(
            self.get_object(), data=data, partial=kwargs['partial']
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"user": serializer.data})


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class CategoryListView(generics.ListCreateAPIView):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductListView(generics.ListCreateAPIView):
    serializer_class   = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset  = Product.objects.prefetch_related('categories').all()
        category  = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if category:
            queryset = queryset.filter(categories__name__icontains=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        return queryset


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Product.objects.prefetch_related('categories').all()
    serializer_class   = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class OrderListView(generics.ListCreateAPIView):
    serializer_class   = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        items = request.data.get('items', [])

        # ── 1. Vérification du stock ──────────────────────────────────────
        errors   = []
        products = {}

        for item in items:
            product_id = item.get('product_id')
            quantity   = int(item.get('quantity', 1))

            try:
                product = Product.objects.select_for_update().get(pk=product_id)
            except Product.DoesNotExist:
                errors.append(f"Produit {product_id} introuvable.")
                continue

            if product.stock < quantity:
                errors.append(
                    f"Stock insuffisant pour « {product.name} » "
                    f"(disponible : {product.stock}, demandé : {quantity})."
                )
            else:
                products[product_id] = (product, quantity)

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # ── 2. Création commande + décrémentation stock ───────────────────
        with transaction.atomic():
            reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"

            order_data = request.data.copy()
            order_data['reference'] = reference

            serializer = self.get_serializer(data=order_data)
            serializer.is_valid(raise_exception=True)
            order = serializer.save(user=request.user)

            for product_id, (product, quantity) in products.items():
                Product.objects.filter(pk=product_id).update(
                    stock=F('stock') - quantity
                )
                OrderDetails.objects.create(
                    order    = order,
                    product  = product,
                    name     = product.name,
                    price    = product.price,
                    quantity = quantity,
                    total    = product.price * quantity,
                )

        return Response(
            self.get_serializer(order).data,
            status=status.HTTP_201_CREATED
        )


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class   = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


def get_slider_products(request):
    products = Product.objects.prefetch_related('categories').all()[:10]
    data = [{
        "id":    p.product_id,
        "name":  p.name,
        "price": str(p.price),
        "image": p.image if p.image else "/images/bougiesParf.png",
        "stock": p.stock,
    } for p in products]
    return JsonResponse(data, safe=False)


class MessageView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    queryset         = Message.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)