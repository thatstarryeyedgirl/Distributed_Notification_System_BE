from django.urls import path
from .views import notification_status, health_check

urlpatterns = [
    path('status/<uuid:notification_id>/', notification_status,name='notification_detail'),
    path('health/', health_check, name='health_check'),
]

