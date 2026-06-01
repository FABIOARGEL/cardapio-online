"""
Serializadores de Restaurante, Produto e Cupom para o DRF.
"""
from rest_framework import serializers


class ContactSerializer(serializers.Serializer):
    telefone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_null=True)
    whatsapp = serializers.CharField(max_length=20, required=False, allow_null=True)


class AddressSerializer(serializers.Serializer):
    rua = serializers.CharField(max_length=200)
    numero = serializers.CharField(max_length=20)
    complemento = serializers.CharField(max_length=100, required=False, allow_null=True)
    bairro = serializers.CharField(max_length=100)
    cidade = serializers.CharField(max_length=100)
    estado = serializers.CharField(max_length=2)
    cep = serializers.CharField(max_length=10)


class BusinessHourSerializer(serializers.Serializer):
    dia = serializers.IntegerField(min_value=0, max_value=6)
    abertura = serializers.CharField(max_length=5, required=False)
    fechamento = serializers.CharField(max_length=5, required=False)
    fechado = serializers.BooleanField(default=False)


class CreateRestaurantSerializer(serializers.Serializer):
    """Valida criação de restaurante."""
    nome = serializers.CharField(max_length=100)
    descricao = serializers.CharField(max_length=500, required=False, default='')
    contato = ContactSerializer(required=False)
    endereco = AddressSerializer(required=False)
    horarios_funcionamento = BusinessHourSerializer(many=True, required=False, default=list)
    status = serializers.ChoiceField(
        choices=['ativo', 'inativo', 'suspenso'], default='ativo', required=False,
    )
    taxa_entrega = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0,
    )


class UpdateRestaurantSerializer(serializers.Serializer):
    """Valida atualização de restaurante."""
    nome = serializers.CharField(max_length=100, required=False)
    descricao = serializers.CharField(max_length=500, required=False)
    contato = ContactSerializer(required=False)
    endereco = AddressSerializer(required=False)
    horarios_funcionamento = BusinessHourSerializer(many=True, required=False)
    status = serializers.ChoiceField(
        choices=['ativo', 'inativo', 'suspenso'],
        required=False,
    )
    taxa_entrega = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False
    )


class CreateProductSerializer(serializers.Serializer):
    """Valida criação de produto."""
    nome = serializers.CharField(max_length=100)
    descricao = serializers.CharField(max_length=500, required=False, default='')
    preco = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    categoria = serializers.ChoiceField(
        choices=['entrada', 'principal', 'sobremesa', 'bebida', 'combo']
    )
    esta_disponivel = serializers.BooleanField(default=True)
    ordem = serializers.IntegerField(default=0, required=False)
    estoque = serializers.IntegerField(default=-1, required=False)


class UpdateProductSerializer(serializers.Serializer):
    """Valida atualização de produto."""
    nome = serializers.CharField(max_length=100, required=False)
    descricao = serializers.CharField(max_length=500, required=False)
    preco = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0.01, required=False
    )
    categoria = serializers.ChoiceField(
        choices=['entrada', 'principal', 'sobremesa', 'bebida', 'combo'],
        required=False,
    )
    esta_disponivel = serializers.BooleanField(required=False)
    ordem = serializers.IntegerField(required=False)
    estoque = serializers.IntegerField(required=False)


class CreateCouponSerializer(serializers.Serializer):
    """Valida criação de cupom."""
    codigo = serializers.CharField(max_length=30)
    descricao = serializers.CharField(max_length=200, required=False, default='')
    tipo_desconto = serializers.ChoiceField(choices=['porcentagem', 'fixo'])
    valor_desconto = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    pedido_minimo = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0, required=False)
    max_usos = serializers.IntegerField(default=0, required=False)
    valido_ate = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    esta_ativo = serializers.BooleanField(default=True)


class UpdateCouponSerializer(serializers.Serializer):
    """Valida atualização de cupom."""
    descricao = serializers.CharField(max_length=200, required=False)
    tipo_desconto = serializers.ChoiceField(choices=['porcentagem', 'fixo'], required=False)
    valor_desconto = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, required=False)
    pedido_minimo = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    max_usos = serializers.IntegerField(required=False)
    valido_ate = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    esta_ativo = serializers.BooleanField(required=False)
