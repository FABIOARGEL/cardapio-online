"""
JWT Authentication backend for Django REST Framework.

Reads the Authorization header (Bearer <token>) and validates
the JWT token, injecting the user document into request.user.
"""
import jwt
from datetime import datetime, timezone

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTAuthentication(BaseAuthentication):
    """
    DRF authentication class that validates JWT Bearer tokens.

    Usage in views:
        authentication_classes = [JWTAuthentication]
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith(f'{self.keyword} '):
            return None  # No JWT token present, allow other auth methods

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

        # Check token type
        if payload.get('type') != 'access':
            raise AuthenticationFailed('Tipo de token inválido.')

        # Import here to avoid circular imports
        from apps.authentication.documents import User

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise AuthenticationFailed('Usuário não encontrado.')

        if not user.is_active:
            raise AuthenticationFailed('Conta desativada.')

        return (user, payload)

    def authenticate_header(self, request):
        return self.keyword
