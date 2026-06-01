"""
Permissões customizadas DRF para o Cardápio Online.

Controle de acesso baseado em papéis:
- IsAuthenticated: Qualquer usuário autenticado
- IsOwner: Apenas donos de restaurantes
- IsCustomer: Apenas clientes
- IsResourceOwner: Verificação de propriedade para recursos específicos
"""
from rest_framework.permissions import BasePermission

from apps.core.enums import PerfilUsuario


class IsAuthenticated(BasePermission):
    """Permite acesso apenas a usuários autenticados (JWT)."""

    def has_permission(self, request, view):
        return request.user is not None and hasattr(request.user, 'papel')


class IsOwner(BasePermission):
    """Permite acesso apenas a usuários com papel 'dono'."""

    message = 'Apenas donos de restaurantes podem realizar esta ação.'

    def has_permission(self, request, view):
        if not hasattr(request.user, 'papel'):
            return False
        return request.user.papel == PerfilUsuario.DONO


class IsCustomer(BasePermission):
    """Permite acesso apenas a usuários com papel 'cliente'."""

    message = 'Apenas clientes podem realizar esta ação.'

    def has_permission(self, request, view):
        if not hasattr(request.user, 'papel'):
            return False
        return request.user.papel == PerfilUsuario.CLIENTE


class IsResourceOwner(BasePermission):
    """
    Verifica se o usuário autenticado é o dono do recurso acessado.

    A view deve implementar um método `get_owner_id()` que retorna
    o ObjectId do dono do recurso.
    """

    message = 'Você não tem permissão para acessar este recurso.'

    def has_permission(self, request, view):
        if not hasattr(request.user, 'id'):
            return False

        if not hasattr(view, 'get_owner_id'):
            return True  # Se a view não define propriedade, permitir

        owner_id = view.get_owner_id()
        if owner_id is None:
            return True

        return str(request.user.id) == str(owner_id)
