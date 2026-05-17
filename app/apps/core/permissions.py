"""
Custom DRF permissions for Cardápio Online.

Enforces role-based access control:
- IsAuthenticated: Any authenticated user
- IsOwner: Only restaurant owners
- IsCustomer: Only customers
- IsResourceOwner: Ownership verification for specific resources
"""
from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """Allow access only to authenticated users (JWT)."""

    def has_permission(self, request, view):
        return request.user is not None and hasattr(request.user, 'role')


class IsOwner(BasePermission):
    """Allow access only to users with role 'owner'."""

    message = 'Apenas donos de restaurantes podem realizar esta ação.'

    def has_permission(self, request, view):
        if not hasattr(request.user, 'role'):
            return False
        return request.user.role == 'owner'


class IsCustomer(BasePermission):
    """Allow access only to users with role 'customer'."""

    message = 'Apenas clientes podem realizar esta ação.'

    def has_permission(self, request, view):
        if not hasattr(request.user, 'role'):
            return False
        return request.user.role == 'customer'


class IsResourceOwner(BasePermission):
    """
    Verify that the authenticated user owns the resource being accessed.

    The view must implement a `get_owner_id()` method that returns
    the ObjectId of the resource owner.
    """

    message = 'Você não tem permissão para acessar este recurso.'

    def has_permission(self, request, view):
        if not hasattr(request.user, 'id'):
            return False

        if not hasattr(view, 'get_owner_id'):
            return True  # If view doesn't define ownership, allow

        owner_id = view.get_owner_id()
        if owner_id is None:
            return True

        return str(request.user.id) == str(owner_id)
