from __future__ import annotations
from typing import Optional
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CartItem(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = Field(gt=0)


class CheckoutRequest(BaseModel):
    items: list[CartItem]
    email: str
    full_name: str
    phone: Optional[str] = None
    address: str
    city: str
    department: Optional[str] = None
    country: str = "Perú"
    notes: Optional[str] = None


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_name: str
    variant_name: Optional[str] = None
    quantity: int
    unit_price: float
    unit_cost: float
    subtotal: float
    margin: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: str
    subtotal: float
    shipping_cost: float
    total_amount: float
    total_cost: float
    total_margin: float
    currency: str
    payment_id: Optional[str] = None
    payment_status: Optional[str] = None
    provider_order_id: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    items: list[OrderItemOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfirmDispatch(BaseModel):
    provider_order_id: str
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None


class PreferenceOut(BaseModel):
    preference_id: str
    init_point: str
    order_id: str
    total: float
