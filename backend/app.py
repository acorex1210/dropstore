import uuid, smtplib, hmac, hashlib, logging, asyncio
from typing import Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
import mercadopago
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship, selectinload

# ── Config ──────────────────────────────────────────────────
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dropstore"
    meli_access_token: str = ""
    meli_public_key: str = ""
    meli_webhook_secret: str = ""
    dropi_base_url: str = "https://api.dropi.co/api/v1"
    dropi_email: str = ""
    dropi_password: str = ""
    dropi_white_brand_id: str = ""
    dropi_integration_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from_email: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    cors_origins: str = "http://localhost:3000"
    default_margin_percentage: float = 30.0
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()

# ── Database ────────────────────────────────────────────────
_db_url = settings.database_url
if _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
engine = create_async_engine(_db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase): pass

async def get_session():
    async with async_session() as session:
        try: yield session
        finally: await session.close()

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ── Models ──────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    images: Mapped[list] = mapped_column(JSONB, nullable=True, default=list)
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    margin_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    provider_id: Mapped[str] = mapped_column(String(100), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=True, default="manual")
    variants: Mapped[list["ProductVariant"]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="product")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=True)
    base_price: Mapped[float] = mapped_column(Float, nullable=True)
    selling_price: Mapped[float] = mapped_column(Float, nullable=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    product: Mapped["Product"] = relationship("Product", back_populates="variants")

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="Perú")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    shipping_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")
    payment_id: Mapped[str] = mapped_column(String(100), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(30), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)
    provider_order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str] = mapped_column(String(100), nullable=True)
    tracking_url: Mapped[str] = mapped_column(String(500), nullable=True)
    shipping_address: Mapped[str] = mapped_column(String(300), nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(100), nullable=False)
    shipping_department: Mapped[str] = mapped_column(String(100), nullable=True)
    shipping_country: Mapped[str] = mapped_column(String(50), nullable=False, default="Perú")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    variant_name: Mapped[str] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    margin: Mapped[float] = mapped_column(Float, nullable=False)
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

# ── Schemas ─────────────────────────────────────────────────
class ProductVariantOut(BaseModel):
    id: uuid.UUID; name: str; sku: Optional[str] = None
    base_price: Optional[float] = None; selling_price: Optional[float] = None
    stock: int = 0; attributes: dict = {}
    model_config = {"from_attributes": True}

class ProductOut(BaseModel):
    id: uuid.UUID; name: str; description: Optional[str] = None
    category: Optional[str] = None; images: list = []; base_price: float
    margin_percentage: float; selling_price: float; stock: int; is_active: bool
    provider_name: Optional[str] = "manual"; variants: list[ProductVariantOut] = []
    created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}

class ProductListOut(BaseModel):
    id: uuid.UUID; name: str; category: Optional[str] = None
    images: list = []; selling_price: float; stock: int; margin_percentage: float
    model_config = {"from_attributes": True}

class ProductCreate(BaseModel):
    name: str; description: Optional[str] = None; category: Optional[str] = None
    images: list = []; base_price: float = Field(gt=0)
    margin_percentage: Optional[float] = None; stock: int = 0
    provider_name: str = "manual"; provider_id: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None
    category: Optional[str] = None; images: Optional[list] = None
    base_price: Optional[float] = Field(default=None, gt=0)
    margin_percentage: Optional[float] = None; stock: Optional[int] = None
    is_active: Optional[bool] = None

class CartItem(BaseModel):
    product_id: str; variant_id: Optional[str] = None; quantity: int = Field(gt=0)

class CheckoutRequest(BaseModel):
    items: list[CartItem]; email: str; full_name: str; phone: Optional[str] = None
    address: str; city: str; department: Optional[str] = None
    country: str = "Perú"; notes: Optional[str] = None

class OrderItemOut(BaseModel):
    id: uuid.UUID; product_name: str; variant_name: Optional[str] = None
    quantity: int; unit_price: float; unit_cost: float; subtotal: float; margin: float
    model_config = {"from_attributes": True}

class OrderOut(BaseModel):
    id: uuid.UUID; customer_id: uuid.UUID; status: str; subtotal: float
    shipping_cost: float; total_amount: float; total_cost: float; total_margin: float
    currency: str; payment_id: Optional[str] = None; payment_status: Optional[str] = None
    provider_order_id: Optional[str] = None; tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None; items: list[OrderItemOut] = []; created_at: datetime
    model_config = {"from_attributes": True}

class ConfirmDispatch(BaseModel):
    provider_order_id: str; tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None

class PreferenceOut(BaseModel):
    preference_id: str; init_point: str; order_id: str; total: float

# ── Schemas: Reports ─────────────────────────────────────────
class StatsSummary(BaseModel):
    total_orders: int; total_revenue: float; total_cost: float; total_margin: float
    avg_margin_pct: float; paid_pending: int; processing: int; shipped: int
    delivered: int; cancelled: int; today_revenue: float; today_orders: int

class TopProduct(BaseModel):
    product_id: str; product_name: str; total_sold: int; total_revenue: float
    total_cost: float; total_margin: float

class SalesReportRow(BaseModel):
    period: str; orders: int; revenue: float; cost: float; margin: float; avg_order: float

class ProfitByProduct(BaseModel):
    product_id: str; product_name: str; units_sold: int; revenue: float; cost: float
    margin: float; margin_pct: float

class ProfitByMonth(BaseModel):
    year_month: str; orders: int; revenue: float; cost: float; margin: float; margin_pct: float

# ── Services: Margin ────────────────────────────────────────
def calc_selling_price(base_price: float, margin_percentage: Optional[float] = None) -> float:
    pct = margin_percentage if margin_percentage is not None else settings.default_margin_percentage
    return round(base_price * (1 + pct / 100), 2)

# ── Services: Mercado Pago ──────────────────────────────────
_mp_sdk: mercadopago.SDK | None = None

def mp_sdk() -> mercadopago.SDK | None:
    global _mp_sdk
    if _mp_sdk is None and settings.meli_access_token:
        _mp_sdk = mercadopago.SDK(settings.meli_access_token)
    return _mp_sdk

def mp_create_preference(order_id: uuid.UUID, items: list[dict], payer_email: str,
                          success_url: str, failure_url: str, pending_url: str,
                          notification_url: str) -> Optional[dict]:
    sdk = mp_sdk()
    if not sdk: return None
    result = sdk.preference().create({
        "items": [{"id": str(it.get("product_id","")), "title": it["title"],
                    "quantity": it["quantity"], "unit_price": float(it["unit_price"]),
                    "currency_id": "PEN"} for it in items],
        "payer": {"email": payer_email},
        "back_urls": {"success": success_url, "failure": failure_url, "pending": pending_url},
        "auto_return": "approved", "notification_url": notification_url,
        "external_reference": str(order_id),
    })
    return result.get("response") if result.get("status",400) in (200,201) else None

# ── Services: Dropi Client ──────────────────────────────────
DROP_BASE = settings.dropi_base_url.rstrip("/")
_log = logging.getLogger("dropstore")

async def _drop_req(method: str, path: str, body: Optional[dict] = None) -> Any:
    hdrs = {"Content-Type": "application/json", "dropi-integracion-key": settings.dropi_integration_token}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await (c.get if method=="GET" else c.post)(f"{DROP_BASE}{path}", headers=hdrs, json=body or {})
        if r.status_code >= 400: raise RuntimeError(f"Dropi API error {r.status_code}: {r.text}")
        return r.json()

async def drop_auth() -> str:
    d = await _drop_req("POST", "/login", {"email": settings.dropi_email, "password": settings.dropi_password, "white_brand_id": settings.dropi_white_brand_id})
    return d.get("token","") if isinstance(d,dict) else ""

async def drop_perm_token(temp: str) -> str:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{DROP_BASE}/shops/store", headers={"Authorization":f"Bearer {temp}","Content-Type":"application/json"})
        if r.status_code >= 400: raise RuntimeError(f"Dropi perm error: {r.text}")
        d = r.json()
        return d.get("token","") if isinstance(d,dict) else ""

async def drop_categories() -> list:
    d = await _drop_req("GET","/categories")
    return (d.get("data",[]) if isinstance(d,dict) else d) if isinstance(d,(dict,list)) else []

async def drop_products_page(pageSize=50, startData=0, no_count=True, **kw) -> dict:
    b = {"pageSize":pageSize,"startData":startData,"no_count":no_count, **kw}
    d = await _drop_req("POST","/products/index", b)
    return d if isinstance(d,dict) else {"data":d if isinstance(d,list) else []}

async def drop_product_detail(pid: int) -> dict:
    d = await _drop_req("GET", f"/products/v2/{pid}")
    return d if isinstance(d,dict) else {"data":d}

async def drop_create_order(payload: dict) -> dict:
    d = await _drop_req("POST","/orders/myorders", payload)
    return d if isinstance(d,dict) else {"data":d}

async def drop_order_by_shop(shop_id: str) -> dict:
    d = await _drop_req("GET","/orders/myorders")
    if isinstance(d,dict):
        for o in (d.get("data",[]) if isinstance(d.get("data"),list) else []):
            if o.get("shop_order_id")==shop_id: return o
    return {}

# ── Services: Dropi Products Sync ───────────────────────────
async def drop_sync_products(session: AsyncSession, default_margin: Optional[float] = None) -> int:
    margin = default_margin or 30.0; page = 0; created = 0
    while True:
        resp = await drop_products_page(pageSize=50, startData=page*50, no_count=True)
        items = resp.get("data", resp.get("products",[]))
        if not items or not isinstance(items,list): break
        for item in items:
            if not isinstance(item,dict): continue
            did = item.get("id")
            if not did: continue
            name = item.get("name",item.get("productName","Sin nombre"))
            ps = item.get("price",item.get("sellPrice","0"))
            bp = float(ps)/100 if isinstance(ps,int) else float(ps)
            sp = calc_selling_price(bp,margin)
            imgs_raw = item.get("images",item.get("image",[]))
            imgs = [imgs_raw] if isinstance(imgs_raw,str) else ([i for i in imgs_raw if isinstance(i,str)] if isinstance(imgs_raw,list) else [])
            cat = str(item.get("categoryName",item.get("category","")))
            stk = int(item.get("stock",item.get("inventory",0)))
            r = await session.execute(select(Product).where(Product.provider_id==str(did), Product.provider_name=="dropi"))
            p = r.scalar_one_or_none()
            if p:
                p.name=name; p.base_price=bp; p.margin_percentage=margin; p.selling_price=sp
                p.images=imgs; p.category=cat; p.stock=stk
            else:
                p = Product(name=name, description=item.get("description",""), category=cat, images=imgs,
                            base_price=bp, margin_percentage=margin, selling_price=sp, stock=stk,
                            provider_id=str(did), provider_name="dropi")
                session.add(p); created+=1
            await session.flush()
            for var in (item.get("variations",item.get("variants",[])) or []):
                if not isinstance(var,dict): continue
                vid = var.get("id")
                if not vid: continue
                vn = var.get("name",var.get("value",""))
                vps = var.get("price",var.get("sellPrice",0))
                vp = float(vps)/100 if isinstance(vps,int) else float(vps)
                vs = int(var.get("stock",var.get("inventory",0)))
                va = {"type": var.get("attribute_type",var.get("type",""))} if var.get("attribute_type") or var.get("type") else {}
                rv = await session.execute(select(ProductVariant).where(ProductVariant.product_id==p.id, ProductVariant.sku==str(vid)))
                pv = rv.scalar_one_or_none()
                if pv: pv.name=vn; pv.base_price=vp; pv.selling_price=calc_selling_price(vp,margin) if vp else None; pv.stock=vs; pv.attributes=va
                else: session.add(ProductVariant(product_id=p.id, name=vn, sku=str(vid), base_price=vp, selling_price=calc_selling_price(vp,margin) if vp else None, stock=vs, attributes=va))
        page+=1
        if len(items)<50: break
    await session.commit(); return created

# ── Services: Dropi Orders ──────────────────────────────────
async def drop_push_order(order_id: uuid.UUID, session: AsyncSession) -> Optional[str]:
    r = await session.execute(select(Order).where(Order.id==order_id).options(selectinload(Order.items), selectinload(Order.customer)))
    o = r.scalar_one_or_none()
    if not o or o.status!="paid" or o.provider_order_id: return None
    c = o.customer
    pids = [it.product_id for it in o.items if it.product_id]
    pmap = {}
    if pids:
        for p in (await session.execute(select(Product).where(Product.id.in_(pids)))).scalars(): pmap[p.id]=p
    prods = []; total_cents = 0
    for it in o.items:
        p = pmap.get(it.product_id); did = int(p.provider_id) if p and p.provider_id else 0
        pc = int(it.unit_price*100); total_cents+=pc*it.quantity
        vi = None
        if it.variant_name and p:
            for v in p.variants:
                if v.name==it.variant_name and v.sku: vi=int(v.sku); break
        prods.append({"id":did,"price":pc,"quantity":it.quantity,"variation_id":vi})
    payload = {"calculate_costs_and_shiping":True,"state":(o.shipping_department or "").upper(),
               "city":o.shipping_city.upper(),"name":c.full_name.split()[0] if c.full_name else "",
               "surname":" ".join(c.full_name.split()[1:]) if " " in c.full_name else c.full_name,
               "dir":o.shipping_address,"client_email":c.email,"notes":c.notes or "","payment_method_id":1,
               "phone":c.phone or "","rate_type":"SIN RECAUDO","type":"FINAL_ORDER","total_order":total_cents,
               "products":prods,"shop_order_id":str(o.id)}
    try:
        resp = await drop_create_order(payload)
        rd = resp if isinstance(resp,dict) else {}
        doid = rd.get("data",{}).get("id") if isinstance(rd.get("data"),dict) else rd.get("id")
        if doid: o.provider_order_id=str(doid); o.status="processing"; await session.commit(); return str(doid)
        else: await session.commit(); return None
    except Exception as e:
        o.notes = (o.notes or "")+f" [Dropi error: {e}]"; await session.commit(); return None

async def drop_sync_tracking(order_id: uuid.UUID, session: AsyncSession) -> bool:
    r = await session.execute(select(Order).where(Order.id==order_id))
    o = r.scalar_one_or_none()
    if not o or not o.provider_order_id: return False
    try:
        resp = await drop_order_by_shop(str(o.id))
        if not resp or not isinstance(resp,dict): return False
        guide = resp.get("guide",resp.get("tracking",resp.get("guia","")))
        sd = resp.get("status","")
        if guide and guide!=o.tracking_number:
            o.tracking_number=str(guide)
            if not o.tracking_url: o.tracking_url=f"https://www.dropi.co/tracking/{guide}"
        if sd:
            sl=sd.lower()
            if "entregado" in sl or "delivered" in sl: o.status="delivered"
            elif "enviado" in sl or "shipped" in sl or "despachado" in sl:
                if o.status!="delivered": o.status="shipped"
        await session.commit(); return True
    except: return False

async def drop_sync_all(session: AsyncSession) -> int:
    r = await session.execute(select(Order).where(Order.status.in_(["processing","shipped"]), Order.provider_order_id.isnot(None)))
    u=0
    for o in r.scalars():
        if await drop_sync_tracking(o.id,session): u+=1
    return u

# ── Services: Email ─────────────────────────────────────────
_log = logging.getLogger("dropstore")

HTML_CONFIRM = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
<div style="background:#16a34a;color:white;padding:20px;border-radius:10px 10px 0 0;text-align:center;"><h1 style="margin:0;">¡Gracias por tu compra!</h1></div>
<div style="border:1px solid #e5e7eb;border-top:none;padding:20px;border-radius:0 0 10px 10px;">
<p>Hola <strong>{name}</strong>,</p><p>Hemos recibido tu pago correctamente. Estamos procesando tu pedido.</p>
<h3 style="color:#374151;">Resumen</h3>
<table style="width:100%;border-collapse:collapse;font-size:14px;">
<thead><tr style="background:#f9fafb;"><th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;">Producto</th><th style="text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;">Cant.</th><th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;">Precio</th></tr></thead>
<tbody>{items}</tbody>
<tfoot><tr><td colspan="2" style="text-align:right;padding:8px;font-weight:bold;">Total:</td><td style="text-align:right;padding:8px;font-weight:bold;color:#16a34a;">S/ {total}</td></tr></tfoot></table>
<p style="color:#6b7280;font-size:13px;margin-top:20px;">Te enviaremos el tracking cuando sea despachado.</p></div></body></html>"""

HTML_DISP = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
<div style="background:#2563eb;color:white;padding:20px;border-radius:10px 10px 0 0;text-align:center;"><h1 style="margin:0;">¡Tu pedido está en camino!</h1></div>
<div style="border:1px solid #e5e7eb;border-top:none;padding:20px;border-radius:0 0 10px 10px;">
<p>Hola <strong>{name}</strong>,</p><p>Tu pedido ha sido despachado.</p>
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:15px;margin:15px 0;">
<p style="margin:0;font-size:13px;color:#6b7280;">Número de seguimiento:</p>
<p style="margin:5px 0 0;font-size:18px;font-weight:bold;color:#16a34a;">{tracking}</p>{link}</div>
<table style="width:100%;border-collapse:collapse;font-size:14px;">
<thead><tr style="background:#f9fafb;"><th style="text-align:left;padding:8px;border-bottom:1px solid #e5e7eb;">Producto</th><th style="text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;">Cant.</th><th style="text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;">Precio</th></tr></thead>
<tbody>{items}</tbody></table></div></body></html>"""

def _item_row_html(n: str, q: int, p: float) -> str:
    return f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb;'>{n}</td><td style='text-align:center;padding:8px;border-bottom:1px solid #e5e7eb;'>{q}</td><td style='text-align:right;padding:8px;border-bottom:1px solid #e5e7eb;'>S/ {p:.2f}</td></tr>"

def send_email(to: str, subject: str, html: str) -> bool:
    if not settings.smtp_host or not settings.smtp_from_email:
        _log.warning("SMTP no configurado. No se envió email a %s", to); return False
    msg = MIMEMultipart("alternative")
    msg["Subject"]=subject; msg["From"]=settings.smtp_from_email; msg["To"]=to
    msg.attach(MIMEText(html,"html"))
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            if settings.smtp_port==587: s.starttls()
            if settings.smtp_user and settings.smtp_pass: s.login(settings.smtp_user, settings.smtp_pass)
            s.send_message(msg)
        _log.info("Email enviado a %s — %s", to, subject); return True
    except Exception as e: _log.error("Error email a %s: %s", to, e); return False

def send_order_confirmation(to: str, name: str, items: list[dict], total: float) -> bool:
    its = "\n".join(_item_row_html(i["name"],i["quantity"],i["price"]) for i in items)
    return send_email(to, "¡Gracias por tu compra! - DropStore", HTML_CONFIRM.format(name=name, items=its, total=f"{total:.2f}"))

def send_dispatch_notification(to: str, name: str, tracking: str, tracking_url: Optional[str], items: list[dict]) -> bool:
    its = "\n".join(_item_row_html(i["name"],i["quantity"],i["price"]) for i in items)
    link = (f'<a href="{tracking_url}" style="display:inline-block;margin-top:8px;background:#16a34a;color:white;padding:8px 20px;border-radius:6px;text-decoration:none;font-size:14px;">Rastrear</a>'
            if tracking_url else "")
    return send_email(to, "¡Tu pedido está en camino! - DropStore", HTML_DISP.format(name=name, tracking=tracking, link=link, items=its))

# ── Services: WhatsApp ──────────────────────────────────────
async def wa_send(to: str, msg: str) -> bool:
    if not settings.whatsapp_phone_id or not settings.whatsapp_token:
        _log.warning("WhatsApp no configurado"); return False
    try:
        r = await httpx.AsyncClient(timeout=15).post(
            f"https://graph.facebook.com/v22.0/{settings.whatsapp_phone_id}/messages",
            headers={"Authorization":f"Bearer {settings.whatsapp_token}","Content-Type":"application/json"},
            json={"messaging_product":"whatsapp","to":to,"type":"text","text":{"body":msg}})
        return r.status_code==200
    except: return False

async def wa_order_confirm(to: str, name: str, oid: str, total: float) -> bool:
    return await wa_send(to, f"🛒 DropStore - Confirmación\nHola {name}, recibimos tu pago.\nPedido: {oid[:8]}...\nTotal: S/ {total:.2f}")

async def wa_tracking(to: str, name: str, tracking: str) -> bool:
    return await wa_send(to, f"📦 DropStore - En camino\nHola {name}, tu pedido fue despachado.\nTracking: {tracking}")

# ── Services: Notifications ─────────────────────────────────
async def notify_payment_confirmed(order: Order) -> None:
    c = order.customer
    if not c: return
    its = [{"name":i.product_name,"quantity":i.quantity,"price":i.unit_price} for i in order.items]
    send_order_confirmation(c.email, c.full_name, its, order.total_amount)
    if c.phone: await wa_order_confirm(c.phone, c.full_name, str(order.id), order.total_amount)

async def notify_order_dispatched(order: Order) -> None:
    c = order.customer
    if not c or not order.tracking_number: return
    its = [{"name":i.product_name,"quantity":i.quantity,"price":i.unit_price} for i in order.items]
    send_dispatch_notification(c.email, c.full_name, order.tracking_number, order.tracking_url, its)
    if c.phone: await wa_tracking(c.phone, c.full_name, order.tracking_number)

# ── API: Products ───────────────────────────────────────────
router_prod = APIRouter(prefix="/api/products", tags=["products"])

@router_prod.get("", response_model=list[ProductListOut])
async def list_products(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Product).where(Product.is_active==True).order_by(Product.created_at.desc()))
    return r.scalars().all()

@router_prod.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Product).where(Product.id==product_id, Product.is_active==True).options(selectinload(Product.variants)))
    p = r.scalar_one_or_none()
    if not p: raise HTTPException(404, detail="Producto no encontrado")
    return p

@router_prod.post("", response_model=ProductOut, status_code=201)
async def create_product(data: ProductCreate, session: AsyncSession = Depends(get_session)):
    sp = calc_selling_price(data.base_price, data.margin_percentage)
    p = Product(name=data.name, description=data.description, category=data.category, images=data.images,
                base_price=data.base_price, margin_percentage=data.margin_percentage or 30.0,
                selling_price=sp, stock=data.stock, provider_name=data.provider_name, provider_id=data.provider_id)
    session.add(p); await session.commit(); await session.refresh(p); return p

@router_prod.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: uuid.UUID, data: ProductUpdate, session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Product).where(Product.id==product_id))
    p = r.scalar_one_or_none()
    if not p: raise HTTPException(404, detail="Producto no encontrado")
    upd = data.model_dump(exclude_unset=True)
    for k,v in upd.items(): setattr(p,k,v)
    if "base_price" in upd or "margin_percentage" in upd: p.selling_price = calc_selling_price(p.base_price, p.margin_percentage)
    await session.commit(); await session.refresh(p); return p

# ── API: Checkout ───────────────────────────────────────────
router_co = APIRouter(prefix="/api/checkout", tags=["checkout"])

@router_co.post("/create-preference", response_model=PreferenceOut)
async def create_checkout_preference(data: CheckoutRequest, session: AsyncSession = Depends(get_session)):
    if not data.items: raise HTTPException(400, detail="Carrito vacío")
    pids = [uuid.UUID(it.product_id) for it in data.items]
    r = await session.execute(select(Product).where(Product.id.in_(pids), Product.is_active==True))
    prods = {str(p.id):p for p in r.scalars().all()}
    items_data=[]; pref_items=[]; subtotal=0.0; cost=0.0
    for ci in data.items:
        p = prods.get(ci.product_id)
        if not p: raise HTTPException(404, detail=f"Producto {ci.product_id} no encontrado")
        lt = round(p.selling_price*ci.quantity,2); lc = round(p.base_price*ci.quantity,2)
        items_data.append({"product_id":p.id,"product_name":p.name,"quantity":ci.quantity,"unit_price":p.selling_price,"unit_cost":p.base_price,"subtotal":lt,"margin":lt-lc})
        pref_items.append({"product_id":str(p.id),"title":p.name,"quantity":ci.quantity,"unit_price":p.selling_price})
        subtotal+=lt; cost+=lc
    subtotal=round(subtotal,2); cost=round(cost,2); oid=uuid.uuid4()
    pref = mp_create_preference(oid, pref_items, data.email,
        "http://localhost:3000/checkout?success=true","http://localhost:3000/checkout?failed=true",
        "http://localhost:3000/checkout?pending=true",
        "https://YOUR_NGROK.ngrok.app/api/webhooks/mercadopago")
    if not pref: raise HTTPException(500, detail="Error al crear preferencia de pago")
    cust = Customer(email=data.email, full_name=data.full_name, phone=data.phone, address=data.address,
                    city=data.city, department=data.department, country=data.country, notes=data.notes)
    session.add(cust); await session.flush()
    o = Order(id=oid, customer_id=cust.id, status="pending", subtotal=subtotal, total_amount=subtotal,
              total_cost=cost, total_margin=subtotal-cost, payment_id=pref.get("id"), payment_status="pending",
              shipping_address=data.address, shipping_city=data.city, shipping_department=data.department, shipping_country=data.country)
    session.add(o); await session.flush()
    for it in items_data: session.add(OrderItem(order_id=o.id, **it))
    await session.commit()
    return PreferenceOut(preference_id=pref["id"], init_point=pref["init_point"], order_id=str(o.id), total=subtotal)

@router_co.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Order).where(Order.id==order_id).options(selectinload(Order.items)))
    o = r.scalar_one_or_none()
    if not o: raise HTTPException(404, detail="Orden no encontrada"); return o

@router_co.get("/orders", response_model=list[OrderOut])
async def list_orders(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Order).order_by(Order.created_at.desc()).options(selectinload(Order.items)))
    return r.scalars().all()

@router_co.post("/dispatch/{order_id}", response_model=OrderOut)
async def confirm_dispatch(order_id: uuid.UUID, data: ConfirmDispatch, session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Order).where(Order.id==order_id).options(selectinload(Order.items), selectinload(Order.customer)))
    o = r.scalar_one_or_none()
    if not o: raise HTTPException(404, detail="Orden no encontrada")
    ht = bool(o.tracking_number)
    o.provider_order_id=data.provider_order_id; o.status="processing"
    if data.tracking_number: o.tracking_number=data.tracking_number
    if data.tracking_url: o.tracking_url=data.tracking_url
    await session.commit(); await session.refresh(o)
    if data.tracking_number and not ht: await notify_order_dispatched(o)
    return o

# ── API: Webhooks ───────────────────────────────────────────
router_wh = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router_wh.post("/mercadopago")
async def mercadopago_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    action = data.get("action") or data.get("type","")
    pid = data.get("data",{}).get("id") if "data" in data else None
    if action in ("payment.created","payment.updated") and pid:
        async with httpx.AsyncClient() as c:
            mp = await c.get(f"https://api.mercadopago.com/v1/payments/{pid}", headers={"Authorization":f"Bearer {settings.meli_access_token}"})
            if mp.status_code!=200: raise HTTPException(502, detail="Error consultando pago en MP")
            pay = mp.json(); ext = pay.get("external_reference",""); st = pay.get("status","")
            if ext:
                r = await session.execute(select(Order).where(Order.id==ext).options(selectinload(Order.items), selectinload(Order.customer)))
                o = r.scalar_one_or_none()
                if o:
                    o.payment_status=st; o.payment_id=str(pay.get("id","")); o.payment_method=pay.get("payment_method_id","")
                    if st=="approved":
                        o.status="paid"; await session.commit(); await session.refresh(o)
                        await notify_payment_confirmed(o); await drop_push_order(o.id, session)
                    elif st in ("cancelled","rejected","refunded"): o.status="cancelled"; await session.commit()
                    else: await session.commit()
    return {"received":True}

# ── API: Dropi Sync ─────────────────────────────────────────
router_drop = APIRouter(prefix="/api/dropi", tags=["dropi"])

@router_drop.post("/sync-products")
async def sync_all_products(margin: float = Query(30.0), session: AsyncSession = Depends(get_session)):
    return {"synced": await drop_sync_products(session, default_margin=margin)}

@router_drop.post("/push-order/{order_id}")
async def push_order(order_id: str, session: AsyncSession = Depends(get_session)):
    try: oid = uuid.UUID(order_id)
    except: raise HTTPException(400, detail="ID inválido")
    did = await drop_push_order(oid, session)
    if not did: return {"pushed":False,"detail":"No se pudo crear en Dropi"}
    return {"pushed":True,"dropi_order_id":did}

@router_drop.post("/sync-tracking/{order_id}")
async def sync_tracking(order_id: str, session: AsyncSession = Depends(get_session)):
    try: oid = uuid.UUID(order_id)
    except: raise HTTPException(400, detail="ID inválido")
    return {"updated": await drop_sync_tracking(oid, session)}

@router_drop.post("/sync-all-tracking")
async def sync_all_tracking(session: AsyncSession = Depends(get_session)):
    return {"synced": await drop_sync_all(session)}

@router_drop.get("/auth")
async def get_auth_token():
    if not settings.dropi_email or not settings.dropi_password: return {"error":"Configura DROPI_EMAIL y DROPI_PASSWORD"}
    if not settings.dropi_white_brand_id: return {"error":"Configura DROPI_WHITE_BRAND_ID"}
    t = await drop_auth()
    if not t: return {"error":"Falló autenticación"}
    p = await drop_perm_token(t)
    return {"permanent_token":p, "detail":"Copia este token en DROPI_INTEGRATION_TOKEN en .env"}

# ── API: Admin / Reports / Export ────────────────────────────
router_admin = APIRouter(prefix="/api/admin", tags=["admin"])

@router_admin.get("/stats", response_model=StatsSummary)
async def admin_stats(session: AsyncSession = Depends(get_session)):
    r_all = await session.execute(select(Order))
    all_orders = r_all.scalars().all()
    total_orders = len(all_orders)
    total_revenue = sum(o.total_amount for o in all_orders)
    total_cost = sum(o.total_cost for o in all_orders)
    total_margin = sum(o.total_margin for o in all_orders)
    avg_margin_pct = (total_margin / total_cost * 100) if total_cost else 0.0

    # status breakdown
    statuses = {}
    for o in all_orders:
        statuses[o.status] = statuses.get(o.status, 0) + 1

    # today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = [o for o in all_orders if o.created_at >= today_start]
    today_revenue = sum(o.total_amount for o in today_orders)

    return StatsSummary(
        total_orders=total_orders, total_revenue=round(total_revenue, 2),
        total_cost=round(total_cost, 2), total_margin=round(total_margin, 2),
        avg_margin_pct=round(avg_margin_pct, 1),
        paid_pending=statuses.get("paid", 0), processing=statuses.get("processing", 0),
        shipped=statuses.get("shipped", 0), delivered=statuses.get("delivered", 0),
        cancelled=statuses.get("cancelled", 0),
        today_revenue=round(today_revenue, 2), today_orders=len(today_orders),
    )

@router_admin.get("/top-products", response_model=list[TopProduct])
async def admin_top_products(limit: int = Query(10), session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(OrderItem))
    items = r.scalars().all()
    agg = {}
    for it in items:
        pid = str(it.product_id) if it.product_id else "unknown"
        if pid not in agg:
            agg[pid] = {"name": it.product_name, "qty": 0, "rev": 0.0, "cost": 0.0, "margin": 0.0}
        agg[pid]["qty"] += it.quantity
        agg[pid]["rev"] += it.subtotal
        agg[pid]["cost"] += it.unit_cost * it.quantity
        agg[pid]["margin"] += it.margin
    sorted_products = sorted(agg.values(), key=lambda x: x["rev"], reverse=True)[:limit]
    return [TopProduct(product_id=pid, product_name=p["name"], total_sold=p["qty"],
                       total_revenue=round(p["rev"], 2), total_cost=round(p["cost"], 2),
                       total_margin=round(p["margin"], 2))
            for pid, p in enumerate(sorted_products)]

@router_admin.get("/reports/sales", response_model=list[SalesReportRow])
async def sales_report(days: int = Query(30), session: AsyncSession = Depends(get_session)):
    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    r = await session.execute(select(Order).where(Order.created_at >= cutoff))
    orders = r.scalars().all()
    daily = {}
    for o in orders:
        day = o.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"orders": 0, "revenue": 0.0, "cost": 0.0, "margin": 0.0}
        daily[day]["orders"] += 1
        daily[day]["revenue"] += o.total_amount
        daily[day]["cost"] += o.total_cost
        daily[day]["margin"] += o.total_margin
    sorted_days = sorted(daily.keys(), reverse=True)[:days]
    return [SalesReportRow(period=d, orders=daily[d]["orders"],
                           revenue=round(daily[d]["revenue"], 2),
                           cost=round(daily[d]["cost"], 2),
                           margin=round(daily[d]["margin"], 2),
                           avg_order=round(daily[d]["revenue"] / daily[d]["orders"], 2) if daily[d]["orders"] else 0)
            for d in sorted_days]

@router_admin.get("/reports/profit", response_model=dict)
async def profit_report(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(OrderItem))
    items = r.scalars().all()
    by_product = {}
    by_month = {}
    for it in items:
        pid = str(it.product_id) if it.product_id else "unknown"
        if pid not in by_product:
            by_product[pid] = {"name": it.product_name, "qty": 0, "rev": 0.0, "cost": 0.0, "margin": 0.0}
        by_product[pid]["qty"] += it.quantity
        by_product[pid]["rev"] += it.subtotal
        by_product[pid]["cost"] += it.unit_cost * it.quantity
        by_product[pid]["margin"] += it.margin

    r2 = await session.execute(select(Order))
    for o in r2.scalars().all():
        ym = o.created_at.strftime("%Y-%m")
        if ym not in by_month:
            by_month[ym] = {"orders": 0, "revenue": 0.0, "cost": 0.0, "margin": 0.0}
        by_month[ym]["orders"] += 1
        by_month[ym]["revenue"] += o.total_amount
        by_month[ym]["cost"] += o.total_cost
        by_month[ym]["margin"] += o.total_margin

    products = [ProfitByProduct(product_id=pid, product_name=p["name"], units_sold=p["qty"],
                                revenue=round(p["rev"], 2), cost=round(p["cost"], 2),
                                margin=round(p["margin"], 2),
                                margin_pct=round(p["margin"] / p["cost"] * 100, 1) if p["cost"] else 0)
                for pid, p in sorted(by_product.items(), key=lambda x: x[1]["margin"], reverse=True)]

    months = [ProfitByMonth(year_month=m, orders=d["orders"], revenue=round(d["revenue"], 2),
                            cost=round(d["cost"], 2), margin=round(d["margin"], 2),
                            margin_pct=round(d["margin"] / d["cost"] * 100, 1) if d["cost"] else 0)
              for m, d in sorted(by_month.items(), reverse=True)]

    totals = {"revenue": sum(p.revenue for p in products),
              "cost": sum(p.cost for p in products),
              "margin": sum(p.margin for p in products)}
    totals["margin_pct"] = round(totals["margin"] / totals["cost"] * 100, 1) if totals["cost"] else 0

    return {"products": [p.model_dump() for p in products],
            "months": [m.model_dump() for m in months],
            "totals": totals}

def _csv_escape(val: Any) -> str:
    s = str(val) if val is not None else ""
    if "," in s or '"' in s or "\n" in s:
        s = '"' + s.replace('"', '""') + '"'
    return s

def _csv_line(values: list[Any]) -> str:
    return ",".join(_csv_escape(v) for v in values) + "\n"

@router_admin.get("/export/orders")
async def export_orders_csv(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Order).order_by(Order.created_at.desc()).options(selectinload(Order.items)))
    orders = r.scalars().all()

    def generate():
        yield _csv_line(["OrderID", "Status", "Subtotal", "ShippingCost", "Total", "Cost", "Margin",
                         "Currency", "PaymentID", "PaymentStatus", "ProviderOrderID", "TrackingNumber",
                         "TrackingURL", "ShippingAddress", "ShippingCity", "ShippingDepartment",
                         "ShippingCountry", "Items", "CreatedAt"])
        for o in orders:
            items_str = "; ".join(f"{i.product_name} x{i.quantity} S/{i.unit_price:.2f}" for i in o.items)
            yield _csv_line([str(o.id), o.status, o.subtotal, o.shipping_cost, o.total_amount,
                            o.total_cost, o.total_margin, o.currency, o.payment_id or "",
                            o.payment_status or "", o.provider_order_id or "", o.tracking_number or "",
                            o.tracking_url or "", o.shipping_address, o.shipping_city,
                            o.shipping_department or "", o.shipping_country, items_str,
                            o.created_at.isoformat()])

    return StreamingResponse(generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=orders.csv"})

@router_admin.get("/export/products")
async def export_products_csv(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(Product).order_by(Product.name).options(selectinload(Product.variants)))
    products = r.scalars().all()

    def generate():
        yield _csv_line(["ProductID", "Name", "Category", "BasePrice", "Margin%", "SellingPrice",
                         "Stock", "Active", "Provider", "ProviderID", "Variants", "CreatedAt"])
        for p in products:
            variants_str = "; ".join(f"{v.name} S/{v.selling_price}" for v in p.variants) if p.variants else ""
            yield _csv_line([str(p.id), p.name, p.category or "", p.base_price, p.margin_percentage,
                            p.selling_price, p.stock, "Yes" if p.is_active else "No",
                            p.provider_name or "", p.provider_id or "", variants_str,
                            p.created_at.isoformat()])

    return StreamingResponse(generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=products.csv"})

@router_admin.get("/export/profit")
async def export_profit_csv(session: AsyncSession = Depends(get_session)):
    r = await session.execute(select(OrderItem))
    items = r.scalars().all()

    def generate():
        yield _csv_line(["ProductName", "Variant", "Quantity", "UnitPrice", "UnitCost",
                         "Subtotal", "Margin", "OrderID", "CreatedAt"])
        for it in items:
            yield _csv_line([it.product_name, it.variant_name or "", it.quantity,
                            it.unit_price, it.unit_cost, it.subtotal, it.margin,
                            str(it.order_id), ""])

    return StreamingResponse(generate(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=profit_report.csv"})

# ── Main App ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(title="DropStore API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router_prod)
app.include_router(router_co)
app.include_router(router_wh)
app.include_router(router_drop)
app.include_router(router_admin)

@app.get("/api/health")
async def health():
    return {"status": "ok"}
