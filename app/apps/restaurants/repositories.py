"""
Restaurant repository — centralized database access for Restaurant documents.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.core.base_repository import BaseRepository, PaginatedResult
from apps.core.enums import RestaurantStatus
from apps.restaurants.documents import Restaurant

logger = logging.getLogger(__name__)


class RestaurantRepository(BaseRepository[Restaurant]):
    """Repository for Restaurant document queries."""

    document_class = Restaurant

    def find_active_by_id(self, restaurant_id: str) -> Restaurant | None:
        """Find an active restaurant by ID."""
        return self.find_one(id=restaurant_id, status=RestaurantStatus.ACTIVE)

    def find_by_owner(self, owner_id: str) -> list[Restaurant]:
        """Find all restaurants owned by a user."""
        return self.find_many(owner_id=ObjectId(owner_id))

    def find_by_slug(self, slug: str) -> Restaurant | None:
        """Find a restaurant by URL slug."""
        return self.find_one(slug=slug)

    def find_by_id_and_owner(self, restaurant_id: str, owner_id: str) -> Restaurant | None:
        """Find a restaurant by ID verifying ownership."""
        return self.find_one(id=restaurant_id, owner_id=ObjectId(owner_id))

    def slug_exists(self, slug: str) -> bool:
        """Check if a slug is already taken."""
        return self.exists(slug=slug)

    def list_active(
        self,
        page: int = 1,
        page_size: int = 12,
        search: str | None = None,
        category: str | None = None,
    ) -> PaginatedResult:
        """List active restaurants with search and filtering."""
        filters: dict = {'status': RestaurantStatus.ACTIVE}
        if search:
            filters['__raw__'] = {'$text': {'$search': search}}
        if category:
            filters['products__category'] = category

        return self.paginate(page=page, page_size=page_size, **filters)

    def list_all_products_aggregation(
        self,
        page: int = 1,
        page_size: int = 24,
        search: str | None = None,
        category: str | None = None,
    ) -> PaginatedResult:
        """
        List all available products from active restaurants using
        MongoDB aggregation pipeline (server-side filtering).

        This replaces the previous O(n*m) Python-side iteration.
        """
        # Build the aggregation pipeline
        pipeline: list[dict] = [
            {'$match': {'status': RestaurantStatus.ACTIVE}},
            {'$unwind': '$products'},
            {'$match': {'products.is_available': True}},
        ]

        if category and category != 'all':
            pipeline.append({'$match': {'products.category': category}})

        if search:
            pipeline.append({'$match': {
                'products.name': {'$regex': search, '$options': 'i'},
            }})

        # Count total matching products
        count_pipeline = pipeline + [{'$count': 'total'}]
        count_result = self.aggregate(count_pipeline)
        total = count_result[0]['total'] if count_result else 0

        # Sort, paginate, and project
        pipeline.extend([
            {'$sort': {'products.created_at': -1}},
            {'$skip': (page - 1) * page_size},
            {'$limit': page_size},
            {'$project': {
                '_id': 0,
                'id': {'$toString': '$products._id'},
                'name': '$products.name',
                'description': {'$ifNull': ['$products.description', '']},
                'price': {'$toDouble': '$products.price'},
                'category': '$products.category',
                'image_url': {'$ifNull': ['$products.image_url', '']},
                'images': {'$ifNull': ['$products.images', []]},
                'is_available': '$products.is_available',
                'restaurant_id': {'$toString': '$_id'},
                'restaurant_name': '$name',
                'restaurant_slug': '$slug',
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
