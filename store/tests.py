from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Category


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@bougie.com',
            'password': 'motdepasse123',  # nosec
            'firstname': 'Jean',
            'lastname': 'Dupont'
        }

    def test_register(self):
        response = self.client.post('/api/auth/register/', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login(self):
        User.objects.create_user(**self.user_data)
        response = self.client.post('/api/auth/login/', {
            'email': 'test@bougie.com',
            'password': 'motdepasse123'  # nosec
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class ProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Bougies parfumées')

    def test_liste_produits(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_liste_categories(self):
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)