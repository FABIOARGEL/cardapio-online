"""WebSocket URL routing for Django Channels."""
from django.urls import re_path
from apps.orders import consumers

websocket_urlpatterns = [
    re_path(r'ws/orders/(?P<restaurant_id>[a-f0-9]{24})/$', consumers.OrderConsumer.as_asgi()),
    re_path(r'ws/orders/(?P<order_id>[a-f0-9]{24})/status/$', consumers.OrderStatusConsumer.as_asgi()),
]
