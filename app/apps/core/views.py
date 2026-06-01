"""
Views for frontend pages (Django Templates).

These views render HTML pages — no business logic here.
Business logic is handled by services called from API views.
"""
from django.shortcuts import render


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Public pages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def home(request):
    """Landing page with global product catalog."""
    return render(request, 'core/home.html')


def restaurant_list(request):
    """List all active restaurants with search and filters."""
    return render(request, 'restaurants/list.html')


def restaurant_detail(request, slug: str):
    """Restaurant detail page with menu organized by category."""
    return render(request, 'restaurants/detail.html', {'slug': slug})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Auth pages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def login_page(request):
    """Login page with email/password and Google OAuth."""
    return render(request, 'auth/login.html')


def register_page(request):
    """Registration page with user type selection."""
    return render(request, 'auth/register.html')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Customer pages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def cart_page(request):
    """Shopping cart page."""
    return render(request, 'orders/cart.html')


def checkout_page(request):
    """Checkout/finalization page."""
    return render(request, 'orders/checkout.html')


def order_confirmation(request, numero_pedido: str):
    """Página de confirmação após checkout."""
    return render(request, 'orders/confirmation.html', {'numero_pedido': numero_pedido})


def my_orders(request):
    """List of customer's orders."""
    return render(request, 'orders/my_orders.html')


def order_tracking(request, numero_pedido: str):
    """Página de acompanhamento do status do pedido (websockets)."""
    return render(request, 'orders/tracking.html', {'numero_pedido': numero_pedido})


def profile_page(request):
    """Customer profile management page."""
    return render(request, 'auth/profile.html')


def addresses_page(request):
    """Customer address management page."""
    return render(request, 'auth/addresses.html')



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Owner dashboard pages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def dashboard_overview(request):
    """Restaurant owner dashboard overview."""
    return render(request, 'restaurants/dashboard/overview.html')


def dashboard_products(request):
    """Product management page for restaurant owners."""
    return render(request, 'restaurants/dashboard/products.html')


def dashboard_orders(request):
    """Order management page (Kanban) for restaurant owners."""
    return render(request, 'restaurants/dashboard/orders.html')


def dashboard_settings(request):
    """Restaurant settings page for owners."""
    return render(request, 'restaurants/dashboard/settings.html')


def dashboard_coupons(request):
    """Coupon management page for restaurant owners."""
    return render(request, 'restaurants/dashboard/coupons.html')


def dashboard_reports(request):
    """Order history and reports page."""
    return render(request, 'restaurants/dashboard/reports.html')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health check (for Docker / monitoring)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def health_check(request):
    """Health check endpoint for Docker/load balancer."""
    from django.http import JsonResponse
    return JsonResponse({'status': 'ok', 'service': 'cardapio-online'})
