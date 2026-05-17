"""
Order service — business logic for orders.

Handles order creation (with price snapshot), status transitions,
and WebSocket notifications.

Refactored to use:
- OrderRepository
- CouponValidator (DRY)
- Domain-specific exceptions
- Dependency injection
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from bson import ObjectId
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.core.enums import OrderStatus, DeliveryMethod
from apps.core.exceptions import InvalidStatusTransition, ResourceNotFoundError
from apps.core.utils import generate_order_number, sanitize_input
from apps.core.validators import CouponValidator
from apps.orders.documents import Order, OrderItem, StatusChange, DeliveryAddress
from apps.orders.repositories import OrderRepository
from apps.restaurants.documents import Restaurant
from apps.restaurants.repositories import RestaurantRepository

logger = logging.getLogger(__name__)


class OrderService:
    """Service containing all order business logic."""

    def __init__(
        self,
        order_repo: OrderRepository | None = None,
        restaurant_repo: RestaurantRepository | None = None,
    ) -> None:
        self.order_repo = order_repo or OrderRepository()
        self.restaurant_repo = restaurant_repo or RestaurantRepository()

    def create_order(self, customer_id: str, data: dict) -> dict:
        """
        Create a new order with price snapshots.

        1. Validates restaurant exists and is active
        2. Validates all products exist and are available
        3. Snapshots current prices
        4. Validates coupon (using CouponValidator — DRY)
        5. Creates order with status 'pending'
        6. Notifies restaurant via WebSocket
        """
        restaurant = self.restaurant_repo.find_active_by_id(data['restaurant_id'])
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')

        # Build product lookup from embedded products
        product_map = {str(p._id): p for p in restaurant.products}

        # Validate and snapshot items
        order_items: list[OrderItem] = []
        subtotal = Decimal('0.00')

        for item_data in data['items']:
            product = product_map.get(item_data['product_id'])
            if not product:
                raise ValueError(f"Produto '{item_data['product_id']}' não encontrado.")
            if not product.is_available:
                raise ValueError(f"Produto '{product.name}' não está disponível.")

            quantity = item_data['quantity']
            price = Decimal(str(product.price))
            item_subtotal = price * quantity

            order_items.append(OrderItem(
                product_id=ObjectId(item_data['product_id']),
                name=product.name,
                price=price,
                quantity=quantity,
                subtotal=item_subtotal,
                image_url=product.image_url,
            ))
            subtotal += item_subtotal

        # Delivery fee
        delivery_fee = Decimal('0.00')
        if data['delivery_method'] == DeliveryMethod.DELIVERY:
            delivery_fee = Decimal(str(restaurant.delivery_fee or 0))

        # Coupon validation (using centralized CouponValidator — DRY)
        discount_amount, coupon_code = CouponValidator.validate_and_calculate(
            coupon_code=data.get('coupon_code', ''),
            coupons=restaurant.coupons,
            cart_total=subtotal,
        )

        # Increment coupon usage if valid
        if coupon_code:
            coupon = next((c for c in restaurant.coupons if c.code == coupon_code), None)
            if coupon:
                coupon.used_count += 1

        # Build delivery address
        delivery_address = None
        if data['delivery_method'] == DeliveryMethod.DELIVERY and data.get('delivery_address'):
            delivery_address = DeliveryAddress(**data['delivery_address'])

        final_total = subtotal + delivery_fee - discount_amount

        order = Order(
            order_number=generate_order_number(),
            customer_id=ObjectId(customer_id),
            restaurant_id=ObjectId(data['restaurant_id']),
            items=order_items,
            total=final_total,
            delivery_fee=delivery_fee,
            discount_amount=discount_amount,
            coupon_code=coupon_code,
            payment_method=data.get('payment_method', 'pix'),
            status=OrderStatus.PENDING,
            status_history=[StatusChange(
                status=OrderStatus.PENDING,
                changed_at=datetime.now(timezone.utc),
                changed_by=ObjectId(customer_id),
            )],
            delivery_method=data['delivery_method'],
            delivery_address=delivery_address,
            notes=sanitize_input(data.get('notes', '')),
        )
        self.order_repo.save(order)
        self.restaurant_repo.save(restaurant)  # Save coupon usage

        logger.info(
            "Order %s created by customer %s for restaurant %s (total=%.2f)",
            order.order_number, customer_id, data['restaurant_id'], float(final_total),
        )

        # Notify restaurant via WebSocket
        self._notify_restaurant(str(restaurant.id), order.to_dict())

        return order.to_dict()

    def update_status(
        self,
        order_id: str,
        new_status: str,
        changed_by: str,
        reason: str | None = None,
    ) -> dict:
        """
        Update order status following the state machine.

        Valid transitions are defined in OrderStatus.valid_transitions().
        """
        order = self.order_repo.find_by_id(order_id)
        if not order:
            raise ResourceNotFoundError('Pedido')

        # Validate transition using enum
        current = OrderStatus(order.status)
        if not current.can_transition_to(new_status):
            raise InvalidStatusTransition(order.status, new_status)

        order.status = new_status
        order.status_history.append(StatusChange(
            status=new_status,
            changed_at=datetime.now(timezone.utc),
            changed_by=ObjectId(changed_by),
        ))

        if new_status == OrderStatus.CANCELLED and reason:
            order.notes = f"{order.notes}\n[CANCELAMENTO]: {sanitize_input(reason)}".strip()

        self.order_repo.save(order)

        logger.info("Order %s status: %s → %s (by %s)", order.order_number, current, new_status, changed_by)

        # Notify client via WebSocket
        self._notify_customer(str(order.id), order.to_dict())

        return order.to_dict()

    def get_order(self, order_id: str) -> dict | None:
        """Get an order by ID."""
        order = self.order_repo.find_by_id(order_id)
        return order.to_dict() if order else None

    def get_order_by_number(self, order_number: str) -> dict | None:
        """Get an order by its human-readable number."""
        order = self.order_repo.find_by_order_number(order_number)
        return order.to_dict() if order else None

    def list_customer_orders(self, customer_id: str, page: int = 1, page_size: int = 10) -> dict:
        """List orders for a customer."""
        result = self.order_repo.find_by_customer(customer_id, page=page, page_size=page_size)
        return result.to_dict()

    def list_restaurant_orders(
        self,
        restaurant_id: str,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List orders for a restaurant."""
        result = self.order_repo.find_by_restaurant(
            restaurant_id, status_filter=status_filter, page=page, page_size=page_size,
        )
        return result.to_dict()

    def validate_coupon(self, restaurant_id: str, code: str, cart_total: float) -> dict:
        """Validate a coupon code and calculate discount (uses CouponValidator — DRY)."""
        restaurant = self.restaurant_repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')

        discount_amount, validated_code = CouponValidator.validate_and_calculate(
            coupon_code=code,
            coupons=restaurant.coupons,
            cart_total=Decimal(str(cart_total)),
        )

        coupon = next((c for c in restaurant.coupons if c.code == validated_code), None)

        return {
            'valid': True,
            'code': validated_code,
            'discount_amount': float(discount_amount),
            'discount_type': coupon.discount_type if coupon else '',
            'description': coupon.description if coupon else '',
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # WebSocket notifications
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _notify_restaurant(self, restaurant_id: str, order_data: dict) -> None:
        """Send new order notification to restaurant via WebSocket."""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{restaurant_id}',
                {'type': 'order.new', 'data': order_data},
            )
        except Exception as e:
            logger.debug("WebSocket notification failed (best-effort): %s", e)

    def _notify_customer(self, order_id: str, order_data: dict) -> None:
        """Send status update to customer via WebSocket."""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'order_{order_id}',
                {'type': 'order.status_update', 'data': order_data},
            )
        except Exception as e:
            logger.debug("WebSocket notification failed (best-effort): %s", e)
