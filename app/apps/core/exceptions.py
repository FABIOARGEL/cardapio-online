"""
Custom exceptions for the Cardápio Online platform.

Each exception maps to a specific HTTP status code and user-facing message.
The custom_exception_handler translates domain exceptions to DRF responses.
"""
from __future__ import annotations

import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Auth exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AccountLockedError(Exception):
    """Raised when a user account is temporarily locked due to failed login attempts."""

    def __init__(self, minutes_remaining: int = 15):
        self.minutes_remaining = minutes_remaining
        super().__init__(
            f"Account locked. Try again in {minutes_remaining} minutes."
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Authorization exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class OwnershipError(Exception):
    """Raised when a user tries to access/modify a resource they don't own."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Order exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class InvalidStatusTransition(Exception):
    """Raised when an invalid order status transition is attempted."""

    def __init__(self, current_status: str, requested_status: str):
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid status transition from '{current_status}' to '{requested_status}'"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Upload exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class InvalidFileTypeError(Exception):
    """Raised when an uploaded file has an invalid MIME type."""
    pass


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the size limit."""
    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Coupon exceptions (extracted from generic ValueError)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class InvalidCouponError(Exception):
    """Raised when a coupon code is invalid or inactive."""

    def __init__(self, message: str = 'Cupom inválido.'):
        super().__init__(message)


class CouponExpiredError(Exception):
    """Raised when a coupon has expired."""

    def __init__(self):
        super().__init__('Cupom expirado.')


class CouponMinOrderError(Exception):
    """Raised when cart total is below coupon minimum."""

    def __init__(self, min_order: float):
        self.min_order = min_order
        super().__init__(f'Valor mínimo para este cupom é R$ {min_order:.2f}')


class CouponExhaustedError(Exception):
    """Raised when a coupon has reached maximum uses."""

    def __init__(self):
        super().__init__('Cupom esgotado.')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Resource exceptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ResourceNotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource_name: str = 'Recurso'):
        self.resource_name = resource_name
        super().__init__(f'{resource_name} não encontrado(a).')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Exception Handler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that maps domain exceptions
    to proper HTTP responses with structured error payloads.
    """
    # Let DRF handle its own exceptions first
    response = exception_handler(exc, context)

    if response is not None:
        return response

    # Map domain exceptions to HTTP responses
    error_map: dict[type, tuple[int, str | None]] = {
        OwnershipError: (403, 'Você não tem permissão para acessar este recurso.'),
        AccountLockedError: (429, None),  # Custom handling below
        InvalidFileTypeError: (400, None),
        FileTooLargeError: (400, None),
        ResourceNotFoundError: (404, None),
        InvalidCouponError: (400, None),
        CouponExpiredError: (400, None),
        CouponMinOrderError: (400, None),
        CouponExhaustedError: (400, None),
    }

    for exc_class, (status_code, default_message) in error_map.items():
        if isinstance(exc, exc_class):
            payload = {'error': default_message or str(exc)}
            if isinstance(exc, AccountLockedError):
                payload['minutes_remaining'] = exc.minutes_remaining
            if isinstance(exc, InvalidStatusTransition):
                payload.update({
                    'detail': str(exc),
                    'current_status': exc.current_status,
                    'requested_status': exc.requested_status,
                })
            return Response(payload, status=status_code)

    if isinstance(exc, InvalidStatusTransition):
        return Response(
            {
                'error': 'Transição de status inválida.',
                'detail': str(exc),
                'current_status': exc.current_status,
                'requested_status': exc.requested_status,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Log unhandled exceptions
    logger.exception("Unhandled exception in %s", context.get('view', 'unknown'))

    return Response(
        {'error': 'Ocorreu um erro interno no servidor.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
