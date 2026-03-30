from rest_framework import serializers
from .models import User, Category, Product, Order, OrderDetails, Cart, CartItem


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['user_id', 'email', 'firstname', 'lastname', 'roles']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['email', 'password', 'firstname', 'lastname']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_euros   = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = '__all__'

    def get_price_euros(self, obj):
        return obj.price / 100


class OrderDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrderDetails
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    details = OrderDetailsSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = '__all__'


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'image', 'is_customizable']

class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'custom_name', 'custom_scent']