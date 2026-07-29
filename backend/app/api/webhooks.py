from __future__ import annotations
import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_session
from app.models import Customer, Order
from app.services.dropi_orders import push_order_to_dropi
from app.services.notifications import notify_payment_confirmed

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def verify_mp_signature(request: Request, payload: bytes) -> bool:
    x_sign = request.headers.get("x-signature", "")
    if not x_sign or not settings.meli_webhook_secret:
        return False

    parts = {}
    for part in x_sign.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            parts[k.strip()] = v.strip()

    ts = parts.get("ts", "")
    hash_val = parts.get("v1", "")
    if not ts or not hash_val:
        return False

    expected = hmac.new(
        settings.meli_webhook_secret.encode(),
        f"id:{payload.decode()}ts:{ts}".encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(hash_val, expected)


@router.post("/mercadopago")
async def mercadopago_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    payload = await request.body()
    data = await request.json()

    action = data.get("action") or data.get("type", "")
    payment_id = None

    if "data" in data and "id" in data["data"]:
        payment_id = data["data"]["id"]

    if action == "payment.created" or action == "payment.updated":
        import httpx

        async with httpx.AsyncClient() as client:
            mp_resp = await client.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {settings.meli_access_token}"},
            )
            if mp_resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Error consultando pago en MP")

            payment = mp_resp.json()
            external_ref = payment.get("external_reference", "")
            status = payment.get("status", "")

            if external_ref:
                result = await session.execute(
                    select(Order).where(Order.id == external_ref).options(
                        selectinload(Order.items), selectinload(Order.customer)
                    )
                )
                order = result.scalar_one_or_none()
                if order:
                    order.payment_status = status
                    order.payment_id = str(payment.get("id", ""))
                    order.payment_method = payment.get("payment_method_id", "")

                    if status == "approved":
                        order.status = "paid"
                        await session.commit()
                        await session.refresh(order)
                        await notify_payment_confirmed(order)
                        await push_order_to_dropi(order.id, session)
                    elif status in ("cancelled", "rejected", "refunded"):
                        order.status = "cancelled"
                        await session.commit()
                    else:
                        await session.commit()

    return {"received": True}
