import uuid
from typing import Optional,  Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductVariant
from app.services.dropi_client import get_categories, get_products_page, get_product_detail
from app.services.margin import calc_selling_price


async def sync_categories(session: AsyncSession) -> dict[int, str]:
    """Fetch categories from Dropi. Returns {id: name}."""
    cats = await get_categories()
    mapping: dict[int, str] = {}
    for cat in cats:
        if isinstance(cat, dict):
            cid = cat.get("id")
            name = cat.get("name", "")
            if cid:
                mapping[int(cid)] = name
    return mapping


async def sync_products(
    session: AsyncSession,
    default_margin: Optional[float] = None,
) -> int:
    """Pull all products from Dropi and upsert into local DB.
    Returns number of products created/updated.
    """
    margin = default_margin or 30.0
    page = 0
    page_size = 50
    created = 0

    while True:
        resp = await get_products_page(page_size=page_size, start_data=page * page_size, no_count=True)
        raw = resp if isinstance(resp, dict) else {}
        items = raw.get("data", raw.get("products", []))
        if not items or not isinstance(items, list):
            break

        for item in items:
            if not isinstance(item, dict):
                continue

            dropi_id = item.get("id")
            if not dropi_id:
                continue

            name = item.get("name", item.get("productName", "Sin nombre"))
            price_str = item.get("price", item.get("sellPrice", "0"))
            base_price = float(price_str) / 100 if isinstance(price_str, int) else float(price_str)

            selling_price = calc_selling_price(base_price, margin)

            images_raw = item.get("images", item.get("image", []))
            if isinstance(images_raw, str):
                images = [images_raw]
            elif isinstance(images_raw, list):
                images = [img for img in images_raw if isinstance(img, str)]
            else:
                images = []

            category_name = str(item.get("categoryName", item.get("category", "")))

            stock = int(item.get("stock", item.get("inventory", 0)))

            existing = await session.execute(
                select(Product).where(Product.provider_id == str(dropi_id), Product.provider_name == "dropi")
            )
            product = existing.scalar_one_or_none()

            if product:
                product.name = name
                product.base_price = base_price
                product.margin_percentage = margin
                product.selling_price = selling_price
                product.images = images
                product.category = category_name
                product.stock = stock
            else:
                product = Product(
                    name=name,
                    description=item.get("description", ""),
                    category=category_name,
                    images=images,
                    base_price=base_price,
                    margin_percentage=margin,
                    selling_price=selling_price,
                    stock=stock,
                    provider_id=str(dropi_id),
                    provider_name="dropi",
                )
                session.add(product)
                created += 1

            await session.flush()

            variations = item.get("variations", item.get("variants", []))
            if variations and isinstance(variations, list):
                for var in variations:
                    if not isinstance(var, dict):
                        continue
                    var_id = var.get("id")
                    if not var_id:
                        continue

                    var_name = var.get("name", var.get("value", ""))
                    var_price_str = var.get("price", var.get("sellPrice", 0))
                    var_price = float(var_price_str) / 100 if isinstance(var_price_str, int) else float(var_price_str)
                    var_stock = int(var.get("stock", var.get("inventory", 0)))

                    var_attrs = {}
                    attr_type = var.get("attribute_type", var.get("type"))
                    if attr_type:
                        var_attrs["type"] = attr_type

                    existing_var = await session.execute(
                        select(ProductVariant).where(
                            ProductVariant.product_id == product.id,
                            ProductVariant.sku == str(var_id),
                        )
                    )
                    pv = existing_var.scalar_one_or_none()
                    if pv:
                        pv.name = var_name
                        pv.base_price = var_price
                        pv.selling_price = calc_selling_price(var_price, margin) if var_price else None
                        pv.stock = var_stock
                        pv.attributes = var_attrs
                    else:
                        pv = ProductVariant(
                            product_id=product.id,
                            name=var_name,
                            sku=str(var_id),
                            base_price=var_price,
                            selling_price=calc_selling_price(var_price, margin) if var_price else None,
                            stock=var_stock,
                            attributes=var_attrs,
                        )
                        session.add(pv)

        page += 1
        if len(items) < page_size:
            break

    await session.commit()
    return created


async def sync_product_detail(
    session: AsyncSession,
    dropi_product_id: int,
    margin: Optional[float] = None,
) -> Optional[Product]:
    """Sync a single product from Dropi by its ID."""
    margin = margin or 30.0
    raw = await get_product_detail(dropi_product_id)
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    if not data or not isinstance(data, dict):
        return None

    dropi_id = data.get("id")
    if not dropi_id:
        return None

    name = data.get("name", data.get("productName", "Sin nombre"))
    price_str = data.get("price", data.get("sellPrice", "0"))
    base_price = float(price_str) / 100 if isinstance(price_str, int) else float(price_str)

    selling_price = calc_selling_price(base_price, margin)

    images_raw = data.get("images", data.get("image", []))
    if isinstance(images_raw, str):
        images = [images_raw]
    elif isinstance(images_raw, list):
        images = [img for img in images_raw if isinstance(img, str)]
    else:
        images = []

    category_name = str(data.get("categoryName", data.get("category", "")))
    stock = int(data.get("stock", data.get("inventory", 0)))

    existing = await session.execute(
        select(Product).where(Product.provider_id == str(dropi_id), Product.provider_name == "dropi")
    )
    product = existing.scalar_one_or_none()

    if product:
        product.name = name
        product.base_price = base_price
        product.margin_percentage = margin
        product.selling_price = selling_price
        product.images = images
        product.category = category_name
        product.stock = stock
        product.description = data.get("description", product.description)
    else:
        product = Product(
            name=name,
            description=data.get("description", ""),
            category=category_name,
            images=images,
            base_price=base_price,
            margin_percentage=margin,
            selling_price=selling_price,
            stock=stock,
            provider_id=str(dropi_id),
            provider_name="dropi",
        )
        session.add(product)

    await session.flush()

    # Sync variations
    variations = data.get("variations", data.get("variants", []))
    if variations and isinstance(variations, list):
        for var in variations:
            if not isinstance(var, dict):
                continue
            var_id = var.get("id")
            if not var_id:
                continue

            var_name = var.get("name", var.get("value", ""))
            var_price_str = var.get("price", var.get("sellPrice", 0))
            var_price = float(var_price_str) / 100 if isinstance(var_price_str, int) else float(var_price_str)
            var_stock = int(var.get("stock", var.get("inventory", 0)))

            existing_var = await session.execute(
                select(ProductVariant).where(
                    ProductVariant.product_id == product.id,
                    ProductVariant.sku == str(var_id),
                )
            )
            pv = existing_var.scalar_one_or_none()
            if pv:
                pv.name = var_name
                pv.base_price = var_price
                pv.selling_price = calc_selling_price(var_price, margin) if var_price else None
                pv.stock = var_stock
            else:
                pv = ProductVariant(
                    product_id=product.id,
                    name=var_name,
                    sku=str(var_id),
                    base_price=var_price,
                    selling_price=calc_selling_price(var_price, margin) if var_price else None,
                    stock=var_stock,
                )
                session.add(pv)

    await session.commit()
    return product
