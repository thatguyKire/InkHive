# modules/authentication/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    student_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    # Which Terms of Service / Privacy Policy version the user agreed to, and when
    # (see settings.TERMS_VERSION and modules/legal).
    terms_version = models.CharField(max_length=20, blank=True, default="")
    terms_accepted_at = models.DateTimeField(blank=True, null=True)

    @property
    def has_accepted_terms(self):
        return self.terms_version == settings.TERMS_VERSION

    def accept_terms(self):
        """Record agreement to the current terms (caller saves)."""
        self.terms_version = settings.TERMS_VERSION
        self.terms_accepted_at = timezone.now()

    def save(self, *args, **kwargs):
        # Automatically assign 'admin' role to superusers
        if self.is_superuser:
            self.role = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
