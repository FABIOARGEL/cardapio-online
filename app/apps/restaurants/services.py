"""
Restaurant, Product, Stats, and Coupon services — business logic layer.

Refactored to use:
- Repository pattern (no inline queries)
- Dependency injection
- Centralized enums
- Domain-specific exceptions
- CouponValidator for DRY
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from bson import ObjectId

from apps.core.enums import RestaurantStatus
from apps.core.exceptions import OwnershipError, ResourceNotFoundError
from apps.core.image_service import ImageProcessor
from apps.core.storage import get_upload_service
from apps.core.utils import generate_slug, sanitize_input
from apps.orders.repositories import OrderRepository
from apps.restaurants.documents import (
    BusinessHour,
    Contact,
    Coupon,
    Product,
    Restaurant,
    RestaurantAddress,
)
from apps.restaurants.repositories import RestaurantRepository

logger = logging.getLogger(__name__)


class RestaurantService:
    """Business logic for restaurant CRUD operations."""

    def __init__(
        self,
        restaurant_repo: RestaurantRepository | None = None,
        upload_service=None,
    ) -> None:
        self.repo = restaurant_repo or RestaurantRepository()
        self.upload_service = upload_service or get_upload_service()
        self.image_processor = ImageProcessor()

    def create_restaurant(self, owner_id: str, data: dict, cover_image=None) -> dict:
        """Create a new restaurant with a unique slug."""
        name = sanitize_input(data['name'].strip())
        slug = generate_slug(name)
        base_slug = slug
        counter = 1
        while self.repo.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        cover_url = ''
        if cover_image:
            optimized = self.image_processor.optimize(cover_image)
            cover_url = self.upload_service.upload(optimized, folder='restaurants')

        contact = Contact(**data['contact']) if data.get('contact') else None
        address = RestaurantAddress(**data['address']) if data.get('address') else None
        business_hours = [BusinessHour(**bh) for bh in data.get('business_hours', [])]

        initial_status = data.get('status', RestaurantStatus.ACTIVE)

        restaurant = Restaurant(
            owner_id=ObjectId(owner_id),
            name=name,
            slug=slug,
            description=sanitize_input(data.get('description', '')),
            cover_image_url=cover_url,
            contact=contact,
            address=address,
            business_hours=business_hours,
            status=initial_status,
            delivery_fee=Decimal(str(data.get('delivery_fee', 0))),
        )
        self.repo.save(restaurant)

        logger.info(
            "Restaurant '%s' (id=%s) created by owner %s with status '%s'",
            name, restaurant.id, owner_id, initial_status,
        )
        return restaurant.to_dict()

    def get_restaurant(self, restaurant_id: str) -> dict | None:
        """Get a restaurant by ID with available products."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            return None
        return restaurant.to_dict(include_products=True)

    def get_restaurant_detail_for_owner(self, restaurant_id: str, owner_id: str) -> dict:
        """Get full restaurant data for owner (includes all products + coupons)."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurant.owner_id) != owner_id:
            raise OwnershipError()
        return restaurant.to_dict(include_all_products=True, include_coupons=True)

    def get_restaurant_by_slug(self, slug: str) -> dict | None:
        """Get a restaurant by URL slug with available products."""
        restaurant = self.repo.find_by_slug(slug)
        if not restaurant:
            return None
        return restaurant.to_dict(include_products=True)

    def list_restaurants(
        self, page: int = 1, search: str | None = None, category: str | None = None,
    ) -> dict:
        """List active restaurants for public consumption."""
        result = self.repo.list_active(page=page, search=search, category=category)
        return result.to_dict()

    def list_owner_restaurants(self, owner_id: str) -> list[dict]:
        """List all restaurants owned by a user."""
        restaurants = self.repo.find_by_owner(owner_id)
        return [r.to_dict() for r in restaurants]

    def update_restaurant(
        self,
        restaurant_id: str,
        owner_id: str,
        data: dict,
        cover_image=None,
        logo_image=None,
    ) -> dict:
        """Update restaurant details. Verifies ownership."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurant.owner_id) != owner_id:
            raise OwnershipError()

        if 'name' in data:
            restaurant.name = sanitize_input(data['name'].strip())
        if 'description' in data:
            restaurant.description = sanitize_input(data['description'])
        if 'status' in data:
            restaurant.status = data['status']
        if 'delivery_fee' in data:
            restaurant.delivery_fee = Decimal(str(data['delivery_fee']))
        if 'contact' in data:
            restaurant.contact = Contact(**data['contact'])
        if 'address' in data:
            restaurant.address = RestaurantAddress(**data['address'])
        if 'business_hours' in data:
            restaurant.business_hours = [BusinessHour(**bh) for bh in data['business_hours']]

        if cover_image:
            if restaurant.cover_image_url:
                self.upload_service.delete(restaurant.cover_image_url)
            optimized = self.image_processor.optimize(cover_image)
            restaurant.cover_image_url = self.upload_service.upload(optimized, folder='restaurants')

        if logo_image:
            if restaurant.logo_url:
                self.upload_service.delete(restaurant.logo_url)
            optimized = self.image_processor.optimize(logo_image)
            restaurant.logo_url = self.upload_service.upload(optimized, folder='restaurants')

        self.repo.save(restaurant)
        return restaurant.to_dict()

    def delete_restaurant(self, restaurant_id: str, owner_id: str) -> bool:
        """Delete a restaurant and all associated images."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurant.owner_id) != owner_id:
            raise OwnershipError()

        # Clean up images
        if restaurant.cover_image_url:
            self.upload_service.delete(restaurant.cover_image_url)
        for product in restaurant.products:
            if product.image_url:
                self.upload_service.delete(product.image_url)
            for img_url in (product.images or []):
                self.upload_service.delete(img_url)

        self.repo.delete(restaurant)
        logger.info("Restaurant %s deleted by owner %s", restaurant_id, owner_id)
        return True


class ProductService:
    """Business logic for product management."""

    def __init__(
        self,
        restaurant_repo: RestaurantRepository | None = None,
        upload_service=None,
    ) -> None:
        self.repo = restaurant_repo or RestaurantRepository()
        self.upload_service = upload_service or get_upload_service()
        self.image_processor = ImageProcessor()

    def _get_restaurant_for_owner(self, restaurant_id: str, owner_id: str) -> Restaurant:
        """Helper: fetch restaurant and verify ownership."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurant.owner_id) != owner_id:
            raise OwnershipError()
        return restaurant

    def _find_product(self, restaurant: Restaurant, product_id: str) -> Product:
        """Helper: find embedded product by ID."""
        product = next((p for p in restaurant.products if str(p._id) == product_id), None)
        if not product:
            raise ResourceNotFoundError('Produto')
        return product

    def add_product(self, restaurant_id: str, owner_id: str, data: dict, images=None) -> dict:
        """Add a product to a restaurant."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)

        image_urls = []
        if images:
            for img in images:
                optimized = self.image_processor.optimize(img)
                image_urls.append(self.upload_service.upload(optimized, folder='products'))

        main_image_url = image_urls[0] if image_urls else ''
        product = Product(
            _id=ObjectId(),
            name=sanitize_input(data['name'].strip()),
            description=sanitize_input(data.get('description', '')),
            price=data['price'],
            category=data['category'],
            image_url=main_image_url,
            images=image_urls,
            is_available=data.get('is_available', True),
            sort_order=data.get('sort_order', 0),
            stock=data.get('stock', -1),
        )
        restaurant.products.append(product)
        if product.category not in restaurant.categories:
            restaurant.categories.append(product.category)
        self.repo.save(restaurant)

        logger.info("Product '%s' added to restaurant %s", product.name, restaurant_id)
        return product.to_dict()

    def update_product(
        self, restaurant_id: str, product_id: str, owner_id: str, data: dict, images=None,
    ) -> dict:
        """Update a product within a restaurant."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)
        product = self._find_product(restaurant, product_id)

        for field in ('name', 'description', 'price', 'category', 'is_available', 'sort_order', 'stock'):
            if field in data:
                val = data[field]
                if field in ('name', 'description') and isinstance(val, str):
                    val = sanitize_input(val)
                setattr(product, field, val)

        if images is not None and len(images) > 0:
            # Delete old images
            if product.image_url:
                self.upload_service.delete(product.image_url)
            for img_url in (product.images or []):
                try:
                    self.upload_service.delete(img_url)
                except Exception:
                    pass

            # Upload new images
            new_urls = []
            for img in images:
                optimized = self.image_processor.optimize(img)
                new_urls.append(self.upload_service.upload(optimized, folder='products'))
            product.image_url = new_urls[0] if new_urls else ''
            product.images = new_urls

        product.updated_at = datetime.now(timezone.utc)
        self.repo.save(restaurant)
        return product.to_dict()

    def remove_product(self, restaurant_id: str, product_id: str, owner_id: str) -> bool:
        """Remove a product and its images."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)
        product = self._find_product(restaurant, product_id)

        if product.image_url:
            self.upload_service.delete(product.image_url)
        for img_url in (product.images or []):
            try:
                self.upload_service.delete(img_url)
            except Exception:
                pass

        restaurant.products.remove(product)
        restaurant.categories = list({p.category for p in restaurant.products})
        self.repo.save(restaurant)

        logger.info("Product %s removed from restaurant %s", product_id, restaurant_id)
        return True

    def list_products(
        self, restaurant_id: str, category: str | None = None, available_only: bool = True,
    ) -> list[dict]:
        """List products for a specific restaurant."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')

        products = restaurant.products
        if available_only:
            products = [p for p in products if p.is_available]
        if category:
            products = [p for p in products if p.category == category]
        products.sort(key=lambda p: (p.sort_order, p.name))
        return [p.to_dict() for p in products]

    def list_all_products(
        self,
        page: int = 1,
        page_size: int = 24,
        search: str | None = None,
        category: str | None = None,
    ) -> dict:
        """
        List all available products from active restaurants.

        Uses MongoDB aggregation pipeline for server-side filtering
        and pagination (replaces the old O(n*m) Python-side loop).
        """
        result = self.repo.list_all_products_aggregation(
            page=page, page_size=page_size, search=search, category=category,
        )
        return result.to_dict()


class StatsService:
    """Service to compute dashboard statistics for a restaurant."""

    def __init__(
        self,
        restaurant_repo: RestaurantRepository | None = None,
        order_repo: OrderRepository | None = None,
    ) -> None:
        self.restaurant_repo = restaurant_repo or RestaurantRepository()
        self.order_repo = order_repo or OrderRepository()

    def _verify_ownership(self, restaurant_id: str, owner_id: str) -> Restaurant:
        """Verify restaurant exists and is owned by the user."""
        restaurant = self.restaurant_repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurant.owner_id) != owner_id:
            raise OwnershipError()
        return restaurant

    def get_dashboard_stats(self, restaurant_id: str, owner_id: str) -> dict:
        """
        Get comprehensive dashboard statistics via single aggregation.

        Replaces the old approach of N+1 queries and Python-side iteration.
        """
        restaurant = self._verify_ownership(restaurant_id, owner_id)

        stats = self.order_repo.get_dashboard_stats(restaurant_id)

        # Add product counts from restaurant document
        stats['total_products'] = len(restaurant.products)
        stats['available_products'] = sum(1 for p in restaurant.products if p.is_available)

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
        """Get paginated order history with filters."""
        self._verify_ownership(restaurant_id, owner_id)

        return self.order_repo.get_order_history(
            restaurant_id=restaurant_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            date_from=date_from,
            date_to=date_to,
        )


class CouponService:
    """Service for managing restaurant coupons/promotions."""

    def __init__(self, restaurant_repo: RestaurantRepository | None = None) -> None:
        self.repo = restaurant_repo or RestaurantRepository()

    def _get_restaurant_for_owner(self, restaurant_id: str, owner_id: str) -> Restaurant:
        """Helper: fetch restaurant and verify ownership."""
        restaurant = self.repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')
        if str(restaurant.owner_id) != owner_id:
            raise OwnershipError()
        return restaurant

    def add_coupon(self, restaurant_id: str, owner_id: str, data: dict) -> dict:
        """Add a coupon to a restaurant."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)

        code = data['code'].upper().strip()
        if any(c.code == code for c in restaurant.coupons):
            raise ValueError(f"Cupom '{code}' já existe.")

        coupon = Coupon(
            _id=ObjectId(),
            code=code,
            description=sanitize_input(data.get('description', '')),
            discount_type=data['discount_type'],
            discount_value=Decimal(str(data['discount_value'])),
            min_order=Decimal(str(data.get('min_order', 0))),
            max_uses=data.get('max_uses', 0),
            is_active=data.get('is_active', True),
        )
        if data.get('valid_until'):
            coupon.valid_until = datetime.fromisoformat(data['valid_until'])

        restaurant.coupons.append(coupon)
        self.repo.save(restaurant)

        logger.info("Coupon '%s' added to restaurant %s", code, restaurant_id)
        return coupon.to_dict()

    def update_coupon(
        self, restaurant_id: str, coupon_id: str, owner_id: str, data: dict,
    ) -> dict:
        """Update a coupon within a restaurant."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)

        coupon = next((c for c in restaurant.coupons if str(c._id) == coupon_id), None)
        if not coupon:
            raise ResourceNotFoundError('Cupom')

        for field in ('description', 'discount_type', 'discount_value', 'min_order', 'max_uses', 'is_active'):
            if field in data:
                if field in ('discount_value', 'min_order'):
                    setattr(coupon, field, Decimal(str(data[field])))
                elif field == 'description':
                    coupon.description = sanitize_input(data[field])
                else:
                    setattr(coupon, field, data[field])

        if 'valid_until' in data:
            coupon.valid_until = datetime.fromisoformat(data['valid_until']) if data['valid_until'] else None

        self.repo.save(restaurant)
        return coupon.to_dict()

    def remove_coupon(self, restaurant_id: str, coupon_id: str, owner_id: str) -> bool:
        """Remove a coupon from a restaurant."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)

        coupon = next((c for c in restaurant.coupons if str(c._id) == coupon_id), None)
        if not coupon:
            raise ResourceNotFoundError('Cupom')

        restaurant.coupons.remove(coupon)
        self.repo.save(restaurant)

        logger.info("Coupon %s removed from restaurant %s", coupon_id, restaurant_id)
        return True

    def list_coupons(self, restaurant_id: str, owner_id: str) -> list[dict]:
        """List all coupons for a restaurant."""
        restaurant = self._get_restaurant_for_owner(restaurant_id, owner_id)
        return [c.to_dict() for c in restaurant.coupons]
