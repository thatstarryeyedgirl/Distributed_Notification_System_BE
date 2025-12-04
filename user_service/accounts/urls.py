from django.urls import path
from .views import UserRegisterView, UserLoginView, DeviceRegisterView, PreferenceUpdateView, ForgotPasswordView, ResetPasswordView, NotificationStatusView, UserDetailView, HealthView, InternalValidateTokenView

urlpatterns = [
    path('users/', UserRegisterView.as_view(), name='user-register'),
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/login/', UserLoginView.as_view(), name='user-login'),
    path('users/devices/', DeviceRegisterView.as_view(), name='device-register'),
    path('preferences/', PreferenceUpdateView.as_view(), name='preference-update'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<str:uidb64>/<str:token>/', ResetPasswordView.as_view(), name='reset-password'),
    path('notification/<str:notification_preference>/status/', NotificationStatusView.as_view(), name='notification-status'),
    
    path('internal/validate-token/', InternalValidateTokenView.as_view(), name='internal-validate'),
    path('health/', HealthView.as_view(), name='health'),
]

