import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from store.models import Category, Product

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
        "Fraise", "Pomme d’amour", "Bouquet Solaire"
    ]
    parfums_naissance = parfums_standards + ["Musty"]
    couleurs_naissance = ["Jaune", "Bleu Clair", "Bleu", "Rose Clair", "Rose", "Fushia", "Orange", "Gris", 
                          "Vert Foncé", "Terracotta", "Crème", "Beige", "Rouge", "Violet"]

    # --- CATÉGORIES ---
    cat_parfumee, _ = Category.objects.get_or_create(name="Bougies Parfumées")
    cat_moulee, _ = Category.objects.get_or_create(name="Bougies Moulées")
    cat_coffret, _ = Category.objects.get_or_create(name="Coffrets")
    cat_naissance, _ = Category.objects.get_or_create(name="Naissance & Chantilly")

    compteur = 0

    # 1. BOUGIES CONTENANTS (1 Produit = 1 Taille + 1 Parfum)
    tailles_contenants = [
        {"taille": "90g", "price": 860, "weight": 90},
        {"taille": "160g", "price": 1350, "weight": 160},
        {"taille": "230g", "price": 1660, "weight": 230},
    ]

    for taille in tailles_contenants:
        for parfum in parfums_standards:
            nom_produit = f"Bougie en contenant {taille['taille']} - {parfum}"
            Product.objects.update_or_create(
                name=nom_produit,
                defaults={
                    "price": taille["price"],
                    "weight": taille["weight"],
                    "category": cat_parfumee,
                    "image": f"/images/bougie-{taille['taille']}.jpg",
                    "description": f"Bougie artisanale de {taille['taille']} au doux parfum de {parfum}."
                }
            )
            compteur += 1

    # 2. BOUGIES MOULÉES (Sans parfum + 1 Produit par parfum avec surcoût)
    modeles_moules = [
        {"nom": "Bougie moulée Spirale", "base_price": 550, "weight": 180},
        {"nom": "Bougie moulée Petit Cube en Boules", "base_price": 120, "weight": 35},
    ]

    for modele in modeles_moules:
        # Version sans parfum
        Product.objects.update_or_create(
            name=f"{modele['nom']} (Sans parfum)",
            defaults={"price": modele["base_price"], "weight": modele["weight"], "category": cat_moulee}
        )
        compteur += 1

        # Versions avec parfum (+2€ = 200 centimes)
        for parfum in parfums_standards:
            Product.objects.update_or_create(
                name=f"{modele['nom']} - {parfum}",
                defaults={
                    "price": modele["base_price"] + 200, 
                    "weight": modele["weight"], 
                    "category": cat_moulee
                }
            )
            compteur += 1

    # 3. BOUGIE NAISSANCE (Reste en 1 seul produit avec options JSON)
    Product.objects.update_or_create(
        name="Bougie Naissance Personnalisable",
        defaults={
            "price": 1950, "weight": 205, "category": cat_naissance, "is_customizable": 1,
            "customization_options": {
                "parfums_base": parfums_naissance,
                "parfums_chantilly": parfums_naissance,
                "couleurs": couleurs_naissance,
                "prenom_max_length": 7
            }
        }
    )
    compteur += 1

    # 4. COFFRETS (Idem, on garde ça simple)
    Product.objects.update_or_create(name="Coffret taille M (3 bougies 90g)", 
                                     defaults={"price": 2400, "weight": 495, "category": cat_coffret})
    compteur += 1

    print(f"🚀 Terminé ! {compteur} produits indépendants ont été générés dans ta base de données.")


if __name__ == '__main__':
    run_seed()