"""
Serviço de Pedidos — lógica de negócio para pedidos.

Gerencia criação de pedidos (com snapshot de preços), transições
de status e notificações WebSocket.

Refatorado para usar:
- RepositorioPedido
- ValidadorCupom (DRY)
- Exceções de domínio
- Injeção de dependência
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from bson import ObjectId
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.core.enums import StatusPedido, MetodoEntrega
from apps.core.exceptions import InvalidStatusTransition, ResourceNotFoundError
from apps.core.utils import gerar_numero_pedido, sanitize_input
from apps.core.validators import CouponValidator
from apps.orders.documents import Pedido, ItemPedido, MudancaStatus, EnderecoEntrega
from apps.orders.repositories import RepositorioPedido
from apps.restaurants.documents import Restaurante
from apps.restaurants.repositories import RepositorioRestaurante

logger = logging.getLogger(__name__)


class ServicoPedido:
    """Serviço contendo toda a lógica de negócio de pedidos."""

    def __init__(
        self,
        repo_pedido: RepositorioPedido | None = None,
        repo_restaurante: RepositorioRestaurante | None = None,
    ) -> None:
        self.repo_pedido = repo_pedido or RepositorioPedido()
        self.repo_restaurante = repo_restaurante or RepositorioRestaurante()

    def criar_pedido(self, cliente_id: str, dados: dict) -> dict:
        """
        Cria um novo pedido com snapshots de preço.

        1. Valida que o restaurante existe e está ativo
        2. Valida que todos os pratos existem e estão disponíveis
        3. Faz snapshot dos preços atuais
        4. Valida cupom (usando ValidadorCupom — DRY)
        5. Cria pedido com status 'pendente'
        6. Notifica restaurante via WebSocket
        """
        restaurante = self.repo_restaurante.buscar_ativo_por_id(dados['restaurante_id'])
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')

        # Construir lookup de pratos embutidos
        mapa_pratos = {str(p._id): p for p in restaurante.pratos}

        # Validar e snapshot dos itens
        itens_pedido: list[ItemPedido] = []
        subtotal = Decimal('0.00')

        for item_dados in dados['itens']:
            prato = mapa_pratos.get(item_dados['prato_id'])
            if not prato:
                raise ValueError(f"Prato '{item_dados['prato_id']}' não encontrado.")
            if not prato.esta_disponivel:
                raise ValueError(f"Prato '{prato.nome}' não está disponível.")

            quantidade = item_dados['quantidade']
            preco = Decimal(str(prato.preco))
            subtotal_item = preco * quantidade

            itens_pedido.append(ItemPedido(
                prato_id=ObjectId(item_dados['prato_id']),
                nome=prato.nome,
                preco=preco,
                quantidade=quantidade,
                subtotal=subtotal_item,
                imagem_url=prato.imagem_url,
            ))
            subtotal += subtotal_item

        # Taxa de entrega
        taxa_entrega = Decimal('0.00')
        if dados['metodo_entrega'] == MetodoEntrega.ENTREGA:
            taxa_entrega = Decimal(str(restaurante.taxa_entrega or 0))

        # Validação de cupom (usando ValidadorCupom centralizado — DRY)
        valor_desconto, codigo_cupom = CouponValidator.validate_and_calculate(
            coupon_code=dados.get('codigo_cupom', ''),
            coupons=restaurante.cupons,
            cart_total=subtotal,
        )

        # Incrementar uso do cupom se válido
        if codigo_cupom:
            cupom = next((c for c in restaurante.cupons if c.codigo == codigo_cupom), None)
            if cupom:
                cupom.contagem_usos += 1

        # Construir endereço de entrega
        endereco_entrega = None
        if dados['metodo_entrega'] == MetodoEntrega.ENTREGA and dados.get('endereco_entrega'):
            endereco_entrega = EnderecoEntrega(**dados['endereco_entrega'])

        total_final = subtotal + taxa_entrega - valor_desconto

        pedido = Pedido(
            numero_pedido=gerar_numero_pedido(),
            cliente_id=ObjectId(cliente_id),
            restaurante_id=ObjectId(dados['restaurante_id']),
            itens=itens_pedido,
            total=total_final,
            taxa_entrega=taxa_entrega,
            valor_desconto=valor_desconto,
            codigo_cupom=codigo_cupom,
            metodo_pagamento=dados.get('metodo_pagamento', 'pix'),
            status=StatusPedido.PENDENTE,
            historico_status=[MudancaStatus(
                status=StatusPedido.PENDENTE,
                alterado_em=datetime.now(timezone.utc),
                alterado_por=ObjectId(cliente_id),
            )],
            metodo_entrega=dados['metodo_entrega'],
            endereco_entrega=endereco_entrega,
            observacoes=sanitize_input(dados.get('observacoes', '')),
        )
        self.repo_pedido.salvar(pedido)
        self.repo_restaurante.save(restaurante)  # Salvar uso do cupom

        logger.info(
            "Pedido %s criado pelo cliente %s para restaurante %s (total=%.2f)",
            pedido.numero_pedido, cliente_id, dados['restaurante_id'], float(total_final),
        )

        # Notificar restaurante via WebSocket
        self._notificar_restaurante(str(restaurante.id), pedido.to_dict())

        return pedido.to_dict()

    def atualizar_status(
        self,
        pedido_id: str,
        novo_status: str,
        alterado_por: str,
        motivo: str | None = None,
    ) -> dict:
        """
        Atualiza o status do pedido seguindo a máquina de estados.

        Transições válidas são definidas em StatusPedido.transicoes_validas().
        """
        pedido = self.repo_pedido.buscar_por_id(pedido_id)
        if not pedido:
            raise ResourceNotFoundError('Pedido')

        # Validar transição usando enum
        atual = StatusPedido(pedido.status)
        if not atual.pode_transitar_para(novo_status):
            raise InvalidStatusTransition(pedido.status, novo_status)

        pedido.status = novo_status
        pedido.historico_status.append(MudancaStatus(
            status=novo_status,
            alterado_em=datetime.now(timezone.utc),
            alterado_por=ObjectId(alterado_por),
        ))

        if novo_status == StatusPedido.CANCELADO and motivo:
            pedido.observacoes = f"{pedido.observacoes}\n[CANCELAMENTO]: {sanitize_input(motivo)}".strip()

        self.repo_pedido.salvar(pedido)

        logger.info("Pedido %s status: %s → %s (por %s)", pedido.numero_pedido, atual, novo_status, alterado_por)

        # Notificar cliente via WebSocket
        self._notificar_cliente(str(pedido.id), pedido.to_dict())

        return pedido.to_dict()

    def buscar_pedido(self, pedido_id: str) -> dict | None:
        """Busca um pedido por ID."""
        pedido = self.repo_pedido.buscar_por_id(pedido_id)
        return pedido.to_dict() if pedido else None

    def buscar_pedido_por_numero(self, numero_pedido: str) -> dict | None:
        """Busca um pedido pelo seu número legível."""
        pedido = self.repo_pedido.buscar_por_numero_pedido(numero_pedido)
        return pedido.to_dict() if pedido else None

    def listar_pedidos_cliente(self, cliente_id: str, pagina: int = 1, tamanho_pagina: int = 10) -> dict:
        """Lista pedidos de um cliente."""
        resultado = self.repo_pedido.buscar_por_cliente(cliente_id, pagina=pagina, tamanho_pagina=tamanho_pagina)
        return resultado.to_dict()

    def listar_pedidos_restaurante(
        self,
        restaurante_id: str,
        filtro_status: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> dict:
        """Lista pedidos de um restaurante."""
        resultado = self.repo_pedido.buscar_por_restaurante(
            restaurante_id, filtro_status=filtro_status, pagina=pagina, tamanho_pagina=tamanho_pagina,
        )
        return resultado.to_dict()

    def validar_cupom(self, restaurante_id: str, codigo: str, total_carrinho: float) -> dict:
        """Valida um código de cupom e calcula desconto (usa ValidadorCupom — DRY)."""
        restaurante = self.repo_restaurante.find_by_id(restaurante_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')

        valor_desconto, codigo_validado = CouponValidator.validate_and_calculate(
            coupon_code=codigo,
            coupons=restaurante.cupons,
            cart_total=Decimal(str(total_carrinho)),
        )

        cupom = next((c for c in restaurante.cupons if c.codigo == codigo_validado), None)

        return {
            'valido': True,
            'codigo': codigo_validado,
            'valor_desconto': float(valor_desconto),
            'tipo_desconto': cupom.tipo_desconto if cupom else '',
            'descricao': cupom.descricao if cupom else '',
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Notificações WebSocket
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _notificar_restaurante(self, restaurante_id: str, dados_pedido: dict) -> None:
        """Envia notificação de novo pedido ao restaurante via WebSocket."""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'restaurant_{restaurante_id}',
                {'type': 'order.new', 'data': dados_pedido},
            )
        except Exception as e:
            logger.debug("Notificação WebSocket falhou (best-effort): %s", e)

    def _notificar_cliente(self, pedido_id: str, dados_pedido: dict) -> None:
        """Envia atualização de status ao cliente via WebSocket."""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'order_{pedido_id}',
                {'type': 'order.status_update', 'data': dados_pedido},
            )
        except Exception as e:
            logger.debug("Notificação WebSocket falhou (best-effort): %s", e)
