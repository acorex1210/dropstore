from __future__ import annotations
from typing import Optional
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProductVariantOut(BaseModel):
    id: uuid.UUID
    name: str
    sku: Optional[str] = None
    base_price: Optional[float] = None
    selling_price: Optional[float] = None
    stock: int = 0
    attributes: dict = {}

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    images: list = []
    base_price: float
    margin_percentage: float
    selling_price: float
    stock: int
    is_active: bool
    provider_name: Optional[str] = "manual"
    variants: list[ProductVariantOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListOut(BaseModel):
    id: uuid.UUID
    name: str
    category: Optional[str] = None
    images: list = []
    selling_price: float
    stock: int
    margin_percentage: float

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    images: list = []
    base_price: float = Field(gt=0)
    margin_percentage: Optional[float] = None
    stock: int = 0
    provider_name: str = "manual"
    provider_id: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    images: Optional[list] = None
    base_price: Optional[float] = Field(default=None, gt=0)
    margin_percentage: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None
