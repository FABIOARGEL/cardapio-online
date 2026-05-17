"""
Authentication service — all business logic for auth.

Handles:
- User registration (email/password)
- Login with credentials
- Google OAuth 2.0 authentication
- JWT token generation and refresh
- Account lockout after failed attempts
- Profile and address management
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from apps.authentication.documents import User, Address
from apps.authentication.repositories import UserRepository
from apps.core.enums import UserRole, BCRYPT_ROUNDS, MAX_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES
from apps.core.exceptions import AccountLockedError, ResourceNotFoundError
from apps.core.utils import validate_password_strength, sanitize_input

logger = logging.getLogger(__name__)


class AuthService:
    """Service containing all authentication business logic."""

    def __init__(self, user_repo: UserRepository | None = None) -> None:
        self.repo = user_repo or UserRepository()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Registration
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def register(self, name: str, email: str, password: str, role: str = 'customer') -> dict:
        """
        Register a new user with email/password.

        Args:
            name: User's full name
            email: Email address (must be unique)
            password: Raw password (will be hashed with bcrypt)
            role: 'customer' or 'owner'

        Returns:
            Dict with user data and JWT tokens

        Raises:
            ValueError: If email already exists or password is weak
        """
        email = email.lower().strip()
        name = sanitize_input(name.strip())

        if self.repo.email_exists(email):
            raise ValueError("Este email já está cadastrado.")

        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)

        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode('utf-8')

        user = User(name=name, email=email, password_hash=password_hash, role=role)
        self.repo.save(user)

        logger.info("New user registered: %s (role=%s)", email, role)

        return {
            'user': user.to_dict(),
            **self._generate_tokens(user),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Login
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def login(self, email: str, password: str) -> dict:
        """
        Authenticate user with email and password.

        Uses constant-time comparison to prevent timing attacks
        for user enumeration.

        Raises:
            ValueError: If credentials are invalid
            AccountLockedError: If account is locked due to failed attempts
        """
        email = email.lower().strip()

        user = self.repo.find_by_email(email)
        if not user:
            # Perform dummy hash to prevent timing-based user enumeration
            bcrypt.checkpw(b'dummy', bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
            raise ValueError("Email ou senha incorretos.")

        self._check_lockout(user)

        if not user.password_hash or not bcrypt.checkpw(
            password.encode('utf-8'),
            user.password_hash.encode('utf-8'),
        ):
            self._record_failed_attempt(user)
            raise ValueError("Email ou senha incorretos.")

        if not user.is_active:
            raise ValueError("Conta desativada.")

        # Reset failed attempts on successful login
        self.repo.reset_failed_attempts(user)

        logger.info("User logged in: %s", email)

        return {
            'user': user.to_dict(),
            **self._generate_tokens(user),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Google OAuth
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def google_oauth(
        self,
        credential: str | None = None,
        code: str | None = None,
        role: str = 'customer',
    ) -> dict:
        """
        Authenticate or register user via Google OAuth 2.0.

        If user doesn't exist, creates a new account with the given role.
        """
        google_user = self._verify_google_token(credential)

        email = google_user['email'].lower()
        google_id = google_user.get('sub', '')

        user = self.repo.find_by_email(email)
        is_new = False

        if not user:
            user = User(
                email=email,
                name=google_user.get('name', email.split('@')[0]),
                avatar_url=google_user.get('picture'),
                google_id=google_id,
                role=role,
            )
            self.repo.save(user)
            is_new = True
            logger.info("New user created via Google: %s (role=%s, id=%s)", email, role, user.id)
        else:
            needs_save = False
            if not user.google_id:
                user.google_id = google_id
                needs_save = True

            if role == UserRole.OWNER and user.role == UserRole.CUSTOMER:
                user.role = UserRole.OWNER
                needs_save = True
                logger.info("User %s upgraded to 'owner' via Google OAuth", email)

            if needs_save:
                self.repo.save(user)

            logger.info("Existing user logged in via Google: %s (role=%s)", email, user.role)

        if not user.is_active:
            raise ValueError("Conta desativada.")

        return {
            'user': user.to_dict(),
            'is_new': is_new,
            **self._generate_tokens(user),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Token Management
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def refresh_token(self, refresh_token_str: str) -> dict:
        """Generate a new access token from a valid refresh token."""
        try:
            payload = jwt.decode(
                refresh_token_str,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token expirado.")
        except jwt.InvalidTokenError:
            raise ValueError("Refresh token inválido.")

        if payload.get('type') != 'refresh':
            raise ValueError("Tipo de token inválido.")

        user = self.repo.find_active_by_id(payload['user_id'])
        if not user:
            raise ValueError("Usuário não encontrado ou desativado.")

        return {'access_token': self._create_access_token(user)}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Profile & Address Management
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def update_profile(self, user_id: str, data: dict) -> dict:
        """Update user profile fields."""
        user = self.repo.find_by_id(user_id)
        if not user:
            raise ResourceNotFoundError('Usuário')

        if 'name' in data:
            user.name = sanitize_input(data['name'].strip())
        if 'phone' in data:
            user.phone = sanitize_input(data['phone'].strip())

        self.repo.save(user)
        return user.to_dict()

    def update_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Update user password after verifying current password."""
        user = self.repo.find_by_id(user_id)
        if not user:
            raise ResourceNotFoundError('Usuário')

        if not user.password_hash or not bcrypt.checkpw(
            current_password.encode('utf-8'),
            user.password_hash.encode('utf-8'),
        ):
            raise ValueError("Senha atual incorreta.")

        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        user.password_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode('utf-8')

        self.repo.save(user)
        return True

    def add_address(self, user_id: str, data: dict) -> dict:
        """Add a new address to user's address list."""
        user = self.repo.find_by_id(user_id)
        if not user:
            raise ResourceNotFoundError('Usuário')

        if data.get('is_default'):
            for addr in user.addresses:
                addr.is_default = False

        new_address = Address(**data)
        user.addresses.append(new_address)
        self.repo.save(user)
        return user.to_dict()

    def remove_address(self, user_id: str, index: int) -> dict:
        """Remove an address by index."""
        user = self.repo.find_by_id(user_id)
        if not user:
            raise ResourceNotFoundError('Usuário')

        if 0 <= index < len(user.addresses):
            user.addresses.pop(index)
            self.repo.save(user)
            return user.to_dict()
        raise ValueError("Endereço não encontrado.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Private helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _generate_tokens(self, user: User) -> dict:
        """Generate both access and refresh JWT tokens."""
        return {
            'access_token': self._create_access_token(user),
            'refresh_token': self._create_refresh_token(user),
        }

    def _create_access_token(self, user: User) -> str:
        """Create a JWT access token."""
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': str(user.id),
            'email': user.email,
            'role': user.role,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(hours=settings.JWT_ACCESS_TOKEN_LIFETIME_HOURS),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _create_refresh_token(self, user: User) -> str:
        """Create a JWT refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': str(user.id),
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _check_lockout(self, user: User) -> None:
        """Check if user account is locked due to too many failed attempts."""
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
            raise AccountLockedError(minutes_remaining=max(remaining, 1))

    def _record_failed_attempt(self, user: User) -> None:
        """Record a failed login attempt. Lock account after MAX_LOGIN_ATTEMPTS failures."""
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

        self.repo.save(user)

    def _verify_google_token(self, credential: str) -> dict:
        """Verify a Google ID token and return the user info."""
        try:
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=60,
            )
            return idinfo
        except ValueError as e:
            raise ValueError(f"Token Google inválido: {e!s}")
