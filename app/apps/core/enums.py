"""
Centralized enums and constants for the Cardápio Online platform.

All magic strings should reference these enums for type safety
and IDE autocompletion.
"""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    """User role types."""
    CUSTOMER = 'customer'
    OWNER = 'owner'


class RestaurantStatus(StrEnum):
    """Restaurant operational status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'


class OrderStatus(StrEnum):
    """Order lifecycle states."""
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PREPARING = 'preparing'
    READY = 'ready'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

    @classmethod
    def valid_transitions(cls) -> dict[str, list[str]]:
        """Return the state machine transitions."""
        return {
            cls.PENDING: [cls.CONFIRMED, cls.CANCELLED],
            cls.CONFIRMED: [cls.PREPARING, cls.CANCELLED],
            cls.PREPARING: [cls.READY, cls.CANCELLED],
            cls.READY: [cls.DELIVERED, cls.CANCELLED],
            cls.DELIVERED: [],
            cls.CANCELLED: [],
        }

    def can_transition_to(self, target: str) -> bool:
        """Check if transitioning to target status is valid."""
        return target in self.valid_transitions().get(self.value, [])


class DeliveryMethod(StrEnum):
    """Order delivery methods."""
    DELIVERY = 'delivery'
    PICKUP = 'pickup'


class PaymentMethod(StrEnum):
    """Payment method options."""
    PIX = 'pix'
    CARD = 'card'
    CASH = 'cash'


class ProductCategory(StrEnum):
    """Product category types."""
    APPETIZER = 'appetizer'
    MAIN = 'main'
    DESSERT = 'dessert'
    DRINK = 'drink'
    COMBO = 'combo'


class DiscountType(StrEnum):
    """Coupon discount types."""
    PERCENTAGE = 'percentage'
    FIXED = 'fixed'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_PRODUCTS_PER_RESTAURANT = 200
MAX_IMAGES_PER_PRODUCT = 5
MAX_ADDRESSES_PER_USER = 10
DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 100
DEFAULT_DELIVERY_TIME = '40-50 min'
BCRYPT_ROUNDS = 12
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
