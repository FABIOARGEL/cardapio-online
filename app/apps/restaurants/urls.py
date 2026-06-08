"""Restaurant URL routing. Prefixed with /api/restaurants/"""
from django.urls import path
from apps.restaurants import views

app_name = 'restaurants'

urlpatterns = [
    # Public
    path('', views.RestaurantListView.as_view(), name='list'),
    path('all-pratos/', views.AllPratosView.as_view(), name='all_pratos'),
    path('slug/<str:slug>/', views.RestaurantSlugView.as_view(), name='slug'),

    # Owner
    path('create/', views.RestaurantCreateView.as_view(), name='create'),
    path('mine/', views.OwnerRestaurantsView.as_view(), name='mine'),

    # Restaurant detail
    path('<str:restaurant_id>/', views.RestaurantDetailView.as_view(), name='detail'),
    path('<str:restaurant_id>/owner-detail/', views.OwnerRestaurantDetailView.as_view(), name='owner_detail'),

    # Pratos
    path('<str:restaurant_id>/pratos/', views.PratoListView.as_view(), name='prato_list'),
    path('<str:restaurant_id>/pratos/<str:prato_id>/', views.PratoDetailView.as_view(), name='prato_detail'),

    # Stats & History
    path('<str:restaurant_id>/stats/', views.StatsView.as_view(), name='stats'),
    path('<str:restaurant_id>/history/', views.OrderHistoryView.as_view(), name='history'),

    # Coupons
    path('<str:restaurant_id>/coupons/', views.CouponListView.as_view(), name='coupon_list'),
    path('<str:restaurant_id>/coupons/<str:coupon_id>/', views.CouponDetailView.as_view(), name='coupon_detail'),
]
