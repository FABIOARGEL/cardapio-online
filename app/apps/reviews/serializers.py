"""Review serializers for DRF."""
from rest_framework import serializers


class CreateReviewSerializer(serializers.Serializer):
    restaurant_id = serializers.CharField()
    order_id = serializers.CharField(required=False)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
