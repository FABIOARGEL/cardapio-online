"""
Serializadores de Autenticação para o DRF.
"""
from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    """Valida dados de cadastro de usuário."""
    nome = serializers.CharField(min_length=2, max_length=100)
    email = serializers.EmailField()
    senha = serializers.CharField(min_length=8, write_only=True)
    papel = serializers.ChoiceField(choices=['cliente', 'dono'], default='cliente')

    def validate_email(self, value):
        return value.lower().strip()


class LoginSerializer(serializers.Serializer):
    """Valida credenciais de login."""
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class GoogleOAuthSerializer(serializers.Serializer):
    """Valida dados do callback do Google OAuth."""
    code = serializers.CharField(required=False)
    credential = serializers.CharField(required=False)
    papel = serializers.ChoiceField(
        choices=['cliente', 'dono'],
        default='cliente',
        required=False,
    )

    def validate(self, data):
        if not data.get('code') and not data.get('credential'):
            raise serializers.ValidationError(
                "É necessário fornecer 'code' ou 'credential'."
            )
        return data


class TokenRefreshSerializer(serializers.Serializer):
    """Valida requisição de refresh token."""
    refresh_token = serializers.CharField()


class UserResponseSerializer(serializers.Serializer):
    """Serializa dados do usuário para respostas."""
    id = serializers.CharField()
    email = serializers.EmailField()
    nome = serializers.CharField()
    telefone = serializers.CharField(allow_null=True)
    papel = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)
    esta_ativo = serializers.BooleanField()
    criado_em = serializers.DateTimeField()


class UpdateProfileSerializer(serializers.Serializer):
    """Valida dados de atualização de perfil."""
    nome = serializers.CharField(min_length=2, max_length=100, required=False)
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class UpdatePasswordSerializer(serializers.Serializer):
    """Valida dados de atualização de senha."""
    senha_atual = serializers.CharField(write_only=True)
    nova_senha = serializers.CharField(min_length=8, write_only=True)


class AddressSerializer(serializers.Serializer):
    """Valida dados de endereço."""
    rotulo = serializers.CharField(max_length=50, required=False, default='Casa')
    rua = serializers.CharField(max_length=200)
    numero = serializers.CharField(max_length=20)
    complemento = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bairro = serializers.CharField(max_length=100)
    cidade = serializers.CharField(max_length=100)
    estado = serializers.CharField(max_length=2)
    cep = serializers.CharField(max_length=10)
    padrao = serializers.BooleanField(required=False, default=False)
