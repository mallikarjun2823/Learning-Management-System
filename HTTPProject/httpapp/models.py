from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
import os
from django.conf import settings


# Build a per-user upload path and add a unique filename to avoid collisions
def user_directory_file_path(instance, filename):
    ext = filename.split('.')[-1]
    # prefer username; fallback to id or uuid
    user_part = getattr(instance, 'username', None) or getattr(instance, 'id', None) or uuid.uuid4().hex
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join(settings.MEDIA_ROOT, str(user_part), new_filename)


# Custom user model
class Profile(AbstractUser):
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    age = models.IntegerField(null=True, blank=True)
    avatar = models.ImageField(upload_to=user_directory_file_path, null=True, blank=True)
    resume = models.FileField(upload_to=user_directory_file_path, null=True, blank=True)

    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username if self.username else self.name
    