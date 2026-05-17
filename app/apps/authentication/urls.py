"""
Authentication URL routing.

All endpoints are prefixed with /api/auth/ (defined in app/urls.py).
"""
from django.urls import path
from apps.authentication import views

app_name = 'authentication'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('google/', views.GoogleOAuthView.as_view(), name='google_oauth'),
    path('refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.MeView.as_view(), name='me'),
    path('profile/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('password/', views.PasswordUpdateView.as_view(), name='password_update'),
    path('addresses/', views.AddressListView.as_view(), name='address_list'),
    path('addresses/<int:index>/', views.AddressDetailView.as_view(), name='address_detail'),
]
