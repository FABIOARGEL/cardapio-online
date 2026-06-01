"""
Backend de Autenticação JWT para Django REST Framework.

Lê o header Authorization (Bearer <token>) e valida
o token JWT, injetando o documento de usuário em request.user.
"""
import jwt
from datetime import datetime, timezone

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTAuthentication(BaseAuthentication):
    """
    Classe de autenticação DRF que valida tokens JWT Bearer.

    Uso nas views:
        authentication_classes = [JWTAuthentication]
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith(f'{self.keyword} '):
            return None  # Sem token JWT, permitir outros métodos de auth

        token = auth_header[len(self.keyword) + 1:]

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token expirado.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Token inválido.')

        # Verificar tipo do token
        if payload.get('type') != 'access':
            raise AuthenticationFailed('Tipo de token inválido.')

        # Import aqui para evitar imports circulares
        from apps.authentication.documents import Usuario

        try:
            usuario = Usuario.objects.get(id=payload['user_id'])
        except Usuario.DoesNotExist:
            raise AuthenticationFailed('Usuário não encontrado.')

        if not usuario.esta_ativo:
            raise AuthenticationFailed('Conta desativada.')

        return (usuario, payload)

    def authenticate_header(self, request):
        return self.keyword
