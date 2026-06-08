"""
Documentos MongoEngine para as coleções de Restaurante e Produto.

Schema conforme doc 06-modelagem-mongodb.md:
- Restaurante: dono_id, nome, slug, descricao, imagem_capa_url, contato, endereco,
               horarios_funcionamento, produtos (embarcado), cupons (embarcado), status, avaliacao
- Produto: embarcado dentro de Restaurante — nome, descricao, preco, categoria,
           imagem_url, esta_disponivel, ordem, estoque
- Cupom: embarcado dentro de Restaurante — codigo, tipo_desconto, valor_desconto,
         pedido_minimo, max_usos, contagem_usos, valido_de, valido_ate, esta_ativo
"""
from datetime import datetime, timezone
from bson import Decimal128

import mongoengine as me


class Contato(me.EmbeddedDocument):
    """Informações de contato embarcadas de um restaurante."""
    telefone = me.StringField(max_length=20, required=True)
    email = me.EmailField()
    whatsapp = me.StringField(max_length=20)

    meta = {'strict': False}


class Coordenadas(me.EmbeddedDocument):
    """Coordenadas geográficas do restaurante."""
    lat = me.FloatField()
    lng = me.FloatField()

    meta = {'strict': False}


class EnderecoRestaurante(me.EmbeddedDocument):
    """Endereço embarcado de um restaurante."""
    rua = me.StringField(max_length=200, required=True)
    numero = me.StringField(max_length=20, required=True)
    complemento = me.StringField(max_length=100)
    bairro = me.StringField(max_length=100, required=True)
    cidade = me.StringField(max_length=100, required=True)
    estado = me.StringField(max_length=2, required=True)
    cep = me.StringField(max_length=10, required=True)
    coordenadas = me.EmbeddedDocumentField(Coordenadas)

    meta = {'strict': False}


class HorarioFuncionamento(me.EmbeddedDocument):
    """Horário de funcionamento para um dia específico da semana."""
    dia = me.IntField(required=True, min_value=0, max_value=6)  # 0=Dom, 6=Sáb
    abertura = me.StringField(max_length=5)   # HH:MM
    fechamento = me.StringField(max_length=5)  # HH:MM
    fechado = me.BooleanField(default=False)

    meta = {'strict': False}


class AvaliacaoCliente(me.EmbeddedDocument):
    """Avaliação individual de um cliente."""
    _id = me.ObjectIdField(required=True, default=me.ObjectIdField().to_python)
    cliente_id = me.ObjectIdField(required=True)
    nome_cliente = me.StringField(required=True, max_length=100)
    pedido_id = me.ObjectIdField()
    nota = me.IntField(required=True, min_value=1, max_value=5)
    comentario = me.StringField(max_length=500)
    criado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {'strict': False}

    def to_dict(self) -> dict:
        return {
            'id': str(self._id),
            'cliente_id': str(self.cliente_id),
            'nome_cliente': self.nome_cliente,
            'pedido_id': str(self.pedido_id) if self.pedido_id else None,
            'nota': self.nota,
            'comentario': self.comentario,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }


class Avaliacao(me.EmbeddedDocument):
    """Informação agregada de avaliação e lista de itens."""
    media = me.FloatField(default=0.0, min_value=0, max_value=5)
    contagem = me.IntField(default=0, min_value=0)
    itens = me.EmbeddedDocumentListField(AvaliacaoCliente, default=list)

    meta = {'strict': False}


class Produto(me.EmbeddedDocument):
    """
    Produto embarcado dentro de um documento Restaurante.

    Categorias: entrada, principal, sobremesa, bebida, combo
    """
    OPCOES_CATEGORIA = ('entrada', 'principal', 'sobremesa', 'bebida', 'combo')

    _id = me.ObjectIdField(required=True, default=me.ObjectIdField().to_python)
    nome = me.StringField(required=True, max_length=100)
    descricao = me.StringField(max_length=500)
    preco = me.DecimalField(required=True, min_value=0.01, precision=2)
    categoria = me.StringField(required=True, choices=OPCOES_CATEGORIA)
    imagem_url = me.StringField(default='')
    imagens = me.ListField(me.StringField(), max_length=5, default=list)
    esta_disponivel = me.BooleanField(default=True)
    ordem = me.IntField(default=0)
    estoque = me.IntField(default=-1)  # -1 = ilimitado, 0+ = rastreado
    criado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    atualizado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {'strict': False}

    def to_dict(self) -> dict:
        preco_val = 0
        try:
            preco_val = float(self.preco) if self.preco is not None else 0
        except (TypeError, ValueError):
            preco_val = 0
        return {
            'id': str(self._id),
            'nome': self.nome,
            'descricao': self.descricao or '',
            'preco': preco_val,
            'categoria': self.categoria,
            'imagem_url': self.imagem_url or '',
            'imagens': self.imagens or [],
            'esta_disponivel': self.esta_disponivel,
            'ordem': self.ordem,
            'estoque': self.estoque,
        }


class Cupom(me.EmbeddedDocument):
    """
    Cupom/promoção embarcado dentro de um documento Restaurante.

    tipo_desconto: 'porcentagem' ou 'fixo'
    """
    OPCOES_TIPO_DESCONTO = ('porcentagem', 'fixo')

    _id = me.ObjectIdField(required=True, default=me.ObjectIdField().to_python)
    codigo = me.StringField(required=True, max_length=30)
    descricao = me.StringField(max_length=200)
    tipo_desconto = me.StringField(required=True, choices=OPCOES_TIPO_DESCONTO)
    valor_desconto = me.DecimalField(required=True, min_value=0.01, precision=2)
    pedido_minimo = me.DecimalField(default=0, precision=2)
    max_usos = me.IntField(default=0)  # 0 = ilimitado
    contagem_usos = me.IntField(default=0)
    valido_de = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    valido_ate = me.DateTimeField()
    esta_ativo = me.BooleanField(default=True)
    criado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {'strict': False}

    def to_dict(self) -> dict:
        return {
            'id': str(self._id),
            'codigo': self.codigo,
            'descricao': self.descricao,
            'tipo_desconto': self.tipo_desconto,
            'valor_desconto': float(self.valor_desconto) if self.valor_desconto else 0,
            'pedido_minimo': float(self.pedido_minimo) if self.pedido_minimo else 0,
            'max_usos': self.max_usos,
            'contagem_usos': self.contagem_usos,
            'valido_de': self.valido_de.isoformat() if self.valido_de else None,
            'valido_ate': self.valido_ate.isoformat() if self.valido_ate else None,
            'esta_ativo': self.esta_ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }


class Restaurante(me.Document):
    """
    Documento de restaurante armazenado na coleção MongoDB 'restaurantes'.

    Produtos e cupons são embarcados dentro do documento do restaurante para
    performance ótima de leitura (sempre acessados juntos).
    Limite: ~200 produtos por restaurante.
    """
    OPCOES_STATUS = ('ativo', 'inativo', 'suspenso')

    dono_id = me.ObjectIdField(required=True)
    nome = me.StringField(required=True, max_length=100)
    slug = me.StringField(required=True, unique=True, max_length=120)
    descricao = me.StringField(max_length=500)
    imagem_capa_url = me.StringField(default='')
    logo_url = me.StringField()
    contato = me.EmbeddedDocumentField(Contato)
    endereco = me.EmbeddedDocumentField(EnderecoRestaurante)
    horarios_funcionamento = me.EmbeddedDocumentListField(HorarioFuncionamento, default=list)
    categorias = me.ListField(me.StringField(), default=list)
    produtos = me.EmbeddedDocumentListField(Produto, default=list)
    cupons = me.EmbeddedDocumentListField(Cupom, default=list)
    taxa_entrega = me.DecimalField(default=0, precision=2)
    tempo_entrega_estimado = me.StringField(max_length=50, default='40-50 min')
    status = me.StringField(choices=OPCOES_STATUS, default='ativo')
    avaliacao = me.EmbeddedDocumentField(Avaliacao, default=Avaliacao)
    criado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    atualizado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'restaurantes',
        'indexes': [
            {'fields': ['slug'], 'unique': True},
            {'fields': ['dono_id']},
            {'fields': ['status']},
            {
                'fields': ['$nome', '$descricao'],
                'default_language': 'portuguese',
            },
            {'fields': ['produtos.categoria']},
        ],
        'ordering': ['-criado_em'],
        'strict': False,
    }

    def save(self, *args, **kwargs):
        self.atualizado_em = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    def recalcular_avaliacao(self):
        """Recalcula a média e contagem de avaliações a partir da lista de itens."""
        if not self.avaliacao.itens:
            self.avaliacao.media = 0.0
            self.avaliacao.contagem = 0
            return
            
        self.avaliacao.contagem = len(self.avaliacao.itens)
        total_notas = sum(item.nota for item in self.avaliacao.itens)
        self.avaliacao.media = round(total_notas / self.avaliacao.contagem, 1)

    def __str__(self):
        return self.nome

    def to_dict(self, include_products: bool = False, include_all_products: bool = False, include_coupons: bool = False) -> dict:
        """Converte restaurante para dicionário para respostas da API."""
        taxa_entrega_val = 0
        try:
            taxa_entrega_val = float(self.taxa_entrega) if self.taxa_entrega is not None else 0
        except (TypeError, ValueError):
            taxa_entrega_val = 0

        data = {
            'id': str(self.id),
            'dono_id': str(self.dono_id),
            'nome': self.nome,
            'slug': self.slug,
            'descricao': self.descricao or '',
            'imagem_capa_url': self.imagem_capa_url or '',
            'logo_url': self.logo_url or '',
            'taxa_entrega': taxa_entrega_val,
            'tempo_entrega_estimado': self.tempo_entrega_estimado or '40-50 min',
            'contato': {
                'telefone': self.contato.telefone if self.contato else None,
                'email': self.contato.email if self.contato else None,
                'whatsapp': self.contato.whatsapp if self.contato else None,
            } if self.contato else None,
            'endereco': {
                'rua': self.endereco.rua,
                'numero': self.endereco.numero,
                'complemento': self.endereco.complemento,
                'bairro': self.endereco.bairro,
                'cidade': self.endereco.cidade,
                'estado': self.endereco.estado,
                'cep': self.endereco.cep,
            } if self.endereco else None,
            'horarios_funcionamento': [
                {
                    'dia': bh.dia,
                    'abertura': bh.abertura,
                    'fechamento': bh.fechamento,
                    'fechado': bh.fechado,
                }
                for bh in self.horarios_funcionamento
            ],
            'categorias': self.categorias,
            'status': self.status,
            'avaliacao': {
                'media': self.avaliacao.media if self.avaliacao else 0,
                'contagem': self.avaliacao.contagem if self.avaliacao else 0,
            },
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }

        if include_products:
            data['produtos'] = [p.to_dict() for p in self.produtos if p.esta_disponivel]

        if include_all_products:
            data['produtos'] = [p.to_dict() for p in self.produtos]

        if include_coupons:
            data['cupons'] = [c.to_dict() for c in self.cupons]

        return data
