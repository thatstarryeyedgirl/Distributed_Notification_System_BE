from django.urls import path
from .views import (
    AdminRegisterView, AdminLoginView, APIKeyCreateView, 
    APIKeyListView, APIKeyRevokeView, ForgotPasswordView,
    ResetPasswordView, health_check
)

urlpatterns = [
    path('register/', AdminRegisterView.as_view(), name='admin_register'),
    path('login/', AdminLoginView.as_view(), name='admin_login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', ResetPasswordView.as_view(), name='reset_password'),
    path('api-keys/', APIKeyCreateView.as_view(), name='create_api_key'),
    path('api-keys/list/', APIKeyListView.as_view(), name='list_api_keys'),
    path('api-keys/<str:service_name>/revoke/', APIKeyRevokeView.as_view(), name='revoke_api_key'),
    path('health/', health_check, name='health_check'),
]