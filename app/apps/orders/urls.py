"""Order URL routing. Prefixed with /api/orders/"""
from django.urls import path
from apps.orders import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderListView.as_view(), name='list'),
    path('<str:order_id>/', views.OrderDetailView.as_view(), name='detail'),
    path('<str:order_id>/status/', views.OrderStatusView.as_view(), name='status'),
    path('validate-coupon/', views.ValidateCouponView.as_view(), name='validate_coupon'),
]
