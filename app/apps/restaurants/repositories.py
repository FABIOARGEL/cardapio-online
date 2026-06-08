"""
Repositório de Restaurantes — acesso centralizado ao banco para documentos Restaurante.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.core.base_repository import BaseRepository, PaginatedResult
from apps.core.enums import StatusRestaurante
from apps.restaurants.documents import Restaurante

logger = logging.getLogger(__name__)


class RepositorioRestaurante(BaseRepository[Restaurante]):
    """Repositório para consultas no documento Restaurante."""

    document_class = Restaurante

    def buscar_ativo_por_id(self, restaurante_id: str) -> Restaurante | None:
        """Busca um restaurante ativo por ID."""
        return self.find_one(id=restaurante_id, status=StatusRestaurante.ATIVO)

    def buscar_por_dono(self, dono_id: str) -> list[Restaurante]:
        """Busca todos os restaurantes de um usuário."""
        return self.find_many(dono_id=ObjectId(dono_id))

    def buscar_por_slug(self, slug: str) -> Restaurante | None:
        """Busca um restaurante pela URL slug."""
        return self.find_one(slug=slug)

    def buscar_por_id_e_dono(self, restaurante_id: str, dono_id: str) -> Restaurante | None:
        """Busca um restaurante por ID verificando o dono."""
        return self.find_one(id=restaurante_id, dono_id=ObjectId(dono_id))

    def slug_existe(self, slug: str) -> bool:
        """Verifica se uma slug já está em uso."""
        return self.exists(slug=slug)

    def listar_ativos(
        self,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
        category: str | None = None,
    ) -> PaginatedResult:
        """Lista restaurantes ativos com busca e filtros."""
        filters: dict = {'status': StatusRestaurante.ATIVO}
        if search:
            filters['__raw__'] = {'$text': {'$search': search}}
        if category:
            filters['pratos__categoria'] = category

        return self.paginate(page=page, page_size=page_size, **filters)

    def listar_todos_pratos_agregacao(
        self,
        page: int = 1,
        page_size: int = 24,
        search: str | None = None,
        category: str | None = None,
    ) -> PaginatedResult:
        """
        Lista todos os pratos disponíveis de restaurantes ativos usando
        MongoDB aggregation pipeline.
        """
        # Constroi o pipeline de agregação
        pipeline: list[dict] = [
            {'$match': {'status': StatusRestaurante.ATIVO}},
            {'$unwind': '$pratos'},
            {'$match': {'pratos.esta_disponivel': True}},
        ]

        if category and category != 'all':
            pipeline.append({'$match': {'pratos.categoria': category}})

        if search:
            pipeline.append({'$match': {
                'pratos.nome': {'$regex': search, '$options': 'i'},
            }})

        # Conta total de pratos correspondentes
        count_pipeline = pipeline + [{'$count': 'total'}]
        count_result = self.aggregate(count_pipeline)
        total = count_result[0]['total'] if count_result else 0

        # Ordena, pagina e projeta
        pipeline.extend([
            {'$sort': {'pratos.criado_em': -1}},
            {'$skip': (page - 1) * page_size},
            {'$limit': page_size},
            {'$project': {
                '_id': 0,
                'id': {'$toString': '$pratos._id'},
                'nome': '$pratos.nome',
                'descricao': {'$ifNull': ['$pratos.descricao', '']},
                'preco': {'$toDouble': '$pratos.preco'},
                'categoria': '$pratos.categoria',
                'imagem_url': {'$ifNull': ['$pratos.imagem_url', '']},
                'imagens': {'$ifNull': ['$pratos.imagens', []]},
                'esta_disponivel': '$pratos.esta_disponivel',
                'restaurante_id': {'$toString': '$_id'},
                'restaurante_nome': '$nome',
                'restaurante_slug': '$slug',
            }},
        ])

        results = self.aggregate(pipeline)

        total_pages = max(1, (total + page_size - 1) // page_size)
        return PaginatedResult(
            results=results,
            count=total,
            page=page,
            total_pages=total_pages,
            page_size=page_size,
        )
