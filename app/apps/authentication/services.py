"""
Serviço de Autenticação — toda a lógica de negócio para auth.

Responsabilidades:
- Cadastro de usuário (email/senha)
- Login com credenciais
- Autenticação Google OAuth 2.0
- Geração e refresh de tokens JWT
- Bloqueio de conta após tentativas falhas
- Gestão de perfil e endereços
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from apps.authentication.documents import Usuario, Endereco
from apps.authentication.repositories import RepositorioUsuario
from apps.core.enums import PerfilUsuario, BCRYPT_ROUNDS, MAX_TENTATIVAS_LOGIN, DURACAO_BLOQUEIO_MINUTOS
from apps.core.exceptions import AccountLockedError, ResourceNotFoundError
from apps.core.utils import validate_password_strength, sanitize_input

logger = logging.getLogger(__name__)


class AuthService:
    """Serviço contendo toda a lógica de negócio de autenticação."""

    def __init__(self, user_repo: RepositorioUsuario | None = None) -> None:
        self.repo = user_repo or RepositorioUsuario()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Cadastro
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def register(self, nome: str, email: str, senha: str, papel: str = 'cliente') -> dict:
        """
        Cadastra um novo usuário com email/senha.
        """
        email = email.lower().strip()
        nome = sanitize_input(nome.strip())

        # Mapear papel do serializer (em português mas valor amigável do Enum) para o enum real
        mapa_papel = {'cliente': PerfilUsuario.CLIENTE, 'dono': PerfilUsuario.DONO}
        papel = mapa_papel.get(papel, PerfilUsuario.CLIENTE)

        if self.repo.email_existe(email):
            raise ValueError("Este email já está cadastrado.")

        is_valid, error_msg = validate_password_strength(senha)
        if not is_valid:
            raise ValueError(error_msg)

        senha_hash = bcrypt.hashpw(
            senha.encode('utf-8'),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode('utf-8')

        usuario = Usuario(nome=nome, email=email, senha_hash=senha_hash, papel=papel)
        self.repo.save(usuario)

        logger.info("Novo usuário cadastrado: %s (papel=%s)", email, papel)

        return {
            'user': usuario.to_dict(),
            **self._gerar_tokens(usuario),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Login
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def login(self, email: str, senha: str) -> dict:
        """
        Autentica usuário com email e senha.

        Usa comparação de tempo constante para prevenir ataques de timing.
        """
        email = email.lower().strip()

        usuario = self.repo.buscar_por_email(email)
        if not usuario:
            # Hash dummy para prevenir enumeração de usuários por timing
            bcrypt.checkpw(b'dummy', bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
            raise ValueError("Email ou senha incorretos.")

        self._verificar_bloqueio(usuario)

        if not usuario.senha_hash or not bcrypt.checkpw(
            senha.encode('utf-8'),
            usuario.senha_hash.encode('utf-8'),
        ):
            self._registrar_tentativa_falha(usuario)
            raise ValueError("Email ou senha incorretos.")

        if not usuario.esta_ativo:
            raise ValueError("Conta desativada.")

        # Resetar tentativas falhas no login bem-sucedido
        self.repo.resetar_tentativas_falhas(usuario)

        logger.info("Usuário logado: %s", email)

        return {
            'user': usuario.to_dict(),
            **self._gerar_tokens(usuario),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Google OAuth
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def google_oauth(
        self,
        credential: str | None = None,
        code: str | None = None,
        papel: str = 'cliente',
    ) -> dict:
        """
        Autentica ou cadastra usuário via Google OAuth 2.0.

        Se o usuário não existe, cria uma nova conta com o papel informado.
        """
        google_user = self._verificar_token_google(credential)

        email = google_user['email'].lower()
        google_id = google_user.get('sub', '')

        # Mapear papel
        mapa_papel = {'cliente': PerfilUsuario.CLIENTE, 'dono': PerfilUsuario.DONO}
        papel = mapa_papel.get(papel, PerfilUsuario.CLIENTE)

        usuario = self.repo.buscar_por_email(email)
        is_new = False

        if not usuario:
            usuario = Usuario(
                email=email,
                nome=google_user.get('name', email.split('@')[0]),
                avatar_url=google_user.get('picture'),
                google_id=google_id,
                papel=papel,
            )
            self.repo.save(usuario)
            is_new = True
            logger.info("Novo usuário criado via Google: %s (papel=%s, id=%s)", email, papel, usuario.id)
        else:
            needs_save = False
            if not usuario.google_id:
                usuario.google_id = google_id
                needs_save = True

            if papel == PerfilUsuario.DONO and usuario.papel == PerfilUsuario.CLIENTE:
                usuario.papel = PerfilUsuario.DONO
                needs_save = True
                logger.info("Usuário %s promovido para 'dono' via Google OAuth", email)

            if needs_save:
                self.repo.save(usuario)

            logger.info("Usuário existente logado via Google: %s (papel=%s)", email, usuario.papel)

        if not usuario.esta_ativo:
            raise ValueError("Conta desativada.")

        return {
            'user': usuario.to_dict(),
            'is_new': is_new,
            **self._gerar_tokens(usuario),
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Gestão de Tokens
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def refresh_token(self, refresh_token_str: str) -> dict:
        """Gera um novo access token a partir de um refresh token válido."""
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

        usuario = self.repo.buscar_ativo_por_id(payload['user_id'])
        if not usuario:
            raise ValueError("Usuário não encontrado ou desativado.")

        return {'access_token': self._criar_access_token(usuario)}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Gestão de Perfil e Endereços
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def update_profile(self, user_id: str, data: dict) -> dict:
        """Atualiza campos do perfil do usuário."""
        usuario = self.repo.find_by_id(user_id)
        if not usuario:
            raise ResourceNotFoundError('Usuário')

        if 'nome' in data:
            usuario.nome = sanitize_input(data['nome'].strip())
        if 'telefone' in data:
            usuario.telefone = sanitize_input(data['telefone'].strip())

        self.repo.save(usuario)
        return usuario.to_dict()

    def update_password(self, user_id: str, senha_atual: str, nova_senha: str) -> bool:
        """Atualiza a senha do usuário após verificar a senha atual."""
        usuario = self.repo.find_by_id(user_id)
        if not usuario:
            raise ResourceNotFoundError('Usuário')

        if not usuario.senha_hash or not bcrypt.checkpw(
            senha_atual.encode('utf-8'),
            usuario.senha_hash.encode('utf-8'),
        ):
            raise ValueError("Senha atual incorreta.")

        is_valid, error_msg = validate_password_strength(nova_senha)
        if not is_valid:
            raise ValueError(error_msg)

        usuario.senha_hash = bcrypt.hashpw(
            nova_senha.encode('utf-8'),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode('utf-8')

        self.repo.save(usuario)
        return True

    def add_address(self, user_id: str, data: dict) -> dict:
        """Adiciona um novo endereço à lista de endereços do usuário."""
        usuario = self.repo.find_by_id(user_id)
        if not usuario:
            raise ResourceNotFoundError('Usuário')

        # Mapear campos do serializer para o documento
        dados_endereco = {
            'rotulo': data.get('rotulo', 'Casa'),
            'rua': data['rua'],
            'numero': data['numero'],
            'complemento': data.get('complemento', ''),
            'bairro': data['bairro'],
            'cidade': data['cidade'],
            'estado': data['estado'],
            'cep': data['cep'],
            'padrao': data.get('padrao', False),
        }

        if dados_endereco.get('padrao'):
            for addr in usuario.enderecos:
                addr.padrao = False

        novo_endereco = Endereco(**dados_endereco)
        usuario.enderecos.append(novo_endereco)
        self.repo.save(usuario)
        return usuario.to_dict()

    def remove_address(self, user_id: str, index: int) -> dict:
        """Remove um endereço pelo índice."""
        usuario = self.repo.find_by_id(user_id)
        if not usuario:
            raise ResourceNotFoundError('Usuário')

        if 0 <= index < len(usuario.enderecos):
            usuario.enderecos.pop(index)
            self.repo.save(usuario)
            return usuario.to_dict()
        raise ValueError("Endereço não encontrado.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Métodos privados
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _gerar_tokens(self, usuario: Usuario) -> dict:
        """Gera ambos os tokens JWT (access e refresh)."""
        return {
            'access_token': self._criar_access_token(usuario),
            'refresh_token': self._criar_refresh_token(usuario),
        }

    def _criar_access_token(self, usuario: Usuario) -> str:
        """Cria um JWT access token."""
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': str(usuario.id),
            'email': usuario.email,
            'papel': usuario.papel,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(hours=settings.JWT_ACCESS_TOKEN_LIFETIME_HOURS),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _criar_refresh_token(self, usuario: Usuario) -> str:
        """Cria um JWT refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': str(usuario.id),
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _verificar_bloqueio(self, usuario: Usuario) -> None:
        """Verifica se a conta do usuário está bloqueada."""
        if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.now(timezone.utc):
            remaining = (usuario.bloqueado_ate - datetime.now(timezone.utc)).seconds // 60
            raise AccountLockedError(minutes_remaining=max(remaining, 1))

    def _registrar_tentativa_falha(self, usuario: Usuario) -> None:
        """Registra uma tentativa de login falha. Bloqueia a conta após MAX_TENTATIVAS_LOGIN falhas."""
        usuario.tentativas_login_falhas = (usuario.tentativas_login_falhas or 0) + 1

        if usuario.tentativas_login_falhas >= MAX_TENTATIVAS_LOGIN:
            usuario.bloqueado_ate = datetime.now(timezone.utc) + timedelta(minutes=DURACAO_BLOQUEIO_MINUTOS)

        self.repo.save(usuario)

    def _verificar_token_google(self, credential: str) -> dict:
        """Verifica um token de ID do Google e retorna as informações do usuário."""
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
