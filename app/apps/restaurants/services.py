"""
Serviços de Restaurante, Produto, Estatísticas e Cupom — camada de lógica de negócio.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from bson import ObjectId

from apps.core.enums import StatusRestaurante
from apps.core.exceptions import OwnershipError, ResourceNotFoundError
from apps.core.image_service import ImageProcessor
from apps.core.storage import get_upload_service
from apps.core.utils import generate_slug, sanitize_input
from apps.orders.repositories import RepositorioPedido
from apps.restaurants.documents import (
    HorarioFuncionamento,
    Contato,
    Cupom,
    Produto,
    Restaurante,
    EnderecoRestaurante,
)
from apps.restaurants.repositories import RepositorioRestaurante

logger = logging.getLogger(__name__)


class RestaurantService:
    """Lógica de negócio para operações CRUD de restaurantes."""

    def __init__(
        self,
        restaurant_repo: RepositorioRestaurante | None = None,
        upload_service=None,
    ) -> None:
        self.repo = restaurant_repo or RepositorioRestaurante()
        self.upload_service = upload_service or get_upload_service()
        self.image_processor = ImageProcessor()

    def create_restaurant(self, owner_id: str, data: dict, cover_image=None) -> dict:
        """Cria um novo restaurante com um slug único."""
        nome = sanitize_input(data['nome'].strip())
        slug = generate_slug(nome)
        base_slug = slug
        counter = 1
        while self.repo.slug_existe(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        cover_url = ''
        if cover_image:
            optimized = self.image_processor.optimize(cover_image)
            cover_url = self.upload_service.upload(optimized, folder='restaurants')

        # Mapeia contato e endereço
        dados_contato = None
        if data.get('contato'):
            dados_contato = Contato(
                telefone=data['contato']['telefone'],
                email=data['contato'].get('email'),
                whatsapp=data['contato'].get('whatsapp')
            )

        dados_endereco = None
        if data.get('endereco'):
            dados_endereco = EnderecoRestaurante(
                rua=data['endereco']['rua'],
                numero=data['endereco']['numero'],
                complemento=data['endereco'].get('complemento', ''),
                bairro=data['endereco']['bairro'],
                cidade=data['endereco']['cidade'],
                estado=data['endereco']['estado'],
                cep=data['endereco']['cep']
            )

        horarios_funcionamento = []
        for bh in data.get('horarios_funcionamento', []):
            horarios_funcionamento.append(HorarioFuncionamento(
                dia=bh['dia'],
                abertura=bh.get('abertura'),
                fechamento=bh.get('fechamento'),
                fechado=bh.get('fechado', False)
            ))

        initial_status = data.get('status', StatusRestaurante.ATIVO)

        restaurante = Restaurante(
            dono_id=ObjectId(owner_id),
            nome=nome,
            slug=slug,
            descricao=sanitize_input(data.get('descricao', '')),
            imagem_capa_url=cover_url,
            contato=dados_contato,
            endereco=dados_endereco,
            horarios_funcionamento=horarios_funcionamento,
            status=initial_status,
            taxa_entrega=Decimal(str(data.get('taxa_entrega', 0))),
        )
        self.repo.save(restaurante)

        logger.info(
            "Restaurante '%s' (id=%s) criado pelo dono %s com status '%s'",
            nome, restaurante.id, owner_id, initial_status,
        )
        return restaurante.to_dict()

    def get_restaurant(self, restaurant_id: str) -> dict | None:
        """Busca um restaurante por ID com produtos disponíveis."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            return None
        return restaurante.to_dict(include_products=True)

    def get_restaurant_detail_for_owner(self, restaurant_id: str, owner_id: str) -> dict:
        """Busca dados completos do restaurante para o dono."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurante.dono_id) != owner_id:
            raise OwnershipError()
        return restaurante.to_dict(include_all_products=True, include_coupons=True)

    def get_restaurant_by_slug(self, slug: str) -> dict | None:
        """Busca um restaurante por URL slug."""
        restaurante = self.repo.buscar_por_slug(slug)
        if not restaurante:
            return None
        return restaurante.to_dict(include_products=True)

    def list_restaurants(
        self, page: int = 1, search: str | None = None, category: str | None = None,
    ) -> dict:
        """Lista restaurantes ativos."""
        result = self.repo.listar_ativos(page=page, search=search, category=category)
        return result.to_dict()

    def list_owner_restaurants(self, owner_id: str) -> list[dict]:
        """Lista todos os restaurantes de um usuário."""
        restaurantes = self.repo.buscar_por_dono(owner_id)
        return [r.to_dict() for r in restaurantes]

    def update_restaurant(
        self,
        restaurant_id: str,
        owner_id: str,
        data: dict,
        cover_image=None,
        logo_image=None,
    ) -> dict:
        """Atualiza detalhes do restaurante."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurante.dono_id) != owner_id:
            raise OwnershipError()

        if 'nome' in data:
            restaurante.nome = sanitize_input(data['nome'].strip())
        if 'descricao' in data:
            restaurante.descricao = sanitize_input(data['descricao'])
        if 'status' in data:
            restaurante.status = data['status']
        if 'taxa_entrega' in data:
            restaurante.taxa_entrega = Decimal(str(data['taxa_entrega']))
        if 'contato' in data:
            restaurante.contato = Contato(
                telefone=data['contato']['telefone'],
                email=data['contato'].get('email'),
                whatsapp=data['contato'].get('whatsapp')
            )
        if 'endereco' in data:
            restaurante.endereco = EnderecoRestaurante(
                rua=data['endereco']['rua'],
                numero=data['endereco']['numero'],
                complemento=data['endereco'].get('complemento', ''),
                bairro=data['endereco']['bairro'],
                cidade=data['endereco']['cidade'],
                estado=data['endereco']['estado'],
                cep=data['endereco']['cep']
            )
        if 'horarios_funcionamento' in data:
            restaurante.horarios_funcionamento = [
                HorarioFuncionamento(
                    dia=bh['dia'],
                    abertura=bh.get('abertura'),
                    fechamento=bh.get('fechamento'),
                    fechado=bh.get('fechado', False)
                ) for bh in data['horarios_funcionamento']
            ]

        if cover_image:
            if restaurante.imagem_capa_url:
                self.upload_service.delete(restaurante.imagem_capa_url)
            optimized = self.image_processor.optimize(cover_image)
            restaurante.imagem_capa_url = self.upload_service.upload(optimized, folder='restaurants')

        if logo_image:
            if restaurante.logo_url:
                self.upload_service.delete(restaurante.logo_url)
            optimized = self.image_processor.optimize(logo_image)
            restaurante.logo_url = self.upload_service.upload(optimized, folder='restaurants')

        self.repo.save(restaurante)
        return restaurante.to_dict()

    def delete_restaurant(self, restaurant_id: str, owner_id: str) -> bool:
        """Deleta um restaurante e suas imagens associadas."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurante.dono_id) != owner_id:
            raise OwnershipError()

        # Limpa imagens
        if restaurante.imagem_capa_url:
            self.upload_service.delete(restaurante.imagem_capa_url)
        for produto in restaurante.produtos:
            if produto.imagem_url:
                self.upload_service.delete(produto.imagem_url)
            for img_url in (produto.imagens or []):
                self.upload_service.delete(img_url)

        self.repo.delete(restaurante)
        logger.info("Restaurante %s deletado pelo dono %s", restaurant_id, owner_id)
        return True


class ProductService:
    """Lógica de negócio para gerenciamento de produtos."""

    def __init__(
        self,
        restaurant_repo: RepositorioRestaurante | None = None,
        upload_service=None,
    ) -> None:
        self.repo = restaurant_repo or RepositorioRestaurante()
        self.upload_service = upload_service or get_upload_service()
        self.image_processor = ImageProcessor()

    def _get_restaurant_for_owner(self, restaurant_id: str, owner_id: str) -> Restaurante:
        """Helper: busca restaurante e verifica posse."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurante.dono_id) != owner_id:
            raise OwnershipError()
        return restaurante

    def _find_product(self, restaurante: Restaurante, product_id: str) -> Produto:
        """Helper: encontra produto embarcado por ID."""
        produto = next((p for p in restaurante.produtos if str(p._id) == product_id), None)
        if not produto:
            raise ResourceNotFoundError('Produto')
        return produto

    def add_product(self, restaurant_id: str, owner_id: str, data: dict, images=None) -> dict:
        """Adiciona um produto a um restaurante."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)

        image_urls = []
        if images:
            for img in images:
                optimized = self.image_processor.optimize(img)
                image_urls.append(self.upload_service.upload(optimized, folder='products'))

        main_image_url = image_urls[0] if image_urls else ''
        produto = Produto(
            _id=ObjectId(),
            nome=sanitize_input(data['nome'].strip()),
            descricao=sanitize_input(data.get('descricao', '')),
            preco=data['preco'],
            categoria=data['categoria'],
            imagem_url=main_image_url,
            imagens=image_urls,
            esta_disponivel=data.get('esta_disponivel', True),
            ordem=data.get('ordem', 0),
            estoque=data.get('estoque', -1),
        )
        restaurante.produtos.append(produto)
        if produto.categoria not in restaurante.categorias:
            restaurante.categorias.append(produto.categoria)
        self.repo.save(restaurante)

        logger.info("Produto '%s' adicionado ao restaurante %s", produto.nome, restaurant_id)
        return produto.to_dict()

    def update_product(
        self, restaurant_id: str, product_id: str, owner_id: str, data: dict, images=None,
    ) -> dict:
        """Atualiza um produto dentro de um restaurante."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)
        produto = self._find_product(restaurante, product_id)

        campos_permitidos = [
            'nome', 'descricao', 'preco', 'categoria', 
            'esta_disponivel', 'ordem', 'estoque'
        ]

        for field in campos_permitidos:
            if field in data:
                val = data[field]
                if field in ('nome', 'descricao') and isinstance(val, str):
                    val = sanitize_input(val)
                setattr(produto, field, val)

        if images is not None and len(images) > 0:
            if produto.imagem_url:
                self.upload_service.delete(produto.imagem_url)
            for img_url in (produto.imagens or []):
                try:
                    self.upload_service.delete(img_url)
                except Exception:
                    pass

            new_urls = []
            for img in images:
                optimized = self.image_processor.optimize(img)
                new_urls.append(self.upload_service.upload(optimized, folder='products'))
            produto.imagem_url = new_urls[0] if new_urls else ''
            produto.imagens = new_urls

        produto.atualizado_em = datetime.now(timezone.utc)
        self.repo.save(restaurante)
        return produto.to_dict()

    def remove_product(self, restaurant_id: str, product_id: str, owner_id: str) -> bool:
        """Remove um produto e suas imagens."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)
        produto = self._find_product(restaurante, product_id)

        if produto.imagem_url:
            self.upload_service.delete(produto.imagem_url)
        for img_url in (produto.imagens or []):
            try:
                self.upload_service.delete(img_url)
            except Exception:
                pass

        restaurante.produtos.remove(produto)
        restaurante.categorias = list({p.categoria for p in restaurante.produtos})
        self.repo.save(restaurante)

        logger.info("Produto %s removido do restaurante %s", product_id, restaurant_id)
        return True

    def list_products(
        self, restaurant_id: str, category: str | None = None, available_only: bool = True,
    ) -> list[dict]:
        """Lista produtos para um restaurante específico."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')

        produtos = restaurante.produtos
        if available_only:
            produtos = [p for p in produtos if p.esta_disponivel]
        if category:
            produtos = [p for p in produtos if p.categoria == category]
        produtos.sort(key=lambda p: (p.ordem, p.nome))
        return [p.to_dict() for p in produtos]

    def list_all_products(
        self,
        page: int = 1,
        page_size: int = 24,
        search: str | None = None,
        category: str | None = None,
    ) -> dict:
        """Lista todos os produtos disponíveis via agregação."""
        result = self.repo.listar_todos_produtos_agregacao(
            page=page, page_size=page_size, search=search, category=category,
        )
        return result.to_dict()


class StatsService:
    """Serviço para computar estatísticas do dashboard para um restaurante."""

    def __init__(
        self,
        restaurant_repo: RepositorioRestaurante | None = None,
        order_repo: RepositorioPedido | None = None,
    ) -> None:
        self.restaurant_repo = restaurant_repo or RepositorioRestaurante()
        self.order_repo = order_repo or RepositorioPedido()

    def _verify_ownership(self, restaurant_id: str, owner_id: str) -> Restaurante:
        """Verifica se o restaurante existe e pertence ao dono."""
        restaurante = self.restaurant_repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurante.dono_id) != owner_id:
            raise OwnershipError()
        return restaurante

    def get_dashboard_stats(self, restaurant_id: str, owner_id: str) -> dict:
        """Obtém estatísticas agregadas do dashboard."""
        restaurante = self._verify_ownership(restaurant_id, owner_id)
        stats = self.order_repo.obter_estatisticas_dashboard(restaurant_id)

        stats['total_products'] = len(restaurante.produtos)
        stats['available_products'] = sum(1 for p in restaurante.produtos if p.esta_disponivel)

        return stats

    def get_order_history(
        self,
        restaurant_id: str,
        owner_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """Obtém histórico de pedidos paginado com filtros."""
        self._verify_ownership(restaurant_id, owner_id)

        return self.order_repo.obter_historico_pedidos(
            restaurante_id=restaurant_id,
            pagina=page,
            tamanho_pagina=page_size,
            filtro_status=status_filter,
            data_inicio=date_from,
            data_fim=date_to,
        )


class CouponService:
    """Serviço para gerenciar cupons/promoções do restaurante."""

    def __init__(self, restaurant_repo: RepositorioRestaurante | None = None) -> None:
        self.repo = restaurant_repo or RepositorioRestaurante()

    def _get_restaurant_for_owner(self, restaurant_id: str, owner_id: str) -> Restaurante:
        """Helper: busca restaurante e verifica posse."""
        restaurante = self.repo.find_by_id(restaurant_id)
        if not restaurante:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurante.dono_id) != owner_id:
            raise OwnershipError()
        return restaurante

    def add_coupon(self, restaurant_id: str, owner_id: str, data: dict) -> dict:
        """Adiciona um cupom a um restaurante."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)

        codigo = data['codigo'].upper().strip()
        if any(c.codigo == codigo for c in restaurante.cupons):
            raise ValueError(f"Cupom '{codigo}' já existe.")

        cupom = Cupom(
            _id=ObjectId(),
            codigo=codigo,
            descricao=sanitize_input(data.get('descricao', '')),
            tipo_desconto=data['tipo_desconto'],
            valor_desconto=Decimal(str(data['valor_desconto'])),
            pedido_minimo=Decimal(str(data.get('pedido_minimo', 0))),
            max_usos=data.get('max_usos', 0),
            esta_ativo=data.get('esta_ativo', True),
        )
        if data.get('valido_ate'):
            cupom.valido_ate = datetime.fromisoformat(data['valido_ate'])

        restaurante.cupons.append(cupom)
        self.repo.save(restaurante)

        logger.info("Cupom '%s' adicionado ao restaurante %s", codigo, restaurant_id)
        return cupom.to_dict()

    def update_coupon(
        self, restaurant_id: str, coupon_id: str, owner_id: str, data: dict,
    ) -> dict:
        """Atualiza um cupom dentro de um restaurante."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)

        cupom = next((c for c in restaurante.cupons if str(c._id) == coupon_id), None)
        if not cupom:
            raise ResourceNotFoundError('Cupom')

        campos_permitidos = [
            'descricao', 'tipo_desconto', 'valor_desconto', 
            'pedido_minimo', 'max_usos', 'esta_ativo'
        ]

        for field in campos_permitidos:
            if field in data:
                if field in ('valor_desconto', 'pedido_minimo'):
                    setattr(cupom, field, Decimal(str(data[field])))
                elif field == 'descricao':
                    cupom.descricao = sanitize_input(data[field])
                else:
                    setattr(cupom, field, data[field])

        if 'valido_ate' in data:
            cupom.valido_ate = datetime.fromisoformat(data['valido_ate']) if data['valido_ate'] else None

        self.repo.save(restaurante)
        return cupom.to_dict()

    def remove_coupon(self, restaurant_id: str, coupon_id: str, owner_id: str) -> bool:
        """Remove um cupom de um restaurante."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)

        cupom = next((c for c in restaurante.cupons if str(c._id) == coupon_id), None)
        if not cupom:
            raise ResourceNotFoundError('Cupom')

        restaurante.cupons.remove(cupom)
        self.repo.save(restaurante)

        logger.info("Cupom %s removido do restaurante %s", coupon_id, restaurant_id)
        return True

    def list_coupons(self, restaurant_id: str, owner_id: str) -> list[dict]:
        """Lista todos os cupons de um restaurante."""
        restaurante = self._get_restaurant_for_owner(restaurant_id, owner_id)
        return [c.to_dict() for c in restaurante.cupons]
