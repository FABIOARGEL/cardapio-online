"""
Review service — business logic for customer reviews.

Refactored to use ReviewRepository.
"""
from __future__ import annotations

import logging

from bson import ObjectId

from apps.core.exceptions import ResourceNotFoundError
from apps.core.utils import sanitize_input
from apps.restaurants.repositories import RestaurantRepository
from apps.reviews.documents import Review
from apps.reviews.repositories import ReviewRepository

logger = logging.getLogger(__name__)


class ReviewService:
    """Service containing all review business logic."""

    def __init__(
        self,
        review_repo: ReviewRepository | None = None,
        restaurant_repo: RestaurantRepository | None = None,
    ) -> None:
        self.repo = review_repo or ReviewRepository()
        self.restaurant_repo = restaurant_repo or RestaurantRepository()

    def create_review(
        self,
        customer_id: str,
        customer_name: str,
        restaurant_id: str,
        rating: int,
        comment: str = '',
        order_id: str | None = None,
    ) -> dict:
        """Create a new review and update restaurant rating average."""
        # Check duplicate review for same order
        if order_id:
            existing = self.repo.find_by_customer_and_order(customer_id, order_id)
            if existing:
                raise ValueError("Você já avaliou este pedido.")

        restaurant = self.restaurant_repo.find_by_id(restaurant_id)
        if not restaurant:
            raise ResourceNotFoundError('Restaurante')

        review = Review(
            customer_id=ObjectId(customer_id),
            customer_name=sanitize_input(customer_name),
            restaurant_id=ObjectId(restaurant_id),
            order_id=ObjectId(order_id) if order_id else None,
            rating=rating,
            comment=sanitize_input(comment) if comment else '',
        )
        self.repo.save(review)

        # Update restaurant rating using aggregation (more accurate than Python-side)
        rating_data = self.repo.get_restaurant_rating(restaurant_id)
        restaurant.rating.average = rating_data['average']
        restaurant.rating.count = rating_data['count']
        self.restaurant_repo.save(restaurant)

        logger.info(
            "Review created: customer=%s, restaurant=%s, rating=%d",
            customer_id, restaurant_id, rating,
        )
        return review.to_dict()

    def list_restaurant_reviews(
        self, restaurant_id: str, page: int = 1, page_size: int = 10,
    ) -> dict:
        """List reviews for a restaurant with pagination."""
        result = self.repo.list_by_restaurant(restaurant_id, page=page, page_size=page_size)
        return result.to_dict()
