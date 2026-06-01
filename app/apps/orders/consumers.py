"""
WebSocket consumers for real-time order notifications.

Refactored:
- Added JWT authentication on WebSocket handshake
- Proper error handling and logging
"""
from __future__ import annotations

import json
import logging

import jwt
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class AuthenticatedWebsocketConsumer(AsyncWebsocketConsumer):
    """
    Base WebSocket consumer with JWT authentication.

    Extracts the token from the query string: ws://.../?token=<jwt>
    Only authenticated users can connect.
    """

    async def authenticate(self) -> dict | None:
        """
        Authenticate the WebSocket connection using JWT from query string.

        Returns the JWT payload if valid, None otherwise.
        """
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = dict(param.split('=', 1) for param in query_string.split('&') if '=' in param)
        token = params.get('token')

        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get('type') != 'access':
                return None
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None


class OrderConsumer(AuthenticatedWebsocketConsumer):
    """
    WebSocket consumer for restaurant order notifications.

    Endpoint: ws/orders/<restaurant_id>/?token=<jwt>
    Restaurant owners connect to receive real-time new order notifications.
    """

    async def connect(self):
        self.restaurant_id = self.scope['url_route']['kwargs']['restaurant_id']
        self.group_name = f'restaurant_{self.restaurant_id}'

        # Authenticate
        payload = await self.authenticate()
        if not payload or payload.get('papel') != 'dono':
            logger.warning("Unauthorized WebSocket connection attempt to restaurant %s", self.restaurant_id)
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("WebSocket connected: restaurant %s (user=%s)", self.restaurant_id, payload.get('user_id'))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_new(self, event):
        """Handle new order notification — broadcast to restaurant."""
        await self.send(text_data=json.dumps({
            'type': 'new_order',
            'data': event['data'],
        }))


class OrderStatusConsumer(AuthenticatedWebsocketConsumer):
    """
    WebSocket consumer for order status tracking.

    Endpoint: ws/orders/<order_id>/status/?token=<jwt>
    Customers connect to track real-time status updates for their order.
    """

    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.group_name = f'order_{self.order_id}'

        # Authenticate — any authenticated user can track an order
        payload = await self.authenticate()
        if not payload:
            logger.warning("Unauthorized WebSocket connection attempt to order %s", self.order_id)
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_status_update(self, event):
        """Handle status update — send to customer."""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': event['data'],
        }))
