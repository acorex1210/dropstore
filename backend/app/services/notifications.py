import logging

from app.models import Order
from app.services.email import send_dispatch_notification, send_order_confirmation

logger = logging.getLogger("dropstore.notifications")


async def notify_payment_confirmed(order: Order) -> None:
    customer = order.customer
    if not customer:
        logger.warning("Orden %s sin customer, no se envía notificación", order.id)
        return

    items_data = [
        {"name": item.product_name, "quantity": item.quantity, "price": item.unit_price}
        for item in order.items
    ]

    email_sent = send_order_confirmation(
        to=customer.email,
        customer_name=customer.full_name,
        items=items_data,
        total=order.total_amount,
        address=order.shipping_address,
        city=order.shipping_city,
        department=order.shipping_department,
        country=order.shipping_country,
    )

    whatsapp_to = customer.phone
    if whatsapp_to:
        from app.services.whatsapp import send_order_notification
        await send_order_notification(
            to=whatsapp_to,
            customer_name=customer.full_name,
            order_id=str(order.id),
            total=order.total_amount,
        )

    if email_sent:
        logger.info("Notificación enviada para orden %s", order.id)


async def notify_order_dispatched(order: Order) -> None:
    customer = order.customer
    if not customer or not order.tracking_number:
        return

    items_data = [
        {"name": item.product_name, "quantity": item.quantity, "price": item.unit_price}
        for item in order.items
    ]

    email_sent = send_dispatch_notification(
        to=customer.email,
        customer_name=customer.full_name,
        tracking=order.tracking_number,
        tracking_url=order.tracking_url,
        items=items_data,
    )

    whatsapp_to = customer.phone
    if whatsapp_to and order.tracking_number:
        from app.services.whatsapp import send_tracking_notification
        await send_tracking_notification(
            to=whatsapp_to,
            customer_name=customer.full_name,
            tracking=order.tracking_number,
        )

    if email_sent:
        logger.info("Notificación de despacho enviada para orden %s", order.id)
