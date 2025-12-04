from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
import secrets
import string

class AdminsManager(BaseUserManager):
    def create_admin(self, email, name, password=None):
        if not email:
            raise ValueError("Admins must state their email address")
        email = self.normalize_email(email)
        admin = self.model(email=email, name=name)
        admin.set_password(password)
        admin.save(using=self._db)
        return admin

    def create_superuser(self, email, name, password):
        admin = self.create_admin(email, name, password)
        admin.is_superuser = True
        admin.is_staff = True
        admin.save(using=self._db)
        return admin
    

class Admins(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = AdminsManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email


def generate_api_key():
    # Generate a secure API key with mixed characters
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(32))

class AdminAPIKey(models.Model):
    key = models.CharField(max_length=40, unique=True, default=generate_api_key, editable=False)
    admin = models.ForeignKey(Admins, on_delete=models.CASCADE, related_name="api_keys")
    service_name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['admin', 'service_name']

    def __str__(self):
        return f"{self.admin.email} - {self.service_name} ({self.key[:8]}...)"

