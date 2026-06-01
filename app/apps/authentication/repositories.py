"""
Repositório de Usuários — acesso centralizado ao banco para documentos Usuario.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.authentication.documents import Usuario
from apps.core.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RepositorioUsuario(BaseRepository[Usuario]):
    """Repositório para consultas no documento Usuario."""

    document_class = Usuario

    def buscar_por_email(self, email: str) -> Usuario | None:
        """Busca um usuário por email (case-insensitive)."""
        return self.find_one(email=email.lower().strip())

    def buscar_por_google_id(self, google_id: str) -> Usuario | None:
        """Busca um usuário pelo ID do Google OAuth."""
        return self.find_one(google_id=google_id)

    def email_existe(self, email: str) -> bool:
        """Verifica se um email já está cadastrado."""
        return self.exists(email=email.lower().strip())

    def buscar_ativo_por_id(self, usuario_id: str) -> Usuario | None:
        """Busca um usuário ativo por ID."""
        user = self.find_by_id(usuario_id)
        if user and user.esta_ativo:
            return user
        return None

    def incrementar_tentativas_falhas(self, usuario: Usuario) -> None:
        """Incrementa atomicamente as tentativas de login falhas."""
        Usuario.objects(id=usuario.id).update_one(
            inc__tentativas_login_falhas=1,
        )
        usuario.reload()

    def resetar_tentativas_falhas(self, usuario: Usuario) -> None:
        """Reseta as tentativas de login falhas e desbloqueia."""
        Usuario.objects(id=usuario.id).update_one(
            set__tentativas_login_falhas=0,
            unset__bloqueado_ate=True,
        )
