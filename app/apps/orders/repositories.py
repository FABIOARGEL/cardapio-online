"""
Repositório de Pedidos — acesso centralizado ao banco para documentos Pedido.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from apps.core.base_repository import BaseRepository, PaginatedResult
from apps.orders.documents import Pedido

logger = logging.getLogger(__name__)


class RepositorioPedido(BaseRepository[Pedido]):
    """Repositório para consultas no documento Pedido."""

    document_class = Pedido

    def buscar_por_numero_pedido(self, numero_pedido: str) -> Pedido | None:
        """Busca um pedido pelo seu número legível."""
        return self.find_one(numero_pedido=numero_pedido)

    def buscar_por_cliente(
        self, cliente_id: str, pagina: int = 1, tamanho_pagina: int = 10,
    ) -> PaginatedResult:
        """Lista pedidos de um cliente."""
        return self.paginate(
            page=pagina, page_size=tamanho_pagina,
            cliente_id=ObjectId(cliente_id),
        )

    def buscar_por_restaurante(
        self,
        restaurante_id: str,
        filtro_status: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 20,
    ) -> PaginatedResult:
        """Lista pedidos de um restaurante com filtro opcional de status."""
        filtros: dict = {'restaurante_id': ObjectId(restaurante_id)}
        if filtro_status:
            filtros['status'] = filtro_status
        return self.paginate(page=pagina, page_size=tamanho_pagina, **filtros)

    def buscar_por_id(self, pedido_id: str) -> Pedido | None:
        """Busca um pedido por ID."""
        return self.find_by_id(pedido_id)

    def salvar(self, pedido: Pedido) -> None:
        """Salva um pedido no banco."""
        pedido.save()

    def obter_estatisticas_dashboard(self, restaurante_id: str) -> dict:
        """
        Obtém estatísticas abrangentes do dashboard usando uma única aggregation.

        Substitui a abordagem anterior de múltiplas iterações em Python.
        """
        rid = ObjectId(restaurante_id)
        agora = datetime.now(timezone.utc)
        inicio_hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = inicio_hoje - timedelta(days=agora.weekday())
        inicio_mes = inicio_hoje.replace(day=1)

        pipeline = [
            {'$match': {'restaurante_id': rid}},
            {'$facet': {
                # Estatísticas de hoje
                'hoje': [
                    {'$match': {'criado_em': {'$gte': inicio_hoje}, 'status': {'$ne': 'cancelado'}}},
                    {'$group': {
                        '_id': None,
                        'receita': {'$sum': {'$toDouble': '$total'}},
                        'contagem': {'$sum': 1},
                    }},
                ],
                # Estatísticas da semana
                'semana': [
                    {'$match': {'criado_em': {'$gte': inicio_semana}, 'status': {'$ne': 'cancelado'}}},
                    {'$group': {
                        '_id': None,
                        'receita': {'$sum': {'$toDouble': '$total'}},
                        'contagem': {'$sum': 1},
                    }},
                ],
                # Estatísticas do mês
                'mes': [
                    {'$match': {'criado_em': {'$gte': inicio_mes}, 'status': {'$ne': 'cancelado'}}},
                    {'$group': {
                        '_id': None,
                        'receita': {'$sum': {'$toDouble': '$total'}},
                        'contagem': {'$sum': 1},
                    }},
                ],
                # Contagem por status
                'contagem_status': [
                    {'$group': {'_id': '$status', 'contagem': {'$sum': 1}}},
                ],
                # Produtos mais vendidos
                'produtos_mais_vendidos': [
                    {'$match': {'status': {'$ne': 'cancelado'}}},
                    {'$unwind': '$itens'},
                    {'$group': {
                        '_id': '$itens.nome',
                        'quantidade': {'$sum': '$itens.quantidade'},
                    }},
                    {'$sort': {'quantidade': -1}},
                    {'$limit': 5},
                    {'$project': {'_id': 0, 'nome': '$_id', 'quantidade': 1}},
                ],
                # Receita diária (últimos 7 dias)
                'receita_diaria': [
                    {'$match': {
                        'criado_em': {'$gte': inicio_hoje - timedelta(days=6)},
                        'status': {'$ne': 'cancelado'},
                    }},
                    {'$group': {
                        '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$criado_em'}},
                        'receita': {'$sum': {'$toDouble': '$total'}},
                        'pedidos': {'$sum': 1},
                    }},
                    {'$sort': {'_id': 1}},
                ],
                # Pedidos recentes
                'pedidos_recentes': [
                    {'$sort': {'criado_em': -1}},
                    {'$limit': 5},
                ],
                # Contagem total
                'contagem_total': [
                    {'$count': 'total'},
                ],
            }},
        ]

        resultado = self.aggregate(pipeline)
        dados = resultado[0] if resultado else {}

        def _extrair_grupo(chave: str) -> dict:
            itens = dados.get(chave, [])
            if itens:
                return {'receita': itens[0].get('receita', 0), 'pedidos': itens[0].get('contagem', 0)}
            return {'receita': 0, 'pedidos': 0}

        hoje = _extrair_grupo('hoje')
        semana = _extrair_grupo('semana')
        mes = _extrair_grupo('mes')

        contagem_status = {s['_id']: s['contagem'] for s in dados.get('contagem_status', [])}

        # Formatar receita diária com nomes dos dias
        nomes_dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        mapa_diario = {d['_id']: d for d in dados.get('receita_diaria', [])}
        receita_diaria = []
        for i in range(6, -1, -1):
            dia = inicio_hoje - timedelta(days=i)
            dia_str = dia.strftime('%Y-%m-%d')
            entrada = mapa_diario.get(dia_str, {})
            receita_diaria.append({
                'data': dia.strftime('%d/%m'),
                'nome_dia': nomes_dias[dia.weekday()],
                'receita': entrada.get('receita', 0),
                'pedidos': entrada.get('pedidos', 0),
            })

        # Formatar pedidos recentes
        pedidos_recentes = []
        for p in dados.get('pedidos_recentes', []):
            pedidos_recentes.append({
                'id': str(p.get('_id', '')),
                'numero_pedido': p.get('numero_pedido', ''),
                'status': p.get('status', ''),
                'total': float(p.get('total', 0)),
                'criado_em': p.get('criado_em', ''),
            })

        contagem_total = dados.get('contagem_total', [])
        total_geral = contagem_total[0]['total'] if contagem_total else 0

        return {
            'hoje': hoje,
            'semana': semana,
            'mes': mes,
            'ticket_medio': round(mes['receita'] / mes['pedidos'], 2) if mes['pedidos'] else 0,
            'contagem_status': contagem_status,
            'produtos_mais_vendidos': dados.get('produtos_mais_vendidos', []),
            'receita_diaria': receita_diaria,
            'pedidos_recentes': pedidos_recentes,
            'total_pedidos_geral': total_geral,
        }

    def obter_historico_pedidos(
        self,
        restaurante_id: str,
        pagina: int = 1,
        tamanho_pagina: int = 20,
        filtro_status: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> dict:
        """Obtém histórico paginado de pedidos com filtros e estatísticas resumidas."""
        filtros: dict = {'restaurante_id': ObjectId(restaurante_id)}

        if filtro_status:
            filtros['status'] = filtro_status
        if data_inicio:
            filtros['criado_em__gte'] = datetime.fromisoformat(data_inicio)
        if data_fim:
            dt_fim = datetime.fromisoformat(data_fim) + timedelta(days=1)
            filtros['criado_em__lt'] = dt_fim

        paginado = self.paginate(page=pagina, page_size=tamanho_pagina, **filtros)

        # Resumo via aggregation
        match_stage: dict = {'restaurante_id': rid} if (rid := ObjectId(restaurante_id)) else {}
        if filtro_status:
            match_stage['status'] = filtro_status
        if data_inicio:
            match_stage.setdefault('criado_em', {})['$gte'] = datetime.fromisoformat(data_inicio)
        if data_fim:
            match_stage.setdefault('criado_em', {})['$lt'] = datetime.fromisoformat(data_fim) + timedelta(days=1)

        pipeline_resumo = [
            {'$match': match_stage},
            {'$facet': {
                'receita': [
                    {'$match': {'status': {'$ne': 'cancelado'}}},
                    {'$group': {'_id': None, 'total': {'$sum': {'$toDouble': '$total'}}}},
                ],
                'entregues': [
                    {'$match': {'status': 'entregue'}},
                    {'$count': 'total'},
                ],
                'cancelados': [
                    {'$match': {'status': 'cancelado'}},
                    {'$count': 'total'},
                ],
            }},
        ]

        resultado_resumo = self.aggregate(pipeline_resumo)
        dados_resumo = resultado_resumo[0] if resultado_resumo else {}

        dados_receita = dados_resumo.get('receita', [])
        dados_entregues = dados_resumo.get('entregues', [])
        dados_cancelados = dados_resumo.get('cancelados', [])

        resultado = paginado.to_dict()
        resultado['resumo'] = {
            'receita_total': dados_receita[0]['total'] if dados_receita else 0,
            'total_entregues': dados_entregues[0]['total'] if dados_entregues else 0,
            'total_cancelados': dados_cancelados[0]['total'] if dados_cancelados else 0,
        }

        return resultado
