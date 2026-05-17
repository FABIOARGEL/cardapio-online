"""
Review repository — centralized database access for Review documents.
"""
from __future__ import annotations

from bson import ObjectId

from apps.core.base_repository import BaseRepository, PaginatedResult
from apps.reviews.documents import Review


class ReviewRepository(BaseRepository[Review]):
    """Repository for Review document queries."""

    document_class = Review

    def find_by_customer_and_order(self, customer_id: str, order_id: str) -> Review | None:
        """Check if customer already reviewed a specific order."""
        return self.find_one(
            customer_id=ObjectId(customer_id),
            order_id=ObjectId(order_id),
        )

    def list_by_restaurant(
        self, restaurant_id: str, page: int = 1, page_size: int = 10,
    ) -> PaginatedResult:
        """List reviews for a restaurant, newest first."""
        return self.paginate(
            page=page, page_size=page_size,
            restaurant_id=ObjectId(restaurant_id),
        )

    def get_restaurant_rating(self, restaurant_id: str) -> dict:
        """Calculate average rating for a restaurant via aggregation."""
        pipeline = [
            {'$match': {'restaurant_id': ObjectId(restaurant_id)}},
            {'$group': {
                '_id': None,
                'average': {'$avg': '$rating'},
                'count': {'$sum': 1},
            }},
        ]
        result = self.aggregate(pipeline)
        if result:
            return {
                'average': round(result[0]['average'], 1),
                'count': result[0]['count'],
            }
        return {'average': 0.0, 'count': 0}
