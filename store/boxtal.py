import base64
import os
import requests
import logging

logger = logging.getLogger(__name__)

BOXTAL_ACCESS_KEY  = os.getenv('BOXTAL_ACCESS_KEY')
BOXTAL_SECRET_KEY  = os.getenv('BOXTAL_SECRET_KEY')
BOXTAL_ENV         = os.getenv('BOXTAL_ENV', 'sandbox')

BASE_URL = (
    'https://api.boxtal.com'
    if BOXTAL_ENV == 'production'
    else 'https://api.boxtal.build/shipping'
)


def get_auth_header():
    credentials = base64.b64encode(
        f"{BOXTAL_ACCESS_KEY}:{BOXTAL_SECRET_KEY}".encode()
    ).decode()
    return {'Authorization': f'Basic {credentials}', 'Content-Type': 'application/json'}


def create_shipping_order(order, sender, recipient, shipping_offer_code):
    """Crée une étiquette d'expédition via Boxtal API V3."""
    payload = {
        "shippingOfferCode": shipping_offer_code,
        "shipment": {
            "fromAddress": sender,
            "toAddress": recipient,
            "returnAddress": sender,
            "packages": [{"weight": {"value": 1, "unit": "kg"}}],
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v3.1/shipping-order",
            json=payload,
            headers=get_auth_header(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur Boxtal : {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Détail Boxtal : {e.response.text}")
        return None