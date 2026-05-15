import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from store.models import Category, Product  # noqa: E402


def run_seed():
    print("🌱 Génération du catalogue plat...")
    print("Suppression des anciens produits et catégories...")
    Product.objects.all().delete()
    Category.objects.all().delete()
    print("✨ Base de données vidée et prête !")

    # --- DONNÉES DE BASE ---
    parfums_standards = [
        "Vanille", "Framboise", "Mure Myrtille", "Fleur de Tiaré", "Rose",
        "Bois de Santal", "Fruits Tropicaux", "Jasmin", "Barbe à papa",
        "Bubble Gum", "Noix de Coco", "Fleur de Coton", "Fruits rouge",
        "Fraise", "Pomme d'amour", "Bouquet Solaire"
    ]
    parfums_naissance = parfums_standards + ["Musty"]
    couleurs_naissance = ["Jaune", "Bleu Clair", "Bleu", "Rose Clair", "Rose", "Fushia", "Orange", "Gris",
                          "Vert Foncé", "Terracotta", "Crème", "Beige", "Rouge", "Violet"]

    # --- CATÉGORIES ---
    cat_parfumee, _ = Category.objects.get_or_create(name="Bougies Parfumées")
    cat_moulee, _   = Category.objects.get_or_create(name="Bougies Moulées")
    cat_coffret, _  = Category.objects.get_or_create(name="Coffrets")
    cat_naissance, _ = Category.objects.get_or_create(name="Naissance & Chantilly")

    compteur = 0

    def create_product(name, price_cents, weight, category, **kwargs):
        product, _ = Product.objects.update_or_create(
            name=name,
            defaults={
                "price": Decimal(price_cents) / 100,
                "weight": weight,
                **kwargs,
            }
        )
        product.categories.set([category])
        return product

    # 1. BOUGIES CONTENANTS
    tailles_contenants = [
        {"taille": "90g",  "price": 860,  "weight": 90},
        {"taille": "160g", "price": 1350, "weight": 160},
        {"taille": "230g", "price": 1660, "weight": 230},
    ]

    for taille in tailles_contenants:
        for parfum in parfums_standards:
            nom_produit = f"Bougie en contenant {taille['taille']} - {parfum}"
            create_product(
                name=nom_produit,
                price_cents=taille["price"],
                weight=taille["weight"],
                category=cat_parfumee,
                image=f"/images/bougie-{taille['taille']}.jpg",
                description=f"Bougie artisanale de {taille['taille']} au doux parfum de {parfum}."
            )
            compteur += 1

    # 2. BOUGIES MOULÉES
    modeles_moules = [
        {"nom": "Bougie moulée Spirale",              "base_price": 550, "weight": 180},
        {"nom": "Bougie moulée Petit Cube en Boules", "base_price": 120, "weight": 35},
    ]

    for modele in modeles_moules:
        create_product(
            name=f"{modele['nom']} (Sans parfum)",
            price_cents=modele["base_price"],
            weight=modele["weight"],
            category=cat_moulee,
        )
        compteur += 1

        for parfum in parfums_standards:
            create_product(
                name=f"{modele['nom']} - {parfum}",
                price_cents=modele["base_price"] + 200,
                weight=modele["weight"],
                category=cat_moulee,
            )
            compteur += 1

    # 3. BOUGIE NAISSANCE
    create_product(
        name="Bougie Naissance Personnalisable",
        price_cents=1950,
        weight=205,
        category=cat_naissance,
        customizable=True,
        options={
            "parfums_base": parfums_naissance,
            "parfums_chantilly": parfums_naissance,
            "couleurs": couleurs_naissance,
            "prenom_max_length": 7
        }
    )
    compteur += 1

    # 4. COFFRETS
    create_product(
        name="Coffret taille M (3 bougies 90g)",
        price_cents=2400,
        weight=495,
        category=cat_coffret,
    )
    compteur += 1

    print(f"🚀 Terminé ! {compteur} produits indépendants ont été générés dans ta base de données.")


if __name__ == '__main__':
    run_seed()