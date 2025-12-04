from django.db import models

class EmailNotification(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_BOUNCED = "bounced"

    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_PROCESSING, "processing"),
        (STATUS_DELIVERED, "delivered"),
        (STATUS_FAILED, "failed"),
        (STATUS_BOUNCED, "bounced"),
    ]
    
    # Template constants
    TEMPLATE_WELCOME = "welcome_email"
    TEMPLATE_PASSWORD_RESET = "password_reset"
    TEMPLATE_VERIFICATION = "email_verification"
    
    notification_id = models.CharField(max_length=100, unique=True, blank=True)
    request_id = models.CharField(max_length=150, unique=True)
    user_id = models.UUIDField()
    to_email = models.EmailField()
    template_code = models.CharField(max_length=150)
    variables = models.JSONField(default=dict, blank=True)
    priority = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    attempts = models.IntegerField(default=0)
    processed_subject = models.CharField(max_length=255, blank=True)
    processed_body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.notification_id:
            self.notification_id = f"email_{self.pk or hash(f'{self.user_id}{self.template_code}')}"
        super().save(*args, **kwargs)
    
    def auto_update_status(self, status, error_message=None):
        self.status = status
        if error_message:
            self.last_error = error_message
        self.save()
    
    def __str__(self):
        return f"{self.notification_id} - {self.status}"


class DeliveryLog(models.Model):
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_PENDING = "pending"
    
    notification = models.ForeignKey(EmailNotification, on_delete=models.CASCADE, related_name="delivery_logs")
    status = models.CharField(max_length=20)
    smtp_response = models.TextField(blank=True, null=True)
    message_id = models.CharField(max_length=200, null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.notification.notification_id} - {self.status}"


