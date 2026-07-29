import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import settings

logger = logging.getLogger("dropstore.email")


_CONFIRMATION_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #16a34a; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
    <h1 style="margin: 0;">¡Gracias por tu compra!</h1>
  </div>
  <div style="border: 1px solid #e5e7eb; border-top: none; padding: 20px; border-radius: 0 0 10px 10px;">
    <p>Hola <strong>{customer_name}</strong>,</p>
    <p>Hemos recibido tu pago correctamente. Estamos procesando tu pedido y pronto lo enviaremos.</p>

    <h3 style="color: #374151;">Resumen de tu pedido</h3>
    <table style="width: 100%%; border-collapse: collapse; font-size: 14px;">
      <thead>
        <tr style="background: #f9fafb;">
          <th style="text-align: left; padding: 8px; border-bottom: 1px solid #e5e7eb;">Producto</th>
          <th style="text-align: center; padding: 8px; border-bottom: 1px solid #e5e7eb;">Cant.</th>
          <th style="text-align: right; padding: 8px; border-bottom: 1px solid #e5e7eb;">Precio</th>
        </tr>
      </thead>
      <tbody>
        {items_html}
      </tbody>
      <tfoot>
        <tr>
          <td colspan="2" style="text-align: right; padding: 8px; font-weight: bold;">Total:</td>
          <td style="text-align: right; padding: 8px; font-weight: bold; color: #16a34a;">S/ {total}</td>
        </tr>
      </tfoot>
    </table>

    <h3 style="color: #374151; margin-top: 20px;">Dirección de envío</h3>
    <p style="color: #6b7280; font-size: 14px;">
      {address}<br>
      {city}, {department}<br>
      {country}
    </p>

    <p style="color: #6b7280; font-size: 13px; margin-top: 20px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
      Te enviaremos otro correo con el número de seguimiento cuando tu pedido sea despachado.
    </p>
  </div>
</body>
</html>"""

_DISPATCHED_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #2563eb; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
    <h1 style="margin: 0;">¡Tu pedido está en camino!</h1>
  </div>
  <div style="border: 1px solid #e5e7eb; border-top: none; padding: 20px; border-radius: 0 0 10px 10px;">
    <p>Hola <strong>{customer_name}</strong>,</p>
    <p>Tu pedido ha sido despachado y está en camino a tu dirección.</p>

    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 15px; margin: 15px 0;">
      <p style="margin: 0; font-size: 13px; color: #6b7280;">Número de seguimiento:</p>
      <p style="margin: 5px 0 0; font-size: 18px; font-weight: bold; color: #16a34a;">{tracking}</p>
      {tracking_link}
    </div>

    <h3 style="color: #374151;">Resumen del pedido</h3>
    <table style="width: 100%%; border-collapse: collapse; font-size: 14px;">
      <thead>
        <tr style="background: #f9fafb;">
          <th style="text-align: left; padding: 8px; border-bottom: 1px solid #e5e7eb;">Producto</th>
          <th style="text-align: center; padding: 8px; border-bottom: 1px solid #e5e7eb;">Cant.</th>
          <th style="text-align: right; padding: 8px; border-bottom: 1px solid #e5e7eb;">Precio</th>
        </tr>
      </thead>
      <tbody>
        {items_html}
      </tbody>
    </table>

    <p style="color: #6b7280; font-size: 12px; margin-top: 20px; text-align: center;">
      Si tienes alguna duda, responde a este correo.
    </p>
  </div>
</body>
</html>"""


def _item_row(name: str, qty: int, price: float) -> str:
    return f"""\
        <tr>
          <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{name}</td>
          <td style="text-align: center; padding: 8px; border-bottom: 1px solid #e5e7eb;">{qty}</td>
          <td style="text-align: right; padding: 8px; border-bottom: 1px solid #e5e7eb;">S/ {price:.2f}</td>
        </tr>"""


def send_email(to: str, subject: str, html: str) -> bool:
    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_user
    smtp_pass = settings.smtp_pass
    from_email = settings.smtp_from_email

    if not smtp_host or not from_email:
        logger.warning("SMTP no configurado. Email no enviado a %s (subject: %s)", to, subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_port == 587:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Email enviado a %s — %s", to, subject)
        return True
    except Exception as e:
        logger.error("Error enviando email a %s: %s", to, e)
        return False


def send_order_confirmation(
    to: str,
    customer_name: str,
    items: list[dict],
    total: float,
    address: str,
    city: str,
    department: Optional[str],
    country: str,
) -> bool:
    items_html = "\n".join(
        _item_row(it["name"], it["quantity"], it["price"]) for it in items
    )
    html = _CONFIRMATION_TEMPLATE.format(
        customer_name=customer_name,
        items_html=items_html,
        total=f"{total:.2f}",
        address=address,
        city=city,
        department=department or "",
        country=country,
    )
    return send_email(to, "¡Gracias por tu compra! - DropStore", html)


def send_dispatch_notification(
    to: str,
    customer_name: str,
    tracking: str,
    tracking_url: Optional[str],
    items: list[dict],
) -> bool:
    items_html = "\n".join(
        _item_row(it["name"], it["quantity"], it["price"]) for it in items
    )
    tracking_link = ""
    if tracking_url:
        tracking_link = (
            f'<a href="{tracking_url}" style="display: inline-block; margin-top: 8px; '
            f'background: #16a34a; color: white; padding: 8px 20px; border-radius: 6px; '
            f'text-decoration: none; font-size: 14px;">Rastrear pedido</a>'
        )
    html = _DISPATCHED_TEMPLATE.format(
        customer_name=customer_name,
        tracking=tracking,
        tracking_link=tracking_link,
        items_html=items_html,
    )
    return send_email(to, "¡Tu pedido está en camino! - DropStore", html)
