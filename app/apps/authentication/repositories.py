"""
User repository — centralized database access for User documents.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.authentication.documents import User
from apps.core.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User document queries."""

    document_class = User

    def find_by_email(self, email: str) -> User | None:
        """Find a user by email (case-insensitive)."""
        return self.find_one(email=email.lower().strip())

    def find_by_google_id(self, google_id: str) -> User | None:
        """Find a user by Google OAuth ID."""
        return self.find_one(google_id=google_id)

    def email_exists(self, email: str) -> bool:
        """Check if an email is already registered."""
        return self.exists(email=email.lower().strip())

    def find_active_by_id(self, user_id: str) -> User | None:
        """Find an active user by ID."""
        user = self.find_by_id(user_id)
        if user and user.is_active:
            return user
        return None

    def increment_failed_attempts(self, user: User) -> None:
        """Atomically increment failed login attempts."""
        User.objects(id=user.id).update_one(
            inc__failed_login_attempts=1,
        )
        user.reload()

    def reset_failed_attempts(self, user: User) -> None:
        """Reset failed login attempts and unlock."""
        User.objects(id=user.id).update_one(
            set__failed_login_attempts=0,
            unset__locked_until=True,
        )
