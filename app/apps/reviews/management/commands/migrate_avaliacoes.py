"""
Comando de migração de dados: Avaliações para Embedded Documents.
Lê a coleção `avaliacoes` e migra para `Restaurante.avaliacao.itens`.
"""
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migra avaliações da coleção separada para os documentos de Restaurante.'

    def handle(self, *args, **options):
        # Conecta ao MongoDB via PyMongo para evitar dependência do MongoEngine (caso deletemos o Document)
        client = MongoClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_NAME]

        avaliacoes_collection = db['avaliacoes']
        restaurantes_collection = db['restaurantes']

        total_avaliacoes = avaliacoes_collection.count_documents({})
        self.stdout.write(self.style.SUCCESS(f'Encontradas {total_avaliacoes} avaliações para migrar.'))

        if total_avaliacoes == 0:
            return

        migradas = 0
        restaurantes_afetados = set()

        # Primeiro agrupar as avaliações por restaurante para minimizar hits no banco
        avaliacoes_por_restaurante = {}
        for avaliacao in avaliacoes_collection.find():
            restaurante_id = str(avaliacao.get('restaurante_id'))
            if restaurante_id not in avaliacoes_por_restaurante:
                avaliacoes_por_restaurante[restaurante_id] = []
            avaliacoes_por_restaurante[restaurante_id].append(avaliacao)

        for restaurante_id, avaliacoes in avaliacoes_por_restaurante.items():
            try:
                restaurante_oid = ObjectId(restaurante_id)
            except Exception:
                self.stdout.write(self.style.WARNING(f'restaurante_id inválido: {restaurante_id}'))
                continue
                
            restaurante = restaurantes_collection.find_one({'_id': restaurante_oid})
            if not restaurante:
                self.stdout.write(self.style.WARNING(f'Restaurante não encontrado para id: {restaurante_id}'))
                continue

            novos_itens = []
            for avaliacao in avaliacoes:
                item = {
                    '_id': avaliacao.get('_id', ObjectId()),
                    'cliente_id': avaliacao.get('cliente_id'),
                    'nome_cliente': avaliacao.get('nome_cliente', 'Cliente Desconhecido'),
                    'pedido_id': avaliacao.get('pedido_id'),
                    'nota': avaliacao.get('nota', 5),
                    'comentario': avaliacao.get('comentario', ''),
                    'criado_em': avaliacao.get('criado_em')
                }
                # Remove nulos se preferir, mas PyMongo/MongoEngine lidam bem.
                novos_itens.append(item)
                migradas += 1

            # Atualizar o documento no banco
            # Vamos substituir a lista inteira (se não tiver outras avaliações, ok)
            # Como a coleção antiga é a fonte de verdade, podemos sobreescrever
            
            contagem = len(novos_itens)
            media = round(sum(i['nota'] for i in novos_itens) / contagem, 1) if contagem > 0 else 0.0

            restaurantes_collection.update_one(
                {'_id': restaurante_oid},
                {'$set': {
                    'avaliacao.itens': novos_itens,
                    'avaliacao.contagem': contagem,
                    'avaliacao.media': media
                }}
            )
            restaurantes_afetados.add(restaurante_id)

        self.stdout.write(self.style.SUCCESS(
            f'Migração concluída! {migradas} avaliações migradas para {len(restaurantes_afetados)} restaurantes.'
        ))
        
        self.stdout.write(self.style.WARNING(
            'Nota: A coleção `avaliacoes` não foi deletada. Verifique os dados no sistema e delete manualmente quando estiver seguro.'
        ))
