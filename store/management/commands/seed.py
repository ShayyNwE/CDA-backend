from django.core.management.base import BaseCommand
from store.models import Category, Product


class Command(BaseCommand):
    help = "Seed complet du catalogue"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seed catalogue en cours...")

        # --- DONNÉES ---
        parfums_standards = [
            "Vanille", "Framboise", "Mure Myrtille", "Fleur de Tiaré", "Rose",
            "Bois de Santal", "Fruits Tropicaux", "Jasmin", "Barbe à papa",
            "Bubble Gum", "Noix de Coco", "Fleur de Coton", "Fruits rouge",
            "Fraise", "Pomme d’amour", "Bouquet Solaire"
        ]

        parfums_naissance = parfums_standards + ["Musty"]

        couleurs_naissance = [
            "Jaune", "Bleu Clair", "Bleu", "Rose Clair", "Rose", "Fushia",
            "Orange", "Gris", "Vert Foncé", "Terracotta", "Crème",
            "Beige", "Rouge", "Violet"
        ]

        # --- CATÉGORIES ---
        categories = {}
        for name in [
            "Bougies Parfumées",
            "Bougies Moulées",
            "Coffrets",
            "Naissance & Chantilly"
        ]:
            cat, _ = Category.objects.get_or_create(name=name)
            categories[name] = cat

        compteur = 0

        # =========================================================
        # 1. BOUGIES CONTENANTS
        # =========================================================
        tailles = [
            {"taille": "90g", "price": 860, "weight": 90},
            {"taille": "160g", "price": 1350, "weight": 160},
            {"taille": "230g", "price": 1660, "weight": 230},
        ]

        for t in tailles:
            for parfum in parfums_standards:
                name = f"Bougie {t['taille']} - {parfum}"

                Product.objects.update_or_create(
                    name=name,
                    defaults={
                        "price": t["price"],
                        "weight": t["weight"],
                        "category": categories["Bougies Parfumées"],
                        "image": f"/images/bougie-{t['taille']}.jpg",
                        "description": f"Bougie artisanale {t['taille']} parfum {parfum}",
                    }
                )
                compteur += 1

        # =========================================================
        # 2. BOUGIES MOULÉES
        # =========================================================
        modeles = [
            {"nom": "Bougie Spirale", "base_price": 550, "weight": 180},
            {"nom": "Petit Cube", "base_price": 120, "weight": 35},
        ]

        for m in modeles:
            # Sans parfum
            Product.objects.update_or_create(
                name=f"{m['nom']} (Sans parfum)",
                defaults={
                    "price": m["base_price"],
                    "weight": m["weight"],
                    "category": categories["Bougies Moulées"],
                }
            )
            compteur += 1

            # Avec parfum
            for parfum in parfums_standards:
                Product.objects.update_or_create(
                    name=f"{m['nom']} - {parfum}",
                    defaults={
                        "price": m["base_price"] + 200,
                        "weight": m["weight"],
                        "category": categories["Bougies Moulées"],
                    }
                )
                compteur += 1

        # =========================================================
        # 3. BOUGIE NAISSANCE (JSON)
        # =========================================================
        Product.objects.update_or_create(
            name="Bougie Naissance Personnalisable",
            defaults={
                "price": 1950,
                "weight": 205,
                "category": categories["Naissance & Chantilly"],
                "is_customizable": 1,
                "customization_options": {
                    "parfums_base": parfums_naissance,
                    "parfums_chantilly": parfums_naissance,
                    "couleurs": couleurs_naissance,
                    "prenom_max_length": 7
                }
            }
        )
        compteur += 1

        # =========================================================
        # 4. COFFRETS
        # =========================================================
        Product.objects.update_or_create(
            name="Coffret M (3x90g)",
            defaults={
                "price": 2400,
                "weight": 495,
                "category": categories["Coffrets"]
            }
        )
        compteur += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed terminé : {compteur} produits générés"
        ))