import uuid, secrets
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.core.exceptions import ValidationError
from django.conf import settings

class UsersManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            name=name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password):
        user = self.create_user(email, name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Users(AbstractBaseUser, PermissionsMixin):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups"
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions"
    )

    objects = UsersManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.name


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferences", primary_key=True)
    email = models.BooleanField()
    push = models.BooleanField()
    
    def clean(self):
        # Ensure user chooses exactly one preference
        if self.email == self.push:
            raise ValidationError("User must choose either email OR push, not both or neither.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} preferences"


class Device(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="devices")
    DEVICE_TYPES = [
        ('android', 'Android'),
        ('ios', 'IOS'),
        ('web', 'Web'),
    ]
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES)
    push_token = models.CharField(max_length=64, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self,*args,**kwargs):
        if not self.push_token:
            self.push_token = secrets.token_urlsafe(32)
            super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.user.email} ({self.device_type})"


class NotificationStatus(models.TextChoices):
    DELIVERED = "delivered", "Delivered"
    PENDING = "pending", "Pending"
    FAILED = "failed", "Failed"


class NotificationLog(models.Model):
    notification_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_preference = models.CharField(max_length=10, choices=[('email', 'Email'), ('push', 'Push')])
    status = models.CharField(max_length=10, choices=NotificationStatus.choices, default=NotificationStatus.PENDING)
    timestamp = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.notification_id} - {self.status}"


class ErrorLog(models.Model):
    notification = models.ForeignKey(NotificationLog, on_delete=models.CASCADE, related_name="errors")
    service_name = models.CharField(max_length=50)  # 'email_service' or 'push_service'
    error_code = models.CharField(max_length=20)  # 'SMTP_TIMEOUT', 'INVALID_TOKEN', etc.
    error_message = models.TextField()  # Detailed error description
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.notification.notification_id} - {self.error_code}"


