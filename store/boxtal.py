import base64
import os
import requests
import logging
import json

logger = logging.getLogger(__name__)

BOXTAL_ACCESS_KEY = os.getenv("BOXTAL_ACCESS_KEY")
BOXTAL_SECRET_KEY = os.getenv("BOXTAL_SECRET_KEY")
BOXTAL_ENV = os.getenv("BOXTAL_ENV", "sandbox")

BASE_URL = (
    "https://api.boxtal.com"
    if BOXTAL_ENV == "production"
    else "https://api.boxtal.build/shipping"
)


def get_auth_header():
    credentials = base64.b64encode(
        f"{BOXTAL_ACCESS_KEY}:{BOXTAL_SECRET_KEY}".encode()
    ).decode()

    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }


def create_shipping_order(order, sender, recipient, shipping_offer_code):
    """
    Création d'une expédition Boxtal V3.1
    """

    if not shipping_offer_code:
        raise ValueError("shipping_offer_code manquant")

    def normalize_address(addr: dict):
        return {
            "firstName": addr.get("firstName"),
            "lastName": addr.get("lastName"),
            "email": addr.get("email"),
            "phone": addr.get("phone"),
            "street": addr.get("address") or addr.get("street"),
            "city": addr.get("city"),
            "zipCode": addr.get("zipCode"),
            "country": addr.get("country", "FR"),
        }

    payload = {
        "shippingOfferCode": shipping_offer_code,
        "shipment": {
            "fromAddress": normalize_address(sender),
            "toAddress": normalize_address(recipient),
            "returnAddress": normalize_address(sender),
            "packages": [
                {
                    "weight": {"value": 1, "unit": "kg"}
                }
            ],
        },
    }

    logger.error("📦 Payload Boxtal envoyé:\n%s", json.dumps(payload, indent=2))

    try:
        response = requests.post(
            f"{BASE_URL}/v3.1/shipping-order",
            json=payload,
            headers=get_auth_header(),
            timeout=15,
        )

        logger.error("📨 Status Boxtal: %s", response.status_code)
        logger.error("📨 Response Boxtal: %s", response.text)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur Boxtal: {e}")

        if hasattr(e, "response") and e.response is not None:
            logger.error(f"❌ Détail Boxtal: {e.response.text}")

        return None