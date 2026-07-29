from __future__ import annotations
from typing import Optional
import uuid

import mercadopago

from app.config import settings

_sdk: mercadopago.SDK | None = None


def get_sdk() -> mercadopago.SDK:
    global _sdk
    if _sdk is None and settings.meli_access_token:
        _sdk = mercadopago.SDK(settings.meli_access_token)
    return _sdk


def create_preference(
    order_id: uuid.UUID,
    items: list[dict],
    payer_email: str,
    success_url: str,
    failure_url: str,
    pending_url: str,
    notification_url: str,
) -> Optional[dict]:
    sdk = get_sdk()
    if not sdk:
        return None

    preference_data = {
        "items": [
            {
                "id": str(item.get("product_id", "")),
                "title": item["title"],
                "quantity": item["quantity"],
                "unit_price": float(item["unit_price"]),
                "currency_id": "PEN",
            }
            for item in items
        ],
        "payer": {"email": payer_email},
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "auto_return": "approved",
        "notification_url": notification_url,
        "external_reference": str(order_id),
    }

    result = sdk.preference().create(preference_data)
    if result.get("status", 400) in (200, 201):
        return result.get("response")
    return None
