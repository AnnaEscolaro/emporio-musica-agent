from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceInfo:
    list_price_brl: float
    effective_price_brl: float
    has_active_promotion: bool
    discount_percent: float | None
    promotion_description: str | None


def compute_effective_price(
    list_price: float,
    active_discounts: list[tuple[float, str]],
) -> PriceInfo:
    """Usa o maior desconto entre promoções ativas (is_active=1) para o produto."""
    if not active_discounts:
        return PriceInfo(
            list_price_brl=list_price,
            effective_price_brl=list_price,
            has_active_promotion=False,
            discount_percent=None,
            promotion_description=None,
        )
    best_pct, best_desc = max(active_discounts, key=lambda x: x[0])
    effective = round(list_price * (1 - best_pct / 100), 2)
    return PriceInfo(
        list_price_brl=list_price,
        effective_price_brl=effective,
        has_active_promotion=True,
        discount_percent=best_pct,
        promotion_description=best_desc,
    )
