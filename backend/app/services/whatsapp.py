import logging

from app.config import settings

logger = logging.getLogger("dropstore.whatsapp")


async def send_whatsapp_message(to: str, message: str) -> bool:
    phone_id = settings.whatsapp_phone_id
    token = settings.whatsapp_token

    if not phone_id or not token:
        logger.warning("WhatsApp no configurado. Mensaje no enviado a %s", to)
        return False

    import httpx

    url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code == 200:
                logger.info("WhatsApp enviado a %s", to)
                return True
            logger.error("WhatsApp error: %s %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.error("WhatsApp exception: %s", e)
        return False


async def send_order_notification(to: str, customer_name: str, order_id: str, total: float) -> bool:
    msg = (
        f"🛒 *DropStore - Confirmación de pedido*\n\n"
        f"Hola {customer_name}, hemos recibido tu pago correctamente.\n"
        f"Pedido: {order_id[:8]}...\n"
        f"Total: S/ {total:.2f}\n\n"
        f"Te notificaremos cuando esté en camino."
    )
    return await send_whatsapp_message(to, msg)


async def send_tracking_notification(to: str, customer_name: str, tracking: str) -> bool:
    msg = (
        f"📦 *DropStore - Tu pedido está en camino*\n\n"
        f"Hola {customer_name}, tu pedido ha sido despachado.\n"
        f"Número de seguimiento: {tracking}\n\n"
        f"¡Gracias por comprar en DropStore!"
    )
    return await send_whatsapp_message(to, msg)
