import logging
import uuid
import os
import stripe
import json
import requests
import base64
from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .discord_notifications import notify_nouvelle_commande, notify_stock_faible, notify_nouveau_message
from django.core.mail import send_mail
from django.core.cache import cache

from .models import User, Category, Product, Order, OrderDetails, Message, Carrier
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    ProductSerializer, OrderSerializer, MessageSerializer, CustomTokenObtainPairSerializer,
    CarrierSerializer
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


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

        # Désactiver le compte jusqu'à vérification
        user.is_active = False
        user.save()

        # Générer un token de vérification
        token = uuid.uuid4().hex
        cache.set(f'email_verify_{token}', user.user_id, timeout=86400)  # 24h

        verify_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token}"

        send_mail(
            subject="Vérifiez votre email — Shad's Candle 🕯️",
            message=f"Bonjour {user.firstname},\n\nMerci de vous être inscrit !\n\nCliquez sur ce lien pour activer votre compte :\n{verify_url}\n\nCe lien expire dans 24h.\n\nL'équipe Shad's Candle",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {'message': "Compte créé ! Vérifiez votre email pour l'activer."},
            status=status.HTTP_201_CREATED
        )


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

        refresh = CustomTokenObtainPairSerializer.get_token(user)
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
        orders     = Order.objects.filter(user=instance).order_by('-date')
        orders_data = OrderSerializer(orders, many=True).data
        return Response({"user": serializer.data, "orders": orders_data})

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

        with transaction.atomic():
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
            

            # ── Calcul du transporteur ────────────────────────────────────
            carrier_id   = request.data.get('carrier_id')
            carrier_cost = None
            carrier_name = None

            if carrier_id:
                try:
                    carrier = Carrier.objects.get(pk=carrier_id, is_active=True)
                    total_commande = sum(
                        p.price * q for _, (p, q) in products.items()
                    )
                    if carrier.free_above and total_commande >= carrier.free_above:
                        carrier_cost = 0
                    else:
                        carrier_cost = carrier.price
                    carrier_name = carrier.name
                except Carrier.DoesNotExist:
                    return Response({'error': 'Transporteur invalide'}, status=status.HTTP_400_BAD_REQUEST)

            # ── 2. Création commande + décrémentation stock ───────────────────
            reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"
            order_data = request.data.copy()
            order_data['reference'] = reference

            serializer = self.get_serializer(data=order_data)
            serializer.is_valid(raise_exception=True)
            order = serializer.save(
                user=request.user,
                carrier=carrier_name,
                carrier_cost=carrier_cost,
            )

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
            # Notifier Discord
            details_list = list(OrderDetails.objects.filter(order=order))
            notify_nouvelle_commande(order, details_list)

            # Vérifier stock faible pour chaque produit
            for product_id, (product, quantity) in products.items():
                product.refresh_from_db()
                notify_stock_faible(product)

            # Email de confirmation de commande
            lignes = "\n".join(
                f"- {d.name} x{d.quantity} : {d.total / 100}€"
                for d in details_list
            )
            send_mail(
                subject=f"Confirmation de votre commande {order.reference} 🕯️",
                message=f"Bonjour {order.user.firstname},\n\nVotre commande {order.reference} a bien été reçue !\n\nDétail :\n{lignes}\n\nMerci pour votre confiance,\nL'équipe Shad's Candle",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.user.email],
                fail_silently=True,
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
        message = serializer.save(user=user)
        notify_nouveau_message(message)

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # On retourne 200 même si l'email n'existe pas (sécurité)
            return Response({'message': 'Si cet email existe, un lien a été envoyé.'})

        # Générer un token unique
        token = uuid.uuid4().hex
        # Stocker en cache 30 minutes
        cache.set(f'password_reset_{token}', user.user_id, timeout=1800)

        reset_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"

        send_mail(
            subject='Réinitialisation de votre mot de passe — Shads Candle',
            message=f'Cliquez sur ce lien pour réinitialiser votre mot de passe : {reset_url}\n\nCe lien expire dans 30 minutes.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({'message': 'Si cet email existe, un lien a été envoyé.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token    = request.data.get('token')
        password = request.data.get('password')

        if not token or not password:
            return Response({'error': 'Token et mot de passe requis'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = cache.get(f'password_reset_{token}')
        if not user_id:
            return Response({'error': 'Token invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        cache.delete(f'password_reset_{token}')

        return Response({'message': 'Mot de passe réinitialisé avec succès.'})
    
class EmailVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token manquant'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = cache.get(f'email_verify_{token}')
        if not user_id:
            return Response({'error': 'Token invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable'}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()
        cache.delete(f'email_verify_{token}')

        return Response({'message': 'Email vérifié ! Vous pouvez maintenant vous connecter.'})
    
class AdminOrderListView(generics.ListAPIView):
    serializer_class   = OrderSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Order.objects.select_related('user').all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []
        for order in queryset:
            order_data = self.get_serializer(order).data
            order_data['user_detail'] = {
                'email':     order.user.email,
                'firstname': order.user.firstname,
                'lastname':  order.user.lastname,
                'phone':     order.user.phone,
            }
            data.append(order_data)
        return Response(data)
    
class AdminUserListView(generics.ListAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset           = User.objects.all()

@csrf_exempt
def stripe_webhook(request):
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Payload invalide'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Signature invalide'}, status=400)

    if event['type'] == 'checkout.session.completed':
        session  = event['data']['object']
        metadata = session.metadata.to_dict() if session.metadata else {}
        user_id  = metadata.get('user_id')
        items    = json.loads(metadata.get('items', '[]'))

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur introuvable'}, status=400)

        with transaction.atomic():
            reference = f"CMD-{uuid.uuid4().hex[:8].upper()}"
            order = Order.objects.create(
                reference = reference,
                user      = user,
                paid      = True,
                stripe_id = session.id,
                address   = metadata.get('address', ''),
                city      = metadata.get('city', ''),
                zip_code  = metadata.get('zip_code', ''),
                country   = metadata.get('country', 'FR'),
            )

            details_list = []
            for item in items:
                try:
                    product = Product.objects.select_for_update().get(pk=item['product_id'])
                except Product.DoesNotExist:
                    continue

                quantity = int(item.get('quantity', 1))
                if product.stock >= quantity:
                    Product.objects.filter(pk=product.product_id).update(
                        stock=F('stock') - quantity
                    )
                    detail = OrderDetails.objects.create(
                        order    = order,
                        product  = product,
                        name     = product.name,
                        price    = product.price,
                        quantity = quantity,
                        total    = product.price * quantity,
                    )
                    details_list.append(detail)
                    notify_stock_faible(product)

            notify_nouvelle_commande(order, details_list)

            lignes = "\n".join(f"- {d.name} x{d.quantity} : {d.total / 100}€" for d in details_list)
            send_mail(
                subject=f"Confirmation de votre commande {order.reference} 🕯️",
                message=f"Bonjour {user.firstname},\n\nVotre commande {order.reference} a bien été reçue et payée !\n\nDétail :\n{lignes}\n\nMerci pour votre confiance,\nL'équipe Shad's Candle",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

    return JsonResponse({'status': 'ok'})

class CarrierListView(generics.ListCreateAPIView):
    serializer_class   = CarrierSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        return Carrier.objects.filter(is_active=True).order_by('price')


class CarrierDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = CarrierSerializer
    permission_classes = [IsAdminOrReadOnly]
    queryset           = Carrier.objects.all()


class CreateShippingLabelView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Commande introuvable'}, status=status.HTTP_404_NOT_FOUND)

        data      = request.data
        recipient = data.get('recipient', {})

        address_parts = recipient.get('address', '').split(' ', 1)
        house_number  = address_parts[0] if address_parts else ''
        street        = address_parts[1] if len(address_parts) > 1 else recipient.get('address', '')

        payload = {
            "apply_shipping_defaults": True,
            "apply_shipping_rules": True,
            "to_address": {
                "name":         f"{recipient.get('firstName', '')} {recipient.get('lastName', '')}",
                "address_line_1": street,
                "house_number": house_number,
                "postal_code":  recipient.get('zipCode', ''),
                "city":         recipient.get('city', ''),
                "country_code": recipient.get('country', 'FR'),
                "phone_number": recipient.get('phone', ''),
                "email":        recipient.get('email', ''),
            },
            "parcels": [
                {
                    "weight":       "1.000",
                    "order_number": order.reference,
                }
            ],
        }

        public_key  = settings.SENDCLOUD_PUBLIC_KEY
        secret_key  = settings.SENDCLOUD_SECRET_KEY
        credentials = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()

        try:
            res = requests.post(
                "https://panel.sendcloud.sc/api/v3/shipments/create-announce",
                json=payload,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            res.raise_for_status()
            data   = res.json()
            parcel = data.get('data', {}).get('parcels', [{}])[0]
            label  = parcel.get('label_file', '')

            order.label = label
            order.save()

            return Response({'pdf_url': label, 'parcel_id': parcel.get('id')})
        except requests.RequestException as e:
            error_detail = ''
            if hasattr(e, 'response') and e.response is not None:
                error_detail = e.response.text
                logger.error(f"Détail Sendcloud : {error_detail}")
            logger.error(f"Erreur Sendcloud : {e}")
            return Response({'error': str(e), 'detail': error_detail}, status=status.HTTP_502_BAD_GATEWAY)