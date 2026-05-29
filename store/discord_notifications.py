import requests
import os
import logging

logger = logging.getLogger(__name__)

WEBHOOK_COMMANDES = os.getenv('DISCORD_WEBHOOK_COMMANDES')
WEBHOOK_STOCK     = os.getenv('DISCORD_WEBHOOK_STOCK')
WEBHOOK_MESSAGES  = os.getenv('DISCORD_WEBHOOK_MESSAGES')

STOCK_SEUIL = 5


def send_discord(webhook_url, payload):
    """Envoie un message Discord via webhook."""
    if not webhook_url:
        logger.warning("Webhook Discord non configuré.")
        return
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Erreur webhook Discord : {e}")


def notify_nouvelle_commande(order, details):
    """Notifie Discord d'une nouvelle commande."""
    lignes = "\n".join(
        f"• {d.name} x{d.quantity} — {d.total}€"
        for d in details
    )
    total = sum(d.total for d in details)
    payload = {
        "embeds": [{
            "title": "🛒 Nouvelle commande !",
            "color": 0x2ECC71,
            "fields": [
                {"name": "Référence", "value": order.reference, "inline": True},
                {"name": "Client",    "value": str(order.user.email), "inline": True},
                {"name": "Total",     "value": f"{total}€", "inline": True},
                {"name": "Produits",  "value": lignes or "—", "inline": False},
            ],
        }]
    }
    send_discord(WEBHOOK_COMMANDES, payload)


def notify_stock_faible(product):
    """Notifie Discord quand le stock d'un produit passe sous le seuil."""
    if product.stock <= STOCK_SEUIL:
        payload = {
            "embeds": [{
                "title": "⚠️ Stock faible !",
                "color": 0xE74C3C,
                "fields": [
                    {"name": "Produit", "value": product.name, "inline": True},
                    {"name": "Stock restant", "value": str(product.stock), "inline": True},
                ],
                "footer": {"text": "Pensez à réapprovisionner !"}
            }]
        }
        send_discord(WEBHOOK_STOCK, payload)


def notify_nouveau_message(message):
    """Notifie Discord d'un nouveau message de contact."""
    payload = {
        "embeds": [{
            "title": "✉️ Nouveau message de contact !",
            "color": 0x3498DB,
            "fields": [
                {"name": "De",      "value": f"{message.firstname} {message.lastname}", "inline": True},
                {"name": "Email",   "value": message.email, "inline": True},
                {"name": "Sujet",   "value": message.subject, "inline": False},
                {"name": "Message", "value": message.message[:500], "inline": False},
            ],
        }]
    }
    send_discord(WEBHOOK_MESSAGES, payload)