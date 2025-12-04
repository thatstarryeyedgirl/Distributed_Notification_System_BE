import uuid
from django.db import models

class PushNotification(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_PROCESSING, "processing"),
        (STATUS_DELIVERED, "delivered"),
        (STATUS_FAILED, "failed"),
    ]

    notification_id = models.CharField(max_length=100, unique=True)  # From API Gateway
    request_id = models.CharField(max_length=150, unique=True)
    user_id = models.UUIDField()
    push_token = models.CharField(max_length=300)  # From API Gateway
    template_code = models.CharField(max_length=150)
    variables = models.JSONField(default=dict, blank=True)
    priority = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    processed_title = models.CharField(max_length=255, blank=True)
    processed_body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.notification_id} - {self.status}"

class PushDeliveryLog(models.Model):
    notification = models.ForeignKey(PushNotification, on_delete=models.CASCADE, related_name="delivery_logs")
    status = models.CharField(max_length=20)
    fcm_response = models.JSONField(default=dict, blank=True)
    fcm_message_id = models.CharField(max_length=200, blank=True, null=True)
    error_code = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
    
    def __str__(self):
        return f"{self.notification.notification_id} - {self.status}"


