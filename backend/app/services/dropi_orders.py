import uuid
from typing import Optional,  Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order, OrderItem, Product
from app.services.dropi_client import create_order as dropi_create_order
from app.services.dropi_client import get_order_by_shop_id, get_order_by_guide


def _build_dropi_payload(order: Order, items: list[OrderItem], products: dict[uuid.UUID, Product]) -> dict[str, Any]:
    """Build the Dropi API order payload from our internal order."""
    customer = order.customer

    products_payload = []
    total_cents = 0

    for item in items:
        product = products.get(item.product_id)
        dropi_id = int(product.provider_id) if product and product.provider_id else 0

        price_cents = int(item.unit_price * 100)
        qty = item.quantity
        total_cents += price_cents * qty

        variant_id = None
        if item.variant_name and product:
            for v in product.variants:
                if v.name == item.variant_name and v.sku:
                    variant_id = int(v.sku)
                    break

        products_payload.append({
            "id": dropi_id,
            "price": price_cents,
            "quantity": qty,
            "variation_id": variant_id,
        })

    return {
        "calculate_costs_and_shiping": True,
        "state": (order.shipping_department or "").upper(),
        "city": order.shipping_city.upper(),
        "name": customer.full_name.split(" ")[0] if customer.full_name else "",
        "surname": " ".join(customer.full_name.split(" ")[1:]) if " " in customer.full_name else customer.full_name,
        "dir": order.shipping_address,
        "client_email": customer.email,
        "notes": customer.notes or "",
        "payment_method_id": 1,
        "phone": customer.phone or "",
        "rate_type": "SIN RECAUDO",
        "type": "FINAL_ORDER",
        "total_order": total_cents,
        "products": products_payload,
        "shop_order_id": str(order.id),
    }


async def push_order_to_dropi(order_id: uuid.UUID, session: AsyncSession) -> Optional[str]:
    """Push a paid order to Dropi. Returns Dropi order ID or None on failure."""
    result = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.customer))
    )
    order = result.scalar_one_or_none()
    if not order:
        return None

    # Only push paid orders that haven't been pushed yet
    if order.status != "paid" or order.provider_order_id:
        return None

    item_product_ids = [item.product_id for item in order.items if item.product_id]
    products_map: dict[uuid.UUID, Product] = {}
    if item_product_ids:
        prod_result = await session.execute(
            select(Product).where(Product.id.in_(item_product_ids))
        )
        for p in prod_result.scalars().all():
            products_map[p.id] = p

    payload = _build_dropi_payload(order, order.items, products_map)

    try:
        resp = await dropi_create_order(payload)
        resp_data = resp if isinstance(resp, dict) else {}
        dropi_order_id = resp_data.get("data", {}).get("id") if isinstance(resp_data.get("data"), dict) else resp_data.get("id")

        if dropi_order_id:
            order.provider_order_id = str(dropi_order_id)
            order.status = "processing"
            await session.commit()
            return str(dropi_order_id)
        else:
            order.status = "paid"
            await session.commit()
            return None

    except Exception as e:
        order.status = "paid"
        order.notes = (order.notes or "") + f" [Dropi error: {e}]"
        await session.commit()
        return None


async def sync_tracking_info(order_id: uuid.UUID, session: AsyncSession) -> bool:
    """Fetch latest tracking from Dropi and update order. Returns True if updated."""
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order or not order.provider_order_id:
        return False

    try:
        resp = await get_order_by_shop_id(str(order.id))
        if not resp or not isinstance(resp, dict):
            return False

        guide = resp.get("guide", resp.get("tracking", resp.get("guia", "")))
        status_dropi = resp.get("status", "")

        if guide and guide != order.tracking_number:
            order.tracking_number = str(guide)
            if not order.tracking_url:
                order.tracking_url = f"https://www.dropi.co/tracking/{guide}"

        if status_dropi:
            status_lower = status_dropi.lower()
            if "entregado" in status_lower or "delivered" in status_lower:
                order.status = "delivered"
            elif "enviado" in status_lower or "shipped" in status_lower or "despachado" in status_lower:
                if order.status not in ("delivered",):
                    order.status = "shipped"

        await session.commit()
        return True

    except Exception:
        return False


async def sync_all_active_orders(session: AsyncSession) -> int:
    """Sync tracking for all orders in processing/shipped status. Returns count updated."""
    result = await session.execute(
        select(Order).where(
            Order.status.in_(["processing", "shipped"]),
            Order.provider_order_id.isnot(None),
        )
    )
    updated = 0
    for order in result.scalars().all():
        if await sync_tracking_info(order.id, session):
            updated += 1
    return updated
