"""
Restaurant, Product, and Coupon serializers for DRF.
"""
from rest_framework import serializers


class ContactSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_null=True)
    whatsapp = serializers.CharField(max_length=20, required=False, allow_null=True)


class AddressSerializer(serializers.Serializer):
    street = serializers.CharField(max_length=200)
    number = serializers.CharField(max_length=20)
    complement = serializers.CharField(max_length=100, required=False, allow_null=True)
    neighborhood = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=2)
    zip_code = serializers.CharField(max_length=10)


class BusinessHourSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    open = serializers.CharField(max_length=5, required=False)
    close = serializers.CharField(max_length=5, required=False)
    is_closed = serializers.BooleanField(default=False)


class CreateRestaurantSerializer(serializers.Serializer):
    """Validate restaurant creation data."""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, default='')
    contact = ContactSerializer(required=False)
    address = AddressSerializer(required=False)
    business_hours = BusinessHourSerializer(many=True, required=False, default=list)
    status = serializers.ChoiceField(
        choices=['active', 'inactive'], default='active', required=False,
    )
    delivery_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0,
    )


class UpdateRestaurantSerializer(serializers.Serializer):
    """Validate restaurant update data."""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=500, required=False)
    contact = ContactSerializer(required=False)
    address = AddressSerializer(required=False)
    business_hours = BusinessHourSerializer(many=True, required=False)
    status = serializers.ChoiceField(
        choices=['active', 'inactive'],
        required=False,
    )
    delivery_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False
    )


class CreateProductSerializer(serializers.Serializer):
    """Validate product creation data."""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, default='')
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    category = serializers.ChoiceField(
        choices=['appetizer', 'main', 'dessert', 'drink', 'combo']
    )
    is_available = serializers.BooleanField(default=True)
    sort_order = serializers.IntegerField(default=0, required=False)
    stock = serializers.IntegerField(default=-1, required=False)


class UpdateProductSerializer(serializers.Serializer):
    """Validate product update data."""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=500, required=False)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0.01, required=False
    )
    category = serializers.ChoiceField(
        choices=['appetizer', 'main', 'dessert', 'drink', 'combo'],
        required=False,
    )
    is_available = serializers.BooleanField(required=False)
    sort_order = serializers.IntegerField(required=False)
    stock = serializers.IntegerField(required=False)


class CreateCouponSerializer(serializers.Serializer):
    """Validate coupon creation data."""
    code = serializers.CharField(max_length=30)
    description = serializers.CharField(max_length=200, required=False, default='')
    discount_type = serializers.ChoiceField(choices=['percentage', 'fixed'])
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    min_order = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0, required=False)
    max_uses = serializers.IntegerField(default=0, required=False)
    valid_until = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(default=True)


class UpdateCouponSerializer(serializers.Serializer):
    """Validate coupon update data."""
    description = serializers.CharField(max_length=200, required=False)
    discount_type = serializers.ChoiceField(choices=['percentage', 'fixed'], required=False)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, required=False)
    min_order = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    max_uses = serializers.IntegerField(required=False)
    valid_until = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
