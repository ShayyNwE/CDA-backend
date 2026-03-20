from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("roles", ["ROLE_USER", "ROLE_ADMIN"])
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    user_id   = models.AutoField(primary_key=True)
    email     = models.EmailField(max_length=320, unique=True)
    roles     = models.JSONField(default=list)
    firstname = models.CharField(max_length=100, blank=True, null=True)
    lastname  = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name        = models.CharField(max_length=100)

    class Meta:
        db_table = "category"

    def __str__(self):
        return self.name


class Product(models.Model):
    id                    = models.AutoField(primary_key=True)
    name                  = models.CharField(max_length=200)
    description           = models.TextField(blank=True, null=True)
    price                 = models.IntegerField()
    image                 = models.CharField(max_length=255, blank=True, null=True)
    is_customizable       = models.SmallIntegerField(default=0)
    customization_options = models.JSONField(blank=True, null=True)
    weight                = models.IntegerField(blank=True, null=True)
    category              = models.ForeignKey(Category, on_delete=models.RESTRICT, related_name="products")

    class Meta:
        db_table = "product"

    def __str__(self):
        return self.name


class Order(models.Model):
    order_id           = models.AutoField(primary_key=True)
    reference          = models.CharField(max_length=50, unique=True)
    carrier_name       = models.CharField(max_length=100, blank=True, null=True)
    carrier_price      = models.IntegerField(blank=True, null=True)
    delivery_address   = models.TextField(blank=True, null=True)
    is_paid            = models.SmallIntegerField(default=0)
    stripe_session_id  = models.CharField(max_length=255, blank=True, null=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    shipping_label_url = models.CharField(max_length=500, blank=True, null=True)
    user               = models.ForeignKey(User, on_delete=models.RESTRICT, related_name="orders")

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commande {self.reference}"


class OrderDetails(models.Model):
    detail_id     = models.AutoField(primary_key=True)
    product_name  = models.CharField(max_length=200)
    product_price = models.IntegerField()
    quantity      = models.IntegerField()
    total         = models.IntegerField()
    order         = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="details")
    product       = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "order_details"