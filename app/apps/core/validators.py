"""
Reusable validators for the Cardápio Online platform.

Centralizes validation logic that was duplicated across services.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from apps.core.exceptions import (
    CouponExpiredError,
    CouponExhaustedError,
    CouponMinOrderError,
    InvalidCouponError,
)

logger = logging.getLogger(__name__)


class CouponValidator:
    """
    Validates and calculates coupon discounts.

    Extracted from OrderService.create_order and OrderService.validate_coupon
    to eliminate code duplication (DRY).
    """

    @staticmethod
    def validate_and_calculate(
        coupon_code: str,
        coupons: list,
        cart_total: Decimal,
    ) -> tuple[Decimal, str]:
        """
        Validate a coupon and calculate the discount amount.

        Args:
            coupon_code: The coupon code to validate
            coupons: List of coupon embedded documents from the restaurant
            cart_total: The cart subtotal (before delivery fee)

        Returns:
            Tuple of (discount_amount, validated_coupon_code)

        Raises:
            InvalidCouponError: If coupon code doesn't exist or is inactive
            CouponExpiredError: If coupon has expired
            CouponMinOrderError: If cart total is below minimum
            CouponExhaustedError: If coupon has reached max uses
        """
        code = coupon_code.strip().upper()
        if not code:
            return Decimal('0.00'), ''

        coupon = next((c for c in coupons if c.codigo == code and c.esta_ativo), None)
        if not coupon:
            raise InvalidCouponError()

        if coupon.valido_ate and coupon.valido_ate < datetime.now(timezone.utc):
            raise CouponExpiredError()

        if coupon.pedido_minimo and cart_total < Decimal(str(coupon.pedido_minimo)):
            raise CouponMinOrderError(float(coupon.pedido_minimo))

        if coupon.max_usos > 0 and coupon.contagem_usos >= coupon.max_usos:
            raise CouponExhaustedError()

        # Calculate discount
        if coupon.tipo_desconto == 'porcentagem':
            discount = cart_total * (Decimal(str(coupon.valor_desconto)) / Decimal('100.0'))
        else:
            discount = Decimal(str(coupon.valor_desconto))

        # Cap discount at cart total
        discount = min(discount, cart_total)

        return discount, code
