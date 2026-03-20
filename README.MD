# 🕯️ BackEnd

BackEnd pour une application e-commerce

---

## Stack technique

| Couche | Technologie |
|---|---|
| Back-end | Django, Django REST Framework |
| Base de données | PostgreSQL |
| Authentification | JWT (djangorestframework-simplejwt) |
| CORS | django-cors-headers |

---

## Prérequis

- Python 3.13+
- PostgreSQL 18
- Git

---

## Installation du back-end

### 1. Cloner le projet

```bash
git clone https://github.com/TON_USERNAME/ecommerce-bougie.git
cd ecommerce-bougie
```

### 2. Installer les dépendances Python

```bash
pip install django djangorestframework djangorestframework-simplejwt psycopg2-binary django-cors-headers
```

### 3. Configurer PostgreSQL

Se connecter à PostgreSQL et créer la base de données :

```bash
psql -U postgres
```

```sql
CREATE DATABASE bougie_db;
CREATE USER bougie_user WITH PASSWORD 'ton_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE bougie_db TO bougie_user;
GRANT ALL ON SCHEMA public TO bougie_user;
ALTER DATABASE bougie_db OWNER TO bougie_user;
\q
```

### 4. Configurer les variables d'environnement

Modifier les identifiants de base de données dans `backend/settings.py` :

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "bougie_db",
        "USER": "bougie_user",
        "PASSWORD": "ton_mot_de_passe",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

### 5. Appliquer les migrations

```bash
cd backend
python manage.py migrate
```

### 6. Créer un superutilisateur (accès admin)

```bash
python manage.py createsuperuser
```

### 7. Lancer le serveur

```bash
python manage.py runserver
```

Le back-end est accessible sur **http://localhost:8000**

---

## Structure du projet

```
backend/
├── manage.py
├── backend/
│   ├── settings.py        # Configuration Django
│   ├── urls.py            # URLs principales
│   └── wsgi.py
└── store/
    ├── models.py          # Modèles de la base de données
    ├── serializers.py     # Sérialisation des données
    ├── views.py           # Logique des endpoints
    ├── urls.py            # URLs de l'API
    └── admin.py           # Interface d'administration
```

---

## Base de données

Le projet contient 5 tables :

| Table | Description |
|---|---|
| `users` | Utilisateurs avec authentification par email |
| `category` | Catégories de produits |
| `product` | Produits (bougies) avec prix, image, personnalisation |
| `orders` | Commandes avec intégration Stripe |
| `order_details` | Détail des produits dans chaque commande |

> Les prix sont stockés en **centimes** (ex: 12,50 € = `1250`) pour éviter les erreurs d'arrondi avec Stripe.

---

## Endpoints API

### Authentification

| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/auth/register/` | Créer un compte | Public |
| POST | `/api/auth/login/` | Se connecter, reçoit access + refresh token | Public |
| POST | `/api/auth/refresh/` | Rafraîchir le token d'accès | Public |
| GET/PUT | `/api/auth/profile/` | Voir ou modifier son profil | Authentifié |

### Produits & Catégories

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/categories/` | Liste des catégories | Public |
| POST | `/api/categories/` | Créer une catégorie | Authentifié |
| GET | `/api/products/` | Liste des produits | Public |
| POST | `/api/products/` | Créer un produit | Authentifié |
| GET | `/api/products/:id/` | Détail d'un produit | Public |
| PUT/DELETE | `/api/products/:id/` | Modifier ou supprimer un produit | Authentifié |

### Commandes

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/orders/` | Mes commandes | Authentifié |
| POST | `/api/orders/` | Créer une commande | Authentifié |
| GET | `/api/orders/:id/` | Détail d'une commande | Authentifié |

---

## Authentification JWT

Après le login, tu reçois deux tokens :

```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

- **access token** — valable 30 minutes, à envoyer dans chaque requête
- **refresh token** — valable 7 jours, permet d'obtenir un nouveau access token

Pour les requêtes authentifiées, ajouter le header :

```
Authorization: Bearer <access_token>
```

---

## Interface d'administration

Accessible sur **http://localhost:8000/admin** avec les identifiants du superutilisateur.

Permet de gérer directement : utilisateurs, catégories, produits, commandes.

---

## Ajouter PostgreSQL au PATH (Windows)

Si `psql` n'est pas reconnu dans le terminal :

```powershell
$env:PATH += ";C:\Program Files\PostgreSQL\18\bin"
```