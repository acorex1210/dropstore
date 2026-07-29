from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Customer, Order, OrderItem, Product
from app.schemas.order import CheckoutRequest, ConfirmDispatch, OrderOut, PreferenceOut
from app.services.margin import calc_selling_price
from app.services.mercadopago import create_preference
from app.services.notifications import notify_order_dispatched

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


@router.post("/create-preference", response_model=PreferenceOut)
async def create_checkout_preference(data: CheckoutRequest, session: AsyncSession = Depends(get_session)):
    if not data.items:
        raise HTTPException(status_code=400, detail="Carrito vacío")

    product_ids = []
    for item in data.items:
        product_ids.append(uuid.UUID(item.product_id))

    result = await session.execute(
        select(Product).where(Product.id.in_(product_ids), Product.is_active == True)
    )
    products = {str(p.id): p for p in result.scalars().all()}

    order_items_data = []
    preference_items = []
    subtotal = 0.0
    total_cost = 0.0

    for cart_item in data.items:
        pid = cart_item.product_id
        product = products.get(pid)
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto {pid} no encontrado")

        qty = cart_item.quantity
        unit_selling = product.selling_price
        unit_cost = product.base_price
        line_total = round(unit_selling * qty, 2)
        line_cost = round(unit_cost * qty, 2)
        line_margin = round(line_total - line_cost, 2)

        order_items_data.append({
            "product_id": product.id,
            "product_name": product.name,
            "quantity": qty,
            "unit_price": unit_selling,
            "unit_cost": unit_cost,
            "subtotal": line_total,
            "margin": line_margin,
        })

        preference_items.append({
            "product_id": str(product.id),
            "title": product.name,
            "quantity": qty,
            "unit_price": unit_selling,
        })

        subtotal += line_total
        total_cost += line_cost

    subtotal = round(subtotal, 2)
    total_cost = round(total_cost, 2)
    total_margin = round(subtotal - total_cost, 2)

    order_id = uuid.uuid4()

    preference = create_preference(
        order_id=order_id,
        items=preference_items,
        payer_email=data.email,
        success_url="http://localhost:3000/success",
        failure_url="http://localhost:3000/failure",
        pending_url="http://localhost:3000/pending",
        notification_url="https://YOUR_NGROK_URL.ngrok.app/api/webhooks/mercadopago",
    )

    if not preference:
        raise HTTPException(status_code=500, detail="Error al crear preferencia de pago")

    customer = Customer(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        address=data.address,
        city=data.city,
        department=data.department,
        country=data.country,
        notes=data.notes,
    )
    session.add(customer)
    await session.flush()

    order = Order(
        id=order_id,
        customer_id=customer.id,
        status="pending",
        subtotal=subtotal,
        shipping_cost=0,
        total_amount=subtotal,
        total_cost=total_cost,
        total_margin=total_margin,
        payment_id=preference.get("id"),
        payment_status="pending",
        shipping_address=data.address,
        shipping_city=data.city,
        shipping_department=data.department,
        shipping_country=data.country,
    )
    session.add(order)
    await session.flush()

    for item_data in order_items_data:
        order_item = OrderItem(order_id=order.id, **item_data)
        session.add(order_item)

    await session.commit()

    return PreferenceOut(
        preference_id=preference["id"],
        init_point=preference["init_point"],
        order_id=str(order.id),
        total=subtotal,
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return order


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Order).order_by(Order.created_at.desc()).options(selectinload(Order.items))
    )
    return result.scalars().all()


@router.post("/dispatch/{order_id}", response_model=OrderOut)
async def confirm_dispatch(
    order_id: uuid.UUID,
    data: ConfirmDispatch,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(
            selectinload(Order.items), selectinload(Order.customer)
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    had_tracking_before = bool(order.tracking_number)

    order.provider_order_id = data.provider_order_id
    order.status = "processing"
    if data.tracking_number:
        order.tracking_number = data.tracking_number
    if data.tracking_url:
        order.tracking_url = data.tracking_url

    await session.commit()
    await session.refresh(order)

    if data.tracking_number and not had_tracking_before:
        await notify_order_dispatched(order)

    return order
