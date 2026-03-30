from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Category, Product, Order
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    ProductSerializer, OrderSerializer
)


class LoginThrottle(AnonRateThrottle):
    """Throttle strict dédié au login : 5 tentatives/minute."""
    scope = 'login'


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        # Message générique pour ne pas révéler si l'email existe
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
            return Response(
                {'error': 'Compte désactivé'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Empêche un user de modifier ses propres roles ou is_staff
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
    """Lecture pour tous les authentifiés, écriture réservée aux admins."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class OrderListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Force l'association de la commande à l'user connecté
        serializer.save(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)