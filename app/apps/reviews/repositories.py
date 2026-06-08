"""
Repositório de Avaliações — acesso centralizado às avaliações embarcadas.
"""
from __future__ import annotations

from bson import ObjectId

from apps.restaurants.documents import Restaurante, AvaliacaoCliente


class RepositorioAvaliacao:
    """Repositório para lidar com avaliações embarcadas no Restaurante."""

    def buscar_por_cliente_e_pedido(self, cliente_id: str, pedido_id: str) -> AvaliacaoCliente | None:
        """Verifica se o cliente já avaliou um pedido específico."""
        # Usa slice no elemMatch ou busca em memória
        restaurante = Restaurante.objects(
            avaliacao__itens__match={'cliente_id': ObjectId(cliente_id), 'pedido_id': ObjectId(pedido_id)}
        ).first()
        
        if restaurante:
            for item in restaurante.avaliacao.itens:
                if str(item.cliente_id) == str(cliente_id) and str(item.pedido_id) == str(pedido_id):
                    return item
        return None

    def buscar_por_id(self, restaurante_id: str, review_id: str) -> AvaliacaoCliente | None:
        """Busca uma avaliação específica pelo seu ID e ID do restaurante."""
        restaurante = Restaurante.objects(
            id=ObjectId(restaurante_id), 
            avaliacao__itens___id=ObjectId(review_id)
        ).first()
        if restaurante:
            for item in restaurante.avaliacao.itens:
                if str(item._id) == str(review_id):
                    return item
        return None

    def listar_por_restaurante(
        self, restaurante_id: str, page: int = 1, page_size: int = 10,
    ) -> dict:
        """Lista avaliações de um restaurante, mais recentes primeiro."""
        restaurante = Restaurante.objects(id=ObjectId(restaurante_id)).first()
        if not restaurante:
            return {'results': [], 'count': 0, 'page': page, 'total_pages': 0, 'page_size': page_size}
        
        # Ordenar por data decrescente (criado_em)
        itens = sorted(restaurante.avaliacao.itens, key=lambda x: x.criado_em, reverse=True)
        total = len(itens)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        results = [item.to_dict() for item in itens[start:end]]
        
        return {
            'results': results,
            'count': total,
            'page': page,
            'total_pages': total_pages,
            'page_size': page_size
        }
