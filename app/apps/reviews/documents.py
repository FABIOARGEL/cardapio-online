"""
MongoEngine Documents for Review collection.

Stores customer reviews for restaurants and specific orders.
"""
from datetime import datetime, timezone

import mongoengine as me


class Review(me.Document):
    """
    Review document stored in MongoDB 'reviews' collection.

    Each review links a customer to a restaurant (and optionally an order).
    """
    customer_id = me.ObjectIdField(required=True)
    customer_name = me.StringField(required=True, max_length=100)
    restaurant_id = me.ObjectIdField(required=True)
    order_id = me.ObjectIdField()
    rating = me.IntField(required=True, min_value=1, max_value=5)
    comment = me.StringField(max_length=500)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'reviews',
        'indexes': [
            {'fields': ['restaurant_id', '-created_at']},
            {'fields': ['customer_id']},
            {'fields': ['order_id'], 'sparse': True},
        ],
        'ordering': ['-created_at'],
        'strict': False,
    }

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'customer_id': str(self.customer_id),
            'customer_name': self.customer_name,
            'restaurant_id': str(self.restaurant_id),
            'order_id': str(self.order_id) if self.order_id else None,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
