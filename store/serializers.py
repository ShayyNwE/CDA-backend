import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Category, Product, Order, OrderDetails, CartItem, Message


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['user_id', 'email', 'firstname', 'lastname', 'roles']
        read_only_fields = ['user_id', 'roles']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model  = User
        fields = ['email', 'password', 'firstname', 'lastname']

    def validate_password(self, value):
        regex = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{12,}$'
        
        if not re.match(regex, value):
            raise serializers.ValidationError(
                "Le mot de passe doit contenir au moins 12 caractères. Une majuscule, une minuscule, un chiffre et un caractère spécial (@$!%*?&#)."
            )
        return value

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
        read_only_fields = ['detail_id', 'order']


class OrderSerializer(serializers.ModelSerializer):
    details = OrderDetailsSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = '__all__'
        read_only_fields = [
            'order_id', 'user', 'is_paid',
            'stripe_session_id', 'shipping_label_url', 'created_at',
        ]


class CartProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'image', 'is_customizable']


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'custom_name', 'custom_scent']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Message
        fields = '__all__'
        read_only_fields = ['message_id', 'created_at']