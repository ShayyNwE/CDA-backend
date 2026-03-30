from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404 
from django.http import JsonResponse

from .models import User, Category, Product, Order, Cart, CartItem 
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    ProductSerializer, OrderSerializer, CartItemSerializer
)

def api_health_check(request):
    return JsonResponse({"status": "ok", "message": "Le Back Django répond bien !"})
    
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'error': 'Identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access'  : str(refresh.access_token),
            'refresh' : str(refresh),
        })

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class OrderListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

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


# ==========================================
# VUES DU PANIER (CART)
# ==========================================

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