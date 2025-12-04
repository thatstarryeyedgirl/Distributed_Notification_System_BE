from django.db import models
import uuid

NOTIFICATION_TYPE = [
    ('email', 'Email'),
    ('push', 'Push'),
]
STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
class NotificationRequest(models.Model):
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    user_id = models.UUIDField()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_code = models.CharField(max_length=100)
    variables = models.JSONField()
    request_id = models.CharField(max_length=100, unique=True)
    priority = models.IntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.notification_type} - {self.status}"


