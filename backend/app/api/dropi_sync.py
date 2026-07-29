from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.dropi_client import authenticate, generate_permanent_token
from app.services.dropi_orders import push_order_to_dropi, sync_all_active_orders, sync_tracking_info
from app.services.dropi_products import sync_product_detail, sync_products

router = APIRouter(prefix="/api/dropi", tags=["dropi"])


@router.post("/sync-products")
async def sync_all_products(
    margin: float = Query(30.0, description="Margen de ganancia % para productos importados"),
    session: AsyncSession = Depends(get_session),
):
    created = await sync_products(session, default_margin=margin)
    return {"synced": created}


@router.post("/sync-product/{dropi_id}")
async def sync_one_product(
    dropi_id: int,
    margin: float = Query(30.0),
    session: AsyncSession = Depends(get_session),
):
    product = await sync_product_detail(session, dropi_id, margin=margin)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado en Dropi")
    return {
        "id": str(product.id),
        "name": product.name,
        "selling_price": product.selling_price,
        "margin": product.margin_percentage,
    }


@router.post("/push-order/{order_id}")
async def push_order(order_id: str, session: AsyncSession = Depends(get_session)):
    import uuid
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de orden inválido")

    dropi_id = await push_order_to_dropi(oid, session)
    if dropi_id is None:
        return {"pushed": False, "detail": "No se pudo crear la orden en Dropi (verifica que esté pagada y no duplicada)"}
    return {"pushed": True, "dropi_order_id": dropi_id}


@router.post("/sync-tracking/{order_id}")
async def sync_tracking(order_id: str, session: AsyncSession = Depends(get_session)):
    import uuid
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de orden inválido")

    updated = await sync_tracking_info(oid, session)
    return {"updated": updated}


@router.post("/sync-all-tracking")
async def sync_all_tracking(session: AsyncSession = Depends(get_session)):
    updated = await sync_all_active_orders(session)
    return {"synced": updated}


@router.get("/auth")
async def get_auth_token():
    """Generate permanent Dropi integration token from credentials."""
    if not settings.dropi_email or not settings.dropi_password:
        return {"error": "Configura DROPI_EMAIL y DROPI_PASSWORD en .env"}
    if not settings.dropi_white_brand_id:
        return {"error": "Configura DROPI_WHITE_BRAND_ID en .env"}

    from app.config import settings

    temp_token = await authenticate()
    if not temp_token:
        return {"error": "Falló autenticación con Dropi"}

    permanent = await generate_permanent_token(temp_token)
    return {
        "permanent_token": permanent,
        "detail": "Copia este token en DROPI_INTEGRATION_TOKEN en .env",
    }
