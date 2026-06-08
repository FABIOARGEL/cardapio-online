"""
Serviço de Avaliações — lógica de negócio para avaliações de clientes.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.core.exceptions import ResourceNotFoundError
from apps.core.utils import sanitize_input
from apps.restaurants.repositories import RepositorioRestaurante
from apps.restaurants.documents import AvaliacaoCliente
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

        avaliacao = AvaliacaoCliente(
            cliente_id=ObjectId(customer_id),
            nome_cliente=sanitize_input(customer_name),
            pedido_id=ObjectId(pedido_id) if pedido_id else None,
            nota=nota,
            comentario=sanitize_input(comentario) if comentario else '',
        )
        
        restaurante.avaliacao.itens.append(avaliacao)
        restaurante.recalcular_avaliacao()
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
        # result is directly a dict with pagination
        return self.repo.listar_por_restaurante(restaurant_id, page=page, page_size=page_size)

    def update_review(
        self,
        customer_id: str,
        restaurante_id: str,
        review_id: str,
        nota: int | None = None,
        comentario: str | None = None,
    ) -> dict:
        """Edita uma avaliação e atualiza a média."""
        restaurante = self.restaurant_repo.find_by_id(restaurante_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
            
        review_found = None
        for item in restaurante.avaliacao.itens:
            if str(item._id) == str(review_id):
                if str(item.cliente_id) != str(customer_id):
                    raise ValueError("Você não tem permissão para editar esta avaliação.")
                review_found = item
                break
                
        if not review_found:
            raise ResourceNotFoundError('Avaliação')
            
        if nota is not None:
            review_found.nota = nota
        if comentario is not None:
            review_found.comentario = sanitize_input(comentario)
            
        restaurante.recalcular_avaliacao()
        self.restaurant_repo.save(restaurante)
        
        logger.info("Avaliação editada: review_id=%s, restaurante=%s", review_id, restaurante_id)
        return review_found.to_dict()

    def delete_review(
        self,
        customer_id: str,
        restaurante_id: str,
        review_id: str,
    ) -> bool:
        """Exclui uma avaliação e recalcula a média do restaurante."""
        restaurante = self.restaurant_repo.find_by_id(restaurante_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
            
        index_to_remove = -1
        for i, item in enumerate(restaurante.avaliacao.itens):
            if str(item._id) == str(review_id):
                if str(item.cliente_id) != str(customer_id):
                    raise ValueError("Você não tem permissão para excluir esta avaliação.")
                index_to_remove = i
                break
                
        if index_to_remove == -1:
            raise ResourceNotFoundError('Avaliação')
            
        restaurante.avaliacao.itens.pop(index_to_remove)
        restaurante.recalcular_avaliacao()
        self.restaurant_repo.save(restaurante)
        
        logger.info("Avaliação excluída: review_id=%s, restaurante=%s", review_id, restaurante_id)
        return True
