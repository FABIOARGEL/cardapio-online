"""
Documentos MongoEngine para a coleção de Avaliações.

Armazena avaliações de clientes para restaurantes e pedidos específicos.
"""
from datetime import datetime, timezone

import mongoengine as me


class Avaliacao(me.Document):
    """
    Documento de avaliação armazenado na coleção MongoDB 'avaliacoes'.

    Cada avaliação vincula um cliente a um restaurante (e opcionalmente a um pedido).
    """
    cliente_id = me.ObjectIdField(required=True)
    nome_cliente = me.StringField(required=True, max_length=100)
    restaurante_id = me.ObjectIdField(required=True)
    pedido_id = me.ObjectIdField()
    nota = me.IntField(required=True, min_value=1, max_value=5)
    comentario = me.StringField(max_length=500)
    criado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'avaliacoes',
        'indexes': [
            {'fields': ['restaurante_id', '-criado_em']},
            {'fields': ['cliente_id']},
            {'fields': ['pedido_id'], 'sparse': True},
        ],
        'ordering': ['-criado_em'],
        'strict': False,
    }

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'cliente_id': str(self.cliente_id),
            'nome_cliente': self.nome_cliente,
            'restaurante_id': str(self.restaurante_id),
            'pedido_id': str(self.pedido_id) if self.pedido_id else None,
            'nota': self.nota,
            'comentario': self.comentario,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }
