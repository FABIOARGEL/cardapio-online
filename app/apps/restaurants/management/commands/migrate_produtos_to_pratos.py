from django.core.management.base import BaseCommand
import mongoengine as me
from apps.restaurants.documents import Restaurante
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migra o campo "produtos" para "pratos" na coleção de restaurantes do MongoDB.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando migração de "produtos" para "pratos"...')

        collection = Restaurante._get_collection()

        # Update all documents where "produtos" exists
        result = collection.update_many(
            {'produtos': {'$exists': True}},
            {'$rename': {'produtos': 'pratos'}}
        )

        self.stdout.write(self.style.SUCCESS(
            f'Migração concluída! Documentos modificados: {result.modified_count}'
        ))

        # Update index "produtos.categoria" to "pratos.categoria"
        self.stdout.write('Atualizando índices...')
        try:
            collection.drop_index('produtos.categoria_1')
            self.stdout.write('Índice antigo "produtos.categoria_1" removido.')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Não foi possível remover o índice antigo: {e}'))

        # Restoring new index is handled by MongoEngine when the app restarts,
        # but let's make sure by calling ensure_indexes on the modified document.
        Restaurante.ensure_indexes()
        self.stdout.write(self.style.SUCCESS('Índices atualizados com sucesso.'))
