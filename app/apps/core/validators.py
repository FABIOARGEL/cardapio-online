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

        coupon = next((c for c in coupons if c.code == code and c.is_active), None)
        if not coupon:
            raise InvalidCouponError()

        if coupon.valid_until and coupon.valid_until < datetime.now(timezone.utc):
            raise CouponExpiredError()

        if coupon.min_order and cart_total < Decimal(str(coupon.min_order)):
            raise CouponMinOrderError(float(coupon.min_order))

        if coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
            raise CouponExhaustedError()

        # Calculate discount
        if coupon.discount_type == 'percentage':
            discount = cart_total * (Decimal(str(coupon.discount_value)) / Decimal('100.0'))
        else:
            discount = Decimal(str(coupon.discount_value))

        # Cap discount at cart total
        discount = min(discount, cart_total)

        return discount, code
