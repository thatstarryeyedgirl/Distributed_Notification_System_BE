from django.urls import path
from .views import NotificationView, HealthView, enqueue_notification

urlpatterns = [
    path('notifications/', NotificationView.as_view(), name='send_notification'),
    path('enqueue/', enqueue_notification, name='enqueue_notification'),
    path('health/', HealthView.as_view(), name='health_check'),
]