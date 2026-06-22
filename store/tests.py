import pytest
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Category, Product


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='user@test.com', password='Motdepasse123!',
        firstname='User', lastname='Test'
    )


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        email='admin@test.com', password='Motdepasse123!',
        firstname='Admin', lastname='Test'
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name='Test catégorie')


@pytest.fixture
def product(db, category):
    p = Product.objects.create(
        name='Produit test',
        price=10.00,
        weight=100,
        stock=10,
    )
    p.categories.set([category])
    return p


def auth_client(client, user):
    """Retourne un client authentifié avec le token de l'user donné."""
    res = client.post('/api/auth/login/', {'email': user.email, 'password': 'Motdepasse123!'})
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}')
    return client


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

class TestRegister:
    def test_register_ok(self, client, db):
        res = client.post('/api/auth/register/', {
            'email':     'nouveau@test.com',
            'password':  'MotDePasseSecurise1!',
            'firstname': 'Tom',
            'lastname':  'Dupont',
        })
        assert res.status_code == status.HTTP_201_CREATED

    def test_register_mot_de_passe_trop_court(self, client, db):
        res = client.post('/api/auth/register/', {
            'email':    'x@test.com',
            'password': '123',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_email_duplique(self, client, user):
        res = client.post('/api/auth/register/', {
            'email':    'user@test.com',
            'password': 'MotDePasseSecurise1!',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST


class TestLogin:
    def test_login_ok(self, client, user):
        res = client.post('/api/auth/login/', {
            'email':    'user@test.com',
            'password': 'Motdepasse123!',
        })
        assert res.status_code == status.HTTP_200_OK
        assert 'access' in res.data
        assert 'refresh' in res.data

    def test_login_mauvais_mot_de_passe(self, client, user):
        res = client.post('/api/auth/login/', {
            'email':    'user@test.com',
            'password': 'mauvais',
        })
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_email_inexistant(self, client, db):
        res = client.post('/api/auth/login/', {
            'email':    'fantome@test.com',
            'password': 'nimporte',
        })
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_compte_inactif(self, client, db):
        u = User.objects.create_user(
            email='inactif@test.com', password='Motdepasse123!'
        )
        u.is_active = False
        u.save()
        res = client.post('/api/auth/login/', {
            'email': 'inactif@test.com', 'password': 'Motdepasse123!'
        })
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ──────────────────────────────────────────────
# PROFIL
# ──────────────────────────────────────────────

class TestProfile:
    def test_profil_non_authentifie(self, client):
        res = client.get('/api/auth/profile/')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_profil_authentifie(self, client, user):
        res = auth_client(client, user).get('/api/auth/profile/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['user']['email'] == user.email

    def test_user_ne_peut_pas_modifier_ses_roles(self, client, user):
        res = auth_client(client, user).patch('/api/auth/profile/', {'roles': ['ROLE_ADMIN']})
        assert res.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert 'ROLE_ADMIN' not in user.roles


# ──────────────────────────────────────────────
# PRODUITS
# ──────────────────────────────────────────────

class TestProducts:
    def test_liste_produits_sans_auth(self, client, product):
        res = client.get('/api/products/')
        assert res.status_code == status.HTTP_200_OK

    def test_creation_produit_user_normal_interdit(self, client, user, category):
        res = auth_client(client, user).post('/api/products/', {
            'name':         'Produit piraté',
            'price':        1,
            'weight':       100,
            'category_ids': [category.category_id],
        })
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_creation_produit_admin_ok(self, client, admin, category):
        res = auth_client(client, admin).post('/api/products/', {
            'name':         'Produit admin',
            'price':        5.00,
            'weight':       100,
            'stock':        10,
            'category_ids': [category.category_id],
        })
        assert res.status_code == status.HTTP_201_CREATED

    def test_suppression_produit_user_normal_interdit(self, client, user, product):
        res = auth_client(client, user).delete(f'/api/products/{product.product_id}/')
        assert res.status_code == status.HTTP_403_FORBIDDEN


# ──────────────────────────────────────────────
# COMMANDES
# ──────────────────────────────────────────────

class TestOrders:
    def test_commandes_non_authentifie(self, client):
        res = client.get('/api/orders/')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_ne_voit_pas_commandes_autres(self, client, db):
        u1 = User.objects.create_user(
            email='u1@test.com', password='Motdepasse123!'
        )
        u2 = User.objects.create_user(
            email='u2@test.com', password='Motdepasse123!'
        )

        from .models import Order
        Order.objects.create(reference='REF-001', user=u1)

        res = auth_client(client, u2).get('/api/orders/')
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) == 0


# ──────────────────────────────────────────────
# LOGOUT
# ──────────────────────────────────────────────

class TestLogout:
    def test_logout_ok(self, client, user):
        res = client.post('/api/auth/login/', {
            'email': user.email, 'password': 'Motdepasse123!'
        })
        refresh = res.data['refresh']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}')
        res = client.post('/api/auth/logout/', {'refresh': refresh})
        assert res.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_sans_auth(self, client, db):
        res = client.post('/api/auth/logout/', {'refresh': 'nimporte'})
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_token_invalide(self, client, user):
        c = auth_client(client, user)
        res = c.post('/api/auth/logout/', {'refresh': 'tokenbidon'})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ──────────────────────────────────────────────
# MESSAGES
# ──────────────────────────────────────────────

class TestMessages:
    def test_envoyer_message_sans_auth(self, client, db):
        res = client.post('/api/messages/', {
            'firstname': 'Tom',
            'lastname':  'Dupont',
            'email':     'tom@test.com',
            'phone':     '0612345678',
            'subject':   'Test',
            'message':   'Bonjour !',
        })
        assert res.status_code == status.HTTP_201_CREATED

    def test_lire_messages_user_normal_interdit(self, client, user):
        res = auth_client(client, user).get('/api/messages/')
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_lire_messages_admin_ok(self, client, admin):
        res = auth_client(client, admin).get('/api/messages/')
        assert res.status_code == status.HTTP_200_OK

    def test_message_champs_manquants(self, client, db):
        res = client.post('/api/messages/', {
            'firstname': 'Tom',
            'message':   'Bonjour',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_message_telephone_invalide(self, client, db):
        res = client.post('/api/messages/', {
            'firstname': 'Tom',
            'lastname':  'Dupont',
            'email':     'tom@test.com',
            'phone':     'abc',
            'subject':   'Test',
            'message':   'Bonjour',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ──────────────────────────────────────────────
# STOCK — vérification à la commande
# ──────────────────────────────────────────────

class TestStock:
    def test_commande_stock_suffisant(self, client, user, product):
        res = auth_client(client, user).post('/api/orders/', {
            'reference': 'REF-STOCK-OK',
            'items': [
                {'product_id': product.product_id, 'quantity': 2}
            ]
        }, format='json')
        assert res.status_code == status.HTTP_201_CREATED
        product.refresh_from_db()
        assert product.stock == 8

    def test_commande_stock_insuffisant(self, client, user, product):
        res = auth_client(client, user).post('/api/orders/', {
            'reference': 'REF-STOCK-KO',
            'items': [
                {'product_id': product.product_id, 'quantity': 999}
            ]
        }, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert 'errors' in res.data