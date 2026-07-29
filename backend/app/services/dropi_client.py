from typing import Optional,  Any

import httpx

from app.config import settings

BASE_URL = settings.dropi_base_url.rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "dropi-integracion-key": settings.dropi_integration_token,
    }


async def _request(method: str, path: str, body: Optional[dict[str, Any]] = None) -> Any:
    url = f"{BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            resp = await client.get(url, headers=_headers())
        else:
            resp = await client.post(url, headers=_headers(), json=body or {})
        if resp.status_code >= 400:
            raise RuntimeError(f"Dropi API error {resp.status_code}: {resp.text}")
        return resp.json()


async def authenticate() -> str:
    """Step 1: login → temporary token (24h)."""
    body = {
        "email": settings.dropi_email,
        "password": settings.dropi_password,
        "white_brand_id": settings.dropi_white_brand_id,
    }
    data = await _request("POST", "/login", body)
    if isinstance(data, dict):
        return data.get("token", "") or data.get("access_token", "")
    raise RuntimeError(f"Dropi login failed: {data}")


async def generate_permanent_token(temp_token: str) -> str:
    """Step 2: exchange temp token for permanent integration token."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/shops/store",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {temp_token}",
            },
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Dropi permanent token error: {resp.text}")
        data = resp.json()
        if isinstance(data, dict):
            return data.get("token", "") or data.get("integration_token", "") or data.get("data", "")
    raise RuntimeError(f"Dropi permanent token failed: {data}")


async def get_categories() -> list:
    data = await _request("GET", "/categories")
    if isinstance(data, dict):
        return data.get("data", data.get("categories", []))
    return data if isinstance(data, list) else []


async def get_products_page(
    page_size: int = 50,
    start_data: int = 0,
    no_count: bool = True,
    keywords: Optional[str] = None,
    category: Optional[list[int]] = None,
    favorite: Optional[bool] = None,
    privated_product: Optional[bool] = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "pageSize": page_size,
        "startData": start_data,
        "no_count": no_count,
    }
    if keywords:
        body["keywords"] = keywords
    if category:
        body["category"] = category
    if favorite is not None:
        body["favorite"] = favorite
    if privated_product is not None:
        body["privated_product"] = privated_product

    data = await _request("POST", "/products/index", body)
    if isinstance(data, dict):
        return data
    return {"data": data if isinstance(data, list) else [], "total": 0}


async def get_product_detail(product_id: int) -> dict[str, Any]:
    data = await _request("GET", f"/products/v2/{product_id}")
    if isinstance(data, dict):
        return data
    return {"data": data}


async def create_order(payload: dict[str, Any]) -> dict[str, Any]:
    data = await _request("POST", "/orders/myorders", payload)
    if isinstance(data, dict):
        return data
    return {"data": data}


async def get_order_by_shop_id(shop_order_id: str) -> dict[str, Any]:
    """Get Dropi order details using our internal order ID."""
    data = await _request("GET", "/orders/myorders")
    if isinstance(data, dict):
        orders = data.get("data", [])
        if isinstance(orders, list):
            for order in orders:
                if order.get("shop_order_id") == shop_order_id:
                    return order
    return {}


async def get_order_by_guide(guide: str) -> dict[str, Any]:
    data = await _request("GET", f"/orders/myorderbyguide/{guide}")
    if isinstance(data, dict):
        return data
    return {"data": data}
