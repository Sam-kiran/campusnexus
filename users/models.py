from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


def validate_college_email(value):
    """Validate that email is from college domain."""
    from django.conf import settings
    domain = settings.COLLEGE_EMAIL_DOMAIN
    if not value.endswith(domain):
        raise ValidationError(f'Email must be from {domain} domain')


class User(AbstractUser):
    """Custom User model with role-based access."""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('management', 'Management'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True, validators=[EmailValidator(), validate_college_email])
    department = models.CharField(max_length=100, blank=True)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_student(self):
        return self.role == 'student'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_organizer(self):
        return self.role == 'organizer'
    
    def is_management(self):
        return self.role == 'management'
    
    def is_admin_or_organizer(self):
        return self.role in ['admin', 'organizer']
    
    def is_admin_or_management(self):
        return self.role in ['admin', 'management']


class EmailVerification(models.Model):
    """Stores email verification codes for users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_email_verifications'

    def is_valid(self):
        return (not self.used) and (self.expires_at >= timezone.now())


class Leaderboard(models.Model):
    """Leaderboard for student participation."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    total_events_attended = models.IntegerField(default=0)
    total_feedback_given = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leaderboard'
        ordering = ['-total_points', '-total_events_attended']
    
    def __str__(self):
        return f"{self.user.username} - Rank {self.rank}"

