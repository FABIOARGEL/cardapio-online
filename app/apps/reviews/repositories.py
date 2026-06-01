"""
Repositório de Avaliações — acesso centralizado ao banco para documentos Avaliacao.
"""
from __future__ import annotations

from bson import ObjectId

from apps.core.base_repository import BaseRepository, PaginatedResult
from apps.reviews.documents import Avaliacao


class RepositorioAvaliacao(BaseRepository[Avaliacao]):
    """Repositório para consultas no documento Avaliacao."""

    document_class = Avaliacao

    def buscar_por_cliente_e_pedido(self, cliente_id: str, pedido_id: str) -> Avaliacao | None:
        """Verifica se o cliente já avaliou um pedido específico."""
        return self.find_one(
            cliente_id=ObjectId(cliente_id),
            pedido_id=ObjectId(pedido_id),
        )

    def listar_por_restaurante(
        self, restaurante_id: str, page: int = 1, page_size: int = 10,
    ) -> PaginatedResult:
        """Lista avaliações de um restaurante, mais recentes primeiro."""
        return self.paginate(
            page=page, page_size=page_size,
            restaurante_id=ObjectId(restaurante_id),
        )

    def obter_avaliacao_restaurante(self, restaurante_id: str) -> dict:
        """Calcula a nota média de um restaurante via agregação."""
        pipeline = [
            {'$match': {'restaurante_id': ObjectId(restaurante_id)}},
            {'$group': {
                '_id': None,
                'media': {'$avg': '$nota'},
                'contagem': {'$sum': 1},
            }},
        ]
        result = self.aggregate(pipeline)
        if result:
            return {
                'media': round(result[0]['media'], 1),
                'contagem': result[0]['contagem'],
            }
        return {'media': 0.0, 'contagem': 0}
