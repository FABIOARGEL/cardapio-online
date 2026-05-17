"""
MongoEngine Documents for Order collection.
Schema matches doc 06-modelagem-mongodb.md.
"""
from datetime import datetime, timezone
import mongoengine as me


class OrderItem(me.EmbeddedDocument):
    """Embedded order item — snapshot of product at time of order."""
    product_id = me.ObjectIdField(required=True)
    name = me.StringField(required=True)
    price = me.DecimalField(required=True, precision=2)
    quantity = me.IntField(required=True, min_value=1, max_value=99)
    subtotal = me.DecimalField(required=True, precision=2)
    image_url = me.StringField()
    meta = {'strict': False}


class StatusChange(me.EmbeddedDocument):
    """Record of a status transition."""
    status = me.StringField(required=True)
    changed_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    changed_by = me.ObjectIdField()
    meta = {'strict': False}


class DeliveryAddress(me.EmbeddedDocument):
    """Delivery address snapshot."""
    street = me.StringField(max_length=200)
    number = me.StringField(max_length=20)
    complement = me.StringField(max_length=100)
    neighborhood = me.StringField(max_length=100)
    city = me.StringField(max_length=100)
    state = me.StringField(max_length=2)
    zip_code = me.StringField(max_length=10)
    meta = {'strict': False}


class Order(me.Document):
    """Order document stored in MongoDB 'orders' collection."""
    STATUS_CHOICES = ('pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled')
    DELIVERY_CHOICES = ('delivery', 'pickup')
    PAYMENT_CHOICES = ('pix', 'card', 'cash')

    # Valid status transitions
    VALID_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready', 'cancelled'],
        'ready': ['delivered', 'cancelled'],
        'delivered': [],
        'cancelled': [],
    }

    order_number = me.StringField(required=True, unique=True)
    customer_id = me.ObjectIdField(required=True)
    restaurant_id = me.ObjectIdField(required=True)
    items = me.EmbeddedDocumentListField(OrderItem, required=True)
    total = me.DecimalField(required=True, precision=2, min_value=0)
    delivery_fee = me.DecimalField(default=0, precision=2)
    discount_amount = me.DecimalField(default=0, precision=2)
    coupon_code = me.StringField(max_length=30)
    status = me.StringField(required=True, choices=STATUS_CHOICES, default='pending')
    status_history = me.EmbeddedDocumentListField(StatusChange, default=list)
    delivery_method = me.StringField(required=True, choices=DELIVERY_CHOICES)
    delivery_address = me.EmbeddedDocumentField(DeliveryAddress)
    payment_method = me.StringField(required=True, choices=PAYMENT_CHOICES, default='pix')
    notes = me.StringField(max_length=500)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'orders',
        'indexes': [
            {'fields': ['order_number'], 'unique': True},
            {'fields': ['customer_id', '-created_at']},
            {'fields': ['restaurant_id', 'status', '-created_at']},
            {'fields': ['status']},
            {'fields': ['-created_at']},
        ],
        'ordering': ['-created_at'],
        'strict': False,
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': str(self.id),
            'order_number': self.order_number,
            'customer_id': str(self.customer_id),
            'restaurant_id': str(self.restaurant_id),
            'items': [
                {
                    'product_id': str(item.product_id),
                    'name': item.name,
                    'price': float(item.price),
                    'quantity': item.quantity,
                    'subtotal': float(item.subtotal),
                    'image_url': item.image_url,
                }
                for item in self.items
            ],
            'total': float(self.total),
            'delivery_fee': float(self.delivery_fee) if self.delivery_fee else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'coupon_code': self.coupon_code,
            'status': self.status,
            'status_history': [
                {
                    'status': sh.status,
                    'changed_at': sh.changed_at.isoformat() if sh.changed_at else None,
                    'changed_by': str(sh.changed_by) if sh.changed_by else None,
                }
                for sh in self.status_history
            ],
            'delivery_method': self.delivery_method,
            'delivery_address': {
                'street': self.delivery_address.street,
                'number': self.delivery_address.number,
                'complement': self.delivery_address.complement,
                'neighborhood': self.delivery_address.neighborhood,
                'city': self.delivery_address.city,
                'state': self.delivery_address.state,
                'zip_code': self.delivery_address.zip_code,
            } if self.delivery_address else None,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
