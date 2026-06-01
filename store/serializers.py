import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Category, Product, Order, OrderDetails, Message, Carrier
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'email', 'firstname', 'lastname', 'roles', 'phone']
        read_only_fields = ['user_id', 'roles']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['email', 'password', 'firstname', 'lastname','phone']

    def validate_password(self, value):
        regex = (
            r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)'
            r'(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{12,}$'
        )
        if not re.match(regex, value):
            raise serializers.ValidationError(
                "Le mot de passe doit contenir au moins 12 caractères. "
                "Une majuscule, une minuscule, un chiffre et un caractère spécial (@$!%*?&#)."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Category.objects.all(),
        source='categories',
    )

    class Meta:
        model = Product
        fields = [
            'product_id', 'name', 'description', 'price', 'image',
            'customizable', 'options', 'weight', 'stock', 'categories', 'category_ids',
        ]

    def create(self, validated_data):
        categories = validated_data.pop('categories', [])
        product = Product.objects.create(**validated_data)
        product.categories.set(categories)
        return product

    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if categories is not None:
            instance.categories.set(categories)
        return instance


class OrderDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDetails
        fields = '__all__'
        read_only_fields = ['order_detail_id', 'order']


class OrderSerializer(serializers.ModelSerializer):
    details = OrderDetailsSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = [
            'order_id', 'user', 'paid',
            'stripe_id', 'date',
        ]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['message_id', 'date']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_staff'] = user.is_staff
        token['roles'] = user.roles
        return token
    
class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Carrier
        fields = '__all__'