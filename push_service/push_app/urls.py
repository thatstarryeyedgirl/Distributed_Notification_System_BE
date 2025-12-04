from django.urls import path
from .views import notification_status, health

urlpatterns = [
    path('status/<uuid:notification_id>/', notification_status, name='push_notification_detail'),
    path('health/', health, name='health'),
]

