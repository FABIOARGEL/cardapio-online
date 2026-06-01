"""
Serviço de Avaliações — lógica de negócio para avaliações de clientes.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.core.exceptions import ResourceNotFoundError
from apps.core.utils import sanitize_input
from apps.restaurants.repositories import RepositorioRestaurante
from apps.reviews.documents import Avaliacao
from apps.reviews.repositories import RepositorioAvaliacao

logger = logging.getLogger(__name__)


class ReviewService:
    """Serviço contendo toda a lógica de negócio de avaliações."""

    def __init__(
        self,
        review_repo: RepositorioAvaliacao | None = None,
        restaurant_repo: RepositorioRestaurante | None = None,
    ) -> None:
        self.repo = review_repo or RepositorioAvaliacao()
        self.restaurant_repo = restaurant_repo or RepositorioRestaurante()

    def create_review(
        self,
        customer_id: str,
        customer_name: str,
        restaurante_id: str,
        nota: int,
        comentario: str = '',
        pedido_id: str | None = None,
    ) -> dict:
        """Cria uma nova avaliação e atualiza a média do restaurante."""
        if pedido_id:
            existing = self.repo.buscar_por_cliente_e_pedido(customer_id, pedido_id)
            if existing:
                raise ValueError("Você já avaliou este pedido.")

        restaurante = self.restaurant_repo.find_by_id(restaurante_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')

        avaliacao = Avaliacao(
            cliente_id=ObjectId(customer_id),
            nome_cliente=sanitize_input(customer_name),
            restaurante_id=ObjectId(restaurante_id),
            pedido_id=ObjectId(pedido_id) if pedido_id else None,
            nota=nota,
            comentario=sanitize_input(comentario) if comentario else '',
        )
        self.repo.save(avaliacao)

        # Atualiza a nota do restaurante usando agregação
        rating_data = self.repo.obter_avaliacao_restaurante(restaurante_id)
        restaurante.avaliacao.media = rating_data['media']
        restaurante.avaliacao.contagem = rating_data['contagem']
        self.restaurant_repo.save(restaurante)

        logger.info(
            "Avaliação criada: cliente=%s, restaurante=%s, nota=%d",
            customer_id, restaurante_id, nota,
        )
        return avaliacao.to_dict()

    def list_restaurant_reviews(
        self, restaurant_id: str, page: int = 1, page_size: int = 10,
    ) -> dict:
        """Lista avaliações de um restaurante com paginação."""
        result = self.repo.listar_por_restaurante(restaurant_id, page=page, page_size=page_size)
        return result.to_dict()
