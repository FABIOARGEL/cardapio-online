"""
Frontend page URL routing.

Serves Django Templates for the frontend pages.
"""
from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('restaurantes/', views.restaurant_list, name='restaurant_list'),
    path('restaurante/<str:slug>/', views.restaurant_detail, name='restaurant_detail'),

    # Auth pages
    path('login/', views.login_page, name='login'),
    path('cadastro/', views.register_page, name='register'),

    # Customer pages (require auth)
    path('carrinho/', views.cart_page, name='cart'),
    path('checkout/', views.checkout_page, name='checkout'),
    path('pedido/<str:numero_pedido>/', views.order_confirmation, name='order_confirmation'),
    # Tracking
    path('pedido/<str:numero_pedido>/acompanhar/', views.order_tracking, name='order_tracking'),
    path('meus-pedidos/', views.my_orders, name='my_orders'),
    path('perfil/', views.profile_page, name='profile'),
    path('enderecos/', views.addresses_page, name='addresses'),


    # Owner dashboard pages (require auth + owner role)
    path('dashboard/', views.dashboard_overview, name='dashboard'),
    path('dashboard/produtos/', views.dashboard_products, name='dashboard_products'),
    path('dashboard/pedidos/', views.dashboard_orders, name='dashboard_orders'),
    path('dashboard/configuracoes/', views.dashboard_settings, name='dashboard_settings'),
    path('dashboard/cupons/', views.dashboard_coupons, name='dashboard_coupons'),
    path('dashboard/relatorios/', views.dashboard_reports, name='dashboard_reports'),
]
