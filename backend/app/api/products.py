from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Product
from app.schemas.product import ProductCreate, ProductListOut, ProductOut, ProductUpdate
from app.services.margin import calc_selling_price

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductListOut])
async def list_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Product).where(Product.is_active == True).order_by(Product.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Product)
        .where(Product.id == product_id, Product.is_active == True)
        .options(selectinload(Product.variants))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(data: ProductCreate, session: AsyncSession = Depends(get_session)):
    margin = data.margin_percentage
    selling = calc_selling_price(data.base_price, margin)
    product = Product(
        name=data.name,
        description=data.description,
        category=data.category,
        images=data.images,
        base_price=data.base_price,
        margin_percentage=margin or 30.0,
        selling_price=selling,
        stock=data.stock,
        provider_name=data.provider_name,
        provider_id=data.provider_id,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: uuid.UUID, data: ProductUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    if "base_price" in update_data or "margin_percentage" in update_data:
        product.selling_price = calc_selling_price(product.base_price, product.margin_percentage)

    await session.commit()
    await session.refresh(product)
    return product
