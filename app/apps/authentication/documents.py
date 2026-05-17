"""
MongoEngine Documents for User collection.

Schema matches doc 06-modelagem-mongodb.md:
- email (unique, indexed)
- password_hash
- name
- phone
- role (customer | owner)
- avatar_url
- google_id (unique, sparse)
- addresses (embedded list)
- is_active
- created_at / updated_at
"""
from datetime import datetime, timezone

import mongoengine as me


class Address(me.EmbeddedDocument):
    """Embedded document for user addresses."""
    label = me.StringField(max_length=50, default='Casa')
    street = me.StringField(max_length=200, required=True)
    number = me.StringField(max_length=20, required=True)
    complement = me.StringField(max_length=100)
    neighborhood = me.StringField(max_length=100, required=True)
    city = me.StringField(max_length=100, required=True)
    state = me.StringField(max_length=2, required=True)
    zip_code = me.StringField(max_length=10, required=True)
    is_default = me.BooleanField(default=False)

    meta = {'strict': False}


class User(me.Document):
    """
    User document stored in MongoDB 'users' collection.

    Supports two types of users:
    - customer: end-user who browses and orders
    - owner: restaurant owner who manages restaurants and products
    """
    ROLE_CHOICES = ('customer', 'owner')

    email = me.EmailField(required=True, unique=True)
    password_hash = me.StringField()
    name = me.StringField(required=True, min_length=2, max_length=100)
    phone = me.StringField(max_length=20)
    role = me.StringField(required=True, choices=ROLE_CHOICES, default='customer')
    avatar_url = me.StringField()
    google_id = me.StringField(unique=True, sparse=True)
    addresses = me.EmbeddedDocumentListField(Address, default=list)
    is_active = me.BooleanField(default=True)

    # Login attempt tracking for account lockout
    failed_login_attempts = me.IntField(default=0)
    locked_until = me.DateTimeField()

    created_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))
    updated_at = me.DateTimeField(default=lambda: datetime.now(timezone.utc))

    meta = {
        'collection': 'users',
        'indexes': [
            {'fields': ['email'], 'unique': True},
            {'fields': ['google_id'], 'unique': True, 'sparse': True},
            {'fields': ['role']},
        ],
        'ordering': ['-created_at'],
        'strict': False,
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.email})"

    def to_dict(self) -> dict:
        """Convert user to a safe dictionary (without password_hash)."""
        return {
            'id': str(self.id),
            'email': self.email,
            'name': self.name,
            'phone': self.phone,
            'role': self.role,
            'avatar_url': self.avatar_url,
            'addresses': [
                {
                    'label': addr.label,
                    'street': addr.street,
                    'number': addr.number,
                    'complement': addr.complement,
                    'neighborhood': addr.neighborhood,
                    'city': addr.city,
                    'state': addr.state,
                    'zip_code': addr.zip_code,
                    'is_default': addr.is_default,
                }
                for addr in self.addresses
            ],
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
