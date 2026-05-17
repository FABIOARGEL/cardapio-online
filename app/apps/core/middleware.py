"""
Custom middleware for Cardápio Online.

- SecurityHeadersMiddleware: Adds security headers to every response.
- RateLimitMiddleware: Simple in-memory rate limiter per IP.
"""
import time
from collections import defaultdict
from threading import Lock

from django.conf import settings
from django.http import JsonResponse


class SecurityHeadersMiddleware:
    """
    Adds security headers to every HTTP response:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: SAMEORIGIN
    - X-XSS-Protection: 1; mode=block
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        return response


class RateLimitMiddleware:
    """
    Simple in-memory rate limiter.
    Limits requests per IP per minute based on RATE_LIMIT_PER_MINUTE setting.

    Note: In production with multiple workers, use a shared store (Redis).
    For this academic project with InMemoryChannelLayer, this is sufficient.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()
        self.limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 100)

    def __call__(self, request):
        ip = self._get_client_ip(request)
        now = time.time()
        window = 60.0  # 1 minute

        with self.lock:
            # Remove old entries outside the window
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if now - ts < window
            ]

            if len(self.requests[ip]) >= self.limit:
                return JsonResponse(
                    {'error': 'Muitas requisições. Tente novamente em breve.'},
                    status=429
                )

            self.requests[ip].append(now)

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from X-Forwarded-For or REMOTE_ADDR."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
