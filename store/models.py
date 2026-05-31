from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator


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
    password  = models.CharField(max_length=255)
    firstname = models.CharField(max_length=100, default="")
    lastname  = models.CharField(max_length=100, default="")
    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name        = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "category"

    def __str__(self):
        return self.name
    
class Carrier(models.Model):
    carrier_id = models.AutoField(primary_key=True)
    name       = models.CharField(max_length=100)
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    free_above = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        db_table = "carrier"

    def __str__(self):
        return self.name


class Product(models.Model):
    product_id    = models.AutoField(primary_key=True)
    name          = models.CharField(max_length=255)
    description   = models.TextField(blank=True, null=True)
    price         = models.DecimalField(max_digits=10, decimal_places=2)
    image         = models.CharField(max_length=255, blank=True, null=True)
    customizable  = models.BooleanField(default=False)
    options       = models.JSONField(blank=True, null=True)
    weight        = models.IntegerField()
    stock         = models.IntegerField(default=0)
    categories    = models.ManyToManyField(
        Category,
        through="ProductCategory",
        related_name="products",
    )

    class Meta:
        db_table = "product"

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        db_table = "product_category"
        unique_together = ("product", "category")


class Order(models.Model):
    order_id      = models.AutoField(primary_key=True)
    reference     = models.CharField(max_length=50, unique=True)
    carrier       = models.CharField(max_length=100, blank=True, null=True)
    carrier_cost  = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    address       = models.TextField(blank=True, null=True)
    paid          = models.BooleanField(default=False)
    stripe_id     = models.CharField(max_length=255, blank=True, null=True)
    date          = models.DateTimeField(auto_now_add=True)
    label         = models.CharField(max_length=500, blank=True, null=True)
    user          = models.ForeignKey(User, on_delete=models.RESTRICT, related_name="orders")

    class Meta:
        db_table = "order"
        ordering = ["-date"]

    def __str__(self):
        return f"Commande {self.reference}"


class OrderDetails(models.Model):
    order_detail_id = models.AutoField(primary_key=True)
    name            = models.CharField(max_length=255)
    price           = models.DecimalField(max_digits=10, decimal_places=2)
    quantity        = models.IntegerField()
    total           = models.DecimalField(max_digits=10, decimal_places=2)
    order           = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="details")
    product         = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "order_details"


phone_validator = RegexValidator(
    regex=r'^\+?[\d\s\-().]{7,20}$',
    message="Numéro de téléphone invalide."
)


class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    firstname  = models.CharField(max_length=100)
    lastname   = models.CharField(max_length=100)
    email      = models.EmailField(max_length=320)
    phone      = models.CharField(max_length=15, validators=[phone_validator])
    subject    = models.CharField(max_length=255)
    message    = models.TextField()
    date       = models.DateTimeField(auto_now_add=True)
    user       = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )

    class Meta:
        db_table  = "messages"
        ordering  = ["-date"]

    def __str__(self):
        return f"{self.subject} — {self.email}"