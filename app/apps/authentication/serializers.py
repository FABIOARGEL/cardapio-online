"""
Authentication serializers for DRF.

Handles validation of registration, login, and token data.
"""
from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    """Validate user registration data."""
    name = serializers.CharField(min_length=2, max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(choices=['customer', 'owner'], default='customer')

    def validate_email(self, value):
        return value.lower().strip()


class LoginSerializer(serializers.Serializer):
    """Validate login credentials."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class GoogleOAuthSerializer(serializers.Serializer):
    """Validate Google OAuth callback data."""
    code = serializers.CharField(required=False)
    credential = serializers.CharField(required=False)
    role = serializers.ChoiceField(
        choices=['customer', 'owner'],
        default='customer',
        required=False,
    )

    def validate(self, data):
        if not data.get('code') and not data.get('credential'):
            raise serializers.ValidationError(
                "É necessário fornecer 'code' ou 'credential'."
            )
        return data


class TokenRefreshSerializer(serializers.Serializer):
    """Validate token refresh request."""
    refresh_token = serializers.CharField()


class UserResponseSerializer(serializers.Serializer):
    """Serialize user data for API responses."""
    id = serializers.CharField()
    email = serializers.EmailField()
    name = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    role = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class UpdateProfileSerializer(serializers.Serializer):
    """Validate profile update data."""
    name = serializers.CharField(min_length=2, max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class UpdatePasswordSerializer(serializers.Serializer):
    """Validate password update data."""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class AddressSerializer(serializers.Serializer):
    """Validate address data."""
    label = serializers.CharField(max_length=50, required=False, default='Casa')
    street = serializers.CharField(max_length=200)
    number = serializers.CharField(max_length=20)
    complement = serializers.CharField(max_length=100, required=False, allow_blank=True)
    neighborhood = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=2)
    zip_code = serializers.CharField(max_length=10)
    is_default = serializers.BooleanField(required=False, default=False)
