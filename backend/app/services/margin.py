from typing import Optional

from app.config import settings


def calc_selling_price(base_price: float, margin_percentage: Optional[float] = None) -> float:
    pct = margin_percentage if margin_percentage is not None else settings.default_margin_percentage
    return round(base_price * (1 + pct / 100), 2)


def calc_margin(selling_price: float, cost: float) -> float:
    return round(selling_price - cost, 2)
