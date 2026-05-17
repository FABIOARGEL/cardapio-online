"""
URL configuration for Cardápio Online.

Routes:
    /admin/          → Django admin
    /api/auth/       → Authentication endpoints
    /api/restaurants/ → Restaurant & product endpoints
    /api/orders/     → Order endpoints
    /                → Frontend pages
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.core.views import health_check

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Health check (Docker / monitoring)
    path('api/health/', health_check, name='health_check'),

    # OpenAPI / Swagger Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API
    path('api/auth/', include('apps.authentication.urls')),
    path('api/restaurants/', include('apps.restaurants.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/reviews/', include('apps.reviews.urls')),

    # Frontend (pages)
    path('', include('apps.core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
