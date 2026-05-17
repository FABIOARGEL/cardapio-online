"""
MongoEngine Documents for Restaurant and Product collections.

Schema matches doc 06-modelagem-mongodb.md:
- Restaurant: owner_id, name, slug, description, cover_image_url, contact, address,
              business_hours, products (embedded), coupons (embedded), status, rating
- Product: embedded within Restaurant — name, description, price, category,
           image_url, is_available, sort_order, stock
- Coupon: embedded within Restaurant — code, discount_type, discount_value,
          min_order, max_uses, used_count, valid_from, valid_until, is_active
"""
from datetime import datetime, timezone
from bson import Decimal128

import mongoengine as me


class Contact(me.EmbeddedDocument):
    """Embedded contact information for a restaurant."""
    phone = me.StringField(max_length=20, required=True)
    email = me.EmailField()
    whatsapp = me.StringField(max_length=20)

    meta = {'strict': False}


class Coordinates(me.EmbeddedDocument):
    """Geographic coordinates for restaurant location."""
    lat = me.FloatField()
    lng = me.FloatField()

    meta = {'strict': False}


class RestaurantAddress(me.EmbeddedDocument):
    """Embedded address for a restaurant."""
    street = me.StringField(max_length=200, required=True)
    number = me.StringField(max_length=20, required=True)
    complement = me.StringField(max_length=100)
    neighborhood = me.StringField(max_length=100, required=True)
    city = me.StringField(max_length=100, required=True)
    state = me.StringField(max_length=2, required=True)
    zip_code = me.StringField(max_length=10, required=True)
    coordinates = me.EmbeddedDocumentField(Coordinates)

    meta = {'strict': False}


class BusinessHour(me.EmbeddedDocument):
    """Business hours for a specific day of the week."""
    day = me.IntField(required=True, min_value=0, max_value=6)  # 0=Sun, 6=Sat
    open = me.StringField(max_length=5)   # HH:MM
    close = me.StringField(max_length=5)  # HH:MM
    is_closed = me.BooleanField(default=False)

    meta = {'strict': False}


class Rating(me.EmbeddedDocument):
    """Aggregated rating information."""
    average = me.FloatField(default=0.0, min_value=0, max_value=5)
    count = me.IntField(default=0, min_value=0)

    meta = {'strict': False}


class Product(me.EmbeddedDocument):
    """
    Product embedded within a Restaurant document.

    Categories: appetizer, main, dessert, drink, combo
    """
    CATEGORY_CHOICES = ('appetizer', 'main', 'dessert', 'drink', 'combo')

    _id = me.ObjectIdField(required=True, default=me.ObjectIdField().to_python)
    name = me.StringField(required=True, max_length=100)
    description = me.StringField(max_length=500)
    price = me.DecimalField(required=True, min_value=0.01, precision=2)
    category = me.StringField(required=True, choices=CATEGORY_CHOICES)
    image_url = me.StringField(default='')
    images = me.ListField(me.StringField(), max_length=5, default=list)
    is_available = me.BooleanField(default=True)
    sort_order = me.IntField(default=0)
    stock = me.IntField(default=-1)  # -1 = unlimited, 0+ = tracked
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {'strict': False}

    def to_dict(self) -> dict:
        price_val = 0
        try:
            price_val = float(self.price) if self.price is not None else 0
        except (TypeError, ValueError):
            price_val = 0
        return {
            'id': str(self._id),
            'name': self.name,
            'description': self.description or '',
            'price': price_val,
            'category': self.category,
            'image_url': self.image_url or '',
            'images': self.images or [],
            'is_available': self.is_available,
            'sort_order': self.sort_order,
            'stock': self.stock,
        }


class Coupon(me.EmbeddedDocument):
    """
    Coupon/promotion embedded within a Restaurant document.

    discount_type: 'percentage' or 'fixed'
    """
    DISCOUNT_TYPE_CHOICES = ('percentage', 'fixed')

    _id = me.ObjectIdField(required=True, default=me.ObjectIdField().to_python)
    code = me.StringField(required=True, max_length=30)
    description = me.StringField(max_length=200)
    discount_type = me.StringField(required=True, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = me.DecimalField(required=True, min_value=0.01, precision=2)
    min_order = me.DecimalField(default=0, precision=2)
    max_uses = me.IntField(default=0)  # 0 = unlimited
    used_count = me.IntField(default=0)
    valid_from = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    valid_until = me.DateTimeField()
    is_active = me.BooleanField(default=True)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {'strict': False}

    def to_dict(self) -> dict:
        return {
            'id': str(self._id),
            'code': self.code,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value) if self.discount_value else 0,
            'min_order': float(self.min_order) if self.min_order else 0,
            'max_uses': self.max_uses,
            'used_count': self.used_count,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Restaurant(me.Document):
    """
    Restaurant document stored in MongoDB 'restaurants' collection.

    Products and coupons are embedded within the restaurant document for
    optimal read performance (always accessed together).
    Limit: ~200 products per restaurant.
    """
    STATUS_CHOICES = ('active', 'inactive', 'suspended')

    owner_id = me.ObjectIdField(required=True)
    name = me.StringField(required=True, max_length=100)
    slug = me.StringField(required=True, unique=True, max_length=120)
    description = me.StringField(max_length=500)
    cover_image_url = me.StringField(default='')
    logo_url = me.StringField()
    contact = me.EmbeddedDocumentField(Contact)
    address = me.EmbeddedDocumentField(RestaurantAddress)
    business_hours = me.EmbeddedDocumentListField(BusinessHour, default=list)
    categories = me.ListField(me.StringField(), default=list)
    products = me.EmbeddedDocumentListField(Product, default=list)
    coupons = me.EmbeddedDocumentListField(Coupon, default=list)
    delivery_fee = me.DecimalField(default=0, precision=2)
    estimated_delivery_time = me.StringField(max_length=50, default='40-50 min')
    status = me.StringField(choices=STATUS_CHOICES, default='active')
    rating = me.EmbeddedDocumentField(Rating, default=Rating)
    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'restaurants',
        'indexes': [
            {'fields': ['slug'], 'unique': True},
            {'fields': ['owner_id']},
            {'fields': ['status']},
            {
                'fields': ['$name', '$description'],
                'default_language': 'portuguese',
            },
            {'fields': ['products.category']},
        ],
        'ordering': ['-created_at'],
        'strict': False,
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def to_dict(self, include_products: bool = False, include_all_products: bool = False, include_coupons: bool = False) -> dict:
        """Convert restaurant to dictionary for API responses."""
        delivery_fee_val = 0
        try:
            delivery_fee_val = float(self.delivery_fee) if self.delivery_fee is not None else 0
        except (TypeError, ValueError):
            delivery_fee_val = 0

        data = {
            'id': str(self.id),
            'owner_id': str(self.owner_id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description or '',
            'cover_image_url': self.cover_image_url or '',
            'logo_url': self.logo_url or '',
            'delivery_fee': delivery_fee_val,
            'estimated_delivery_time': self.estimated_delivery_time or '40-50 min',
            'contact': {
                'phone': self.contact.phone if self.contact else None,
                'email': self.contact.email if self.contact else None,
                'whatsapp': self.contact.whatsapp if self.contact else None,
            } if self.contact else None,
            'address': {
                'street': self.address.street,
                'number': self.address.number,
                'complement': self.address.complement,
                'neighborhood': self.address.neighborhood,
                'city': self.address.city,
                'state': self.address.state,
                'zip_code': self.address.zip_code,
            } if self.address else None,
            'business_hours': [
                {
                    'day': bh.day,
                    'open': bh.open,
                    'close': bh.close,
                    'is_closed': bh.is_closed,
                }
                for bh in self.business_hours
            ],
            'categories': self.categories,
            'status': self.status,
            'rating': {
                'average': self.rating.average if self.rating else 0,
                'count': self.rating.count if self.rating else 0,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_products:
            data['products'] = [p.to_dict() for p in self.products if p.is_available]

        if include_all_products:
            data['products'] = [p.to_dict() for p in self.products]

        if include_coupons:
            data['coupons'] = [c.to_dict() for c in self.coupons]

        return data
