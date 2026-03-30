import logging
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.shortcuts import get_object_or_404 
from django.http import JsonResponse

from .models import User, Category, Product, Order, Cart, CartItem, Message
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    ProductSerializer, OrderSerializer, CartItemSerializer, MessageSerializer
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


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes   = [LoginThrottle]

    def post(self, request):
        email = request.data.get('email')
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
            logger.warning(f"Tentative de login avec email inconnu : {email}")
            return error_response

        if not user.check_password(password):
            logger.warning(f"Mot de passe incorrect pour : {email}")
            return error_response

        if not user.is_active:
            logger.warning(f"Tentative de login sur compte inactif : {email}")
            return Response(
                {'error': 'Compte désactivé'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        logger.info(f"Login réussi : {email}")
        return Response({
            'access' : str(refresh.access_token),
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
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

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
        return Response(serializer.data)


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
    queryset           = Product.objects.all()
    serializer_class   = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Product.objects.all()
    serializer_class   = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class OrderListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


def get_slider_products(request):
    products = Product.objects.all()[:10] 
    data = []
    for p in products:
        data.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "image": p.image if p.image else "/images/bougiesParf.png"
        })
    return JsonResponse(data, safe=False)


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


@api_view(['GET'])
def get_cart(request):
    cart = get_or_create_cart(request)
    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def add_to_cart(request):
    cart = get_or_create_cart(request)
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))
    custom_name = request.data.get('custom_name')
    custom_scent = request.data.get('custom_scent')

    product = get_object_or_404(Product, id=product_id)

    cart_item = CartItem.objects.filter(
        cart=cart, 
        product=product, 
        custom_name=custom_name, 
        custom_scent=custom_scent
    ).first()

    if cart_item:
        cart_item.quantity += quantity
        cart_item.save()
    else:
        CartItem.objects.create(
            cart=cart, 
            product=product, 
            quantity=quantity, 
            custom_name=custom_name, 
            custom_scent=custom_scent
        )

    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    delta = int(request.data.get('delta', 0))
    cart_item.quantity += delta
    if cart_item.quantity <= 0:
        cart_item.delete()
    else:
        cart_item.save()

    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
def remove_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    cart_item.delete()
    return Response({'status': 'deleted'}, status=status.HTTP_204_NO_CONTENT)


class MessageView(generics.ListCreateAPIView):
    serializer_class   = MessageSerializer
    queryset           = Message.objects.all()

    def get_permissions(self):
        # Envoyer un message : tout le monde (formulaire de contact public)
        # Lire les messages : admins uniquement
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]