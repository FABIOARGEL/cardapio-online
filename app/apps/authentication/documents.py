"""
Documentos MongoEngine para a coleção de Usuários.

Schema conforme doc 06-modelagem-mongodb.md:
- email (único, indexado)
- senha_hash
- nome
- telefone
- papel (cliente | dono)
- avatar_url
- google_id (único, sparse)
- enderecos (lista embarcada)
- esta_ativo
- criado_em / atualizado_em
"""
from datetime import datetime, timezone

import mongoengine as me


class Endereco(me.EmbeddedDocument):
    """Documento embarcado para endereços do usuário."""
    rotulo = me.StringField(max_length=50, default='Casa')
    rua = me.StringField(max_length=200, required=True)
    numero = me.StringField(max_length=20, required=True)
    complemento = me.StringField(max_length=100)
    bairro = me.StringField(max_length=100, required=True)
    cidade = me.StringField(max_length=100, required=True)
    estado = me.StringField(max_length=2, required=True)
    cep = me.StringField(max_length=10, required=True)
    padrao = me.BooleanField(default=False)

    meta = {'strict': False}


class Usuario(me.Document):
    """
    Documento de usuário armazenado na coleção MongoDB 'usuarios'.

    Suporta dois tipos de usuários:
    - cliente: usuário final que navega e faz pedidos
    - dono: dono de restaurante que gerencia restaurantes e produtos
    """
    OPCOES_PAPEL = ('cliente', 'dono')

    email = me.EmailField(required=True, unique=True)
    senha_hash = me.StringField()
    nome = me.StringField(required=True, min_length=2, max_length=100)
    telefone = me.StringField(max_length=20)
    papel = me.StringField(required=True, choices=OPCOES_PAPEL, default='cliente')
    avatar_url = me.StringField()
    google_id = me.StringField(unique=True, sparse=True)
    enderecos = me.EmbeddedDocumentListField(Endereco, default=list)
    esta_ativo = me.BooleanField(default=True)

    # Rastreamento de tentativas de login para bloqueio de conta
    tentativas_login_falhas = me.IntField(default=0)
    bloqueado_ate = me.DateTimeField()

    criado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    atualizado_em = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'usuarios',
        'indexes': [
            {'fields': ['email'], 'unique': True},
            {'fields': ['google_id'], 'unique': True, 'sparse': True},
            {'fields': ['papel']},
        ],
        'ordering': ['-criado_em'],
        'strict': False,
    }

    def save(self, *args, **kwargs):
        self.atualizado_em = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.email})"

    def to_dict(self) -> dict:
        """Converte usuário para dicionário seguro (sem senha_hash)."""
        return {
            'id': str(self.id),
            'email': self.email,
            'nome': self.nome,
            'telefone': self.telefone,
            'papel': self.papel,
            'avatar_url': self.avatar_url,
            'enderecos': [
                {
                    'rotulo': addr.rotulo,
                    'rua': addr.rua,
                    'numero': addr.numero,
                    'complemento': addr.complemento,
                    'bairro': addr.bairro,
                    'cidade': addr.cidade,
                    'estado': addr.estado,
                    'cep': addr.cep,
                    'padrao': addr.padrao,
                }
                for addr in self.enderecos
            ],
            'esta_ativo': self.esta_ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
        }
