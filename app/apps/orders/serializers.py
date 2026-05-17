"""Order serializers for DRF."""
from __future__ import annotations

from rest_framework import serializers


class OrderItemSerializer(serializers.Serializer):
    """Validate individual order items."""
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class CreateOrderSerializer(serializers.Serializer):
    """Validate order creation data."""
    restaurant_id = serializers.CharField()
    items = OrderItemSerializer(many=True, min_length=1)
    delivery_method = serializers.ChoiceField(choices=['delivery', 'pickup'])
    payment_method = serializers.ChoiceField(choices=['pix', 'card', 'cash'], default='pix')
    coupon_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    delivery_address = serializers.DictField(required=False)

    def validate_items(self, value):
        """BUG FIX: This was previously inside ValidateCouponSerializer and never executed."""
        if not value:
            raise serializers.ValidationError("Pedido deve conter ao menos 1 item.")
        return value

    def validate(self, data):
        """Validate delivery address is provided for delivery orders."""
        if data.get('delivery_method') == 'delivery' and not data.get('delivery_address'):
            raise serializers.ValidationError(
                {'delivery_address': 'Endereço de entrega é obrigatório para delivery.'}
            )
        return data


class UpdateOrderStatusSerializer(serializers.Serializer):
    """Validate status update requests."""
    status = serializers.ChoiceField(
        choices=['confirmed', 'preparing', 'ready', 'delivered', 'cancelled']
    )
    cancellation_reason = serializers.CharField(max_length=500, required=False)

    def validate(self, data):
        if data['status'] == 'cancelled' and not data.get('cancellation_reason'):
            raise serializers.ValidationError(
                {'cancellation_reason': 'Motivo é obrigatório para cancelamento.'}
            )
        return data


class ValidateCouponSerializer(serializers.Serializer):
    """Validate coupon validation requests."""
    restaurant_id = serializers.CharField()
    code = serializers.CharField()
    cart_total = serializers.DecimalField(max_digits=10, decimal_places=2)
