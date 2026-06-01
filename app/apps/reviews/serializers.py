"""Serializadores de Avaliação para o DRF."""
from rest_framework import serializers


class CreateReviewSerializer(serializers.Serializer):
    restaurante_id = serializers.CharField()
    pedido_id = serializers.CharField(required=False)
    nota = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
