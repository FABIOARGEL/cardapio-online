"""Order URL routing. Prefixed with /api/orders/"""
from django.urls import path
from apps.orders import views

app_name = 'orders'

urlpatterns = [
    path('', views.ListaPedidosView.as_view(), name='list'),
    path('<str:order_id>/', views.DetalhePedidoView.as_view(), name='detail'),
    path('<str:order_id>/status/', views.StatusPedidoView.as_view(), name='status'),
    path('validate-coupon/', views.ValidarCupomView.as_view(), name='validate_coupon'),
]
