"""
Enums e constantes centralizadas para a plataforma Cardápio Online.

Todas as strings fixas devem referenciar estes enums para segurança
de tipos e autocompletar no IDE.
"""
from __future__ import annotations

from enum import StrEnum


class PerfilUsuario(StrEnum):
    """Tipos de perfil de usuário."""
    CLIENTE = 'cliente'
    DONO = 'dono'


class StatusRestaurante(StrEnum):
    """Status operacional do restaurante."""
    ATIVO = 'ativo'
    INATIVO = 'inativo'
    SUSPENSO = 'suspenso'


class StatusPedido(StrEnum):
    """Estados do ciclo de vida do pedido."""
    PENDENTE = 'pendente'
    CONFIRMADO = 'confirmado'
    PREPARANDO = 'preparando'
    PRONTO = 'pronto'
    ENTREGUE = 'entregue'
    CANCELADO = 'cancelado'

    @classmethod
    def transicoes_validas(cls) -> dict[str, list[str]]:
        """Retorna as transições da máquina de estados."""
        return {
            cls.PENDENTE: [cls.CONFIRMADO, cls.CANCELADO],
            cls.CONFIRMADO: [cls.PREPARANDO, cls.CANCELADO],
            cls.PREPARANDO: [cls.PRONTO, cls.CANCELADO],
            cls.PRONTO: [cls.ENTREGUE, cls.CANCELADO],
            cls.ENTREGUE: [],
            cls.CANCELADO: [],
        }

    def pode_transitar_para(self, alvo: str) -> bool:
        """Verifica se a transição para o status alvo é válida."""
        return alvo in self.transicoes_validas().get(self.value, [])


class MetodoEntrega(StrEnum):
    """Métodos de entrega do pedido."""
    ENTREGA = 'entrega'
    RETIRADA = 'retirada'


class MetodoPagamento(StrEnum):
    """Opções de método de pagamento."""
    PIX = 'pix'
    CARTAO = 'cartao'
    DINHEIRO = 'dinheiro'


class CategoriaProduto(StrEnum):
    """Tipos de categoria de produto."""
    ENTRADA = 'entrada'
    PRINCIPAL = 'principal'
    SOBREMESA = 'sobremesa'
    BEBIDA = 'bebida'
    COMBO = 'combo'


class TipoDesconto(StrEnum):
    """Tipos de desconto de cupom."""
    PORCENTAGEM = 'porcentagem'
    FIXO = 'fixo'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constantes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAX_PRODUTOS_POR_RESTAURANTE = 200
MAX_IMAGENS_POR_PRODUTO = 5
MAX_ENDERECOS_POR_USUARIO = 10
TAMANHO_PAGINA_PADRAO = 12
TAMANHO_PAGINA_MAXIMO = 100
TEMPO_ENTREGA_PADRAO = '40-50 min'
BCRYPT_ROUNDS = 12
MAX_TENTATIVAS_LOGIN = 5
DURACAO_BLOQUEIO_MINUTOS = 15
