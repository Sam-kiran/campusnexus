from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from users.models import User
from io import BytesIO
from django.core.files.base import ContentFile
import uuid

# Optional QR code import
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


class PaymentQRCode(models.Model):
    """Reusable payment QR codes that can be used across multiple events."""
    name = models.CharField(max_length=200, help_text="Name/description for this QR code")
    qr_code_image = models.ImageField(upload_to='payment_qr_codes/', help_text="QR code image file")
    qr_code_data = models.TextField(blank=True, help_text="QR code data (UPI ID, etc.)")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_qr_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Whether this QR code is currently in use")
    
    class Meta:
        db_table = 'payment_qr_codes'
        ordering = ['-created_at']
        verbose_name = 'Payment QR Code'
        verbose_name_plural = 'Payment QR Codes'
    
    def __str__(self):
        return f"{self.name} (Created: {self.created_at.strftime('%Y-%m-%d')})"


class Event(models.Model):
    """Event model with all required fields."""
    CATEGORY_CHOICES = [
        ('tech', 'Technology'),
        ('sports', 'Sports'),
        ('cultural', 'Cultural'),
        ('academic', 'Academic'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('competition', 'Competition'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    department = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    rules = models.TextField(help_text="Event rules and guidelines")
    event_date = models.DateTimeField()
    location = models.CharField(max_length=200)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_team_event = models.BooleanField(default=False)
    team_size = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    banner = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    qr_code = models.ImageField(upload_to='event_qr_codes/', null=True, blank=True)
    qr_code_data = models.TextField(blank=True, help_text="QR code data for payment")
    payment_qr_code = models.ForeignKey(PaymentQRCode, on_delete=models.SET_NULL, null=True, blank=True, related_name='events', help_text="Reusable payment QR code")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_events')
    approved_at = models.DateTimeField(null=True, blank=True)
    hotness_score = models.FloatField(default=0.0)
    average_rating = models.FloatField(default=0.0)
    total_registrations = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'events'
        ordering = ['-event_date', '-created_at']
        indexes = [
            models.Index(fields=['event_date', 'status']),
            models.Index(fields=['category', 'department']),
            models.Index(fields=['-hotness_score']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.event_date.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        """Generate QR code on save if not exists and no image uploaded."""
        # If payment_qr_code is set, use it instead of generating
        if self.payment_qr_code and self.payment_qr_code.qr_code_image:
            # Always copy the QR code from PaymentQRCode to ensure it's updated
            self.qr_code = self.payment_qr_code.qr_code_image
        # Only generate QR code if no QR code image exists, no payment_qr_code set, and QR code data is provided
        elif not self.qr_code and self.qr_code_data and QRCODE_AVAILABLE:
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(self.qr_code_data)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                filename = f'event_{self.id or uuid.uuid4()}_qr.png'
                self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
            except Exception:
                pass  # QR code generation failed, continue without it
        
        super().save(*args, **kwargs)
    
    def get_qr_code_image(self):
        """Get the QR code image, either from payment_qr_code or qr_code field."""
        if self.payment_qr_code and self.payment_qr_code.qr_code_image:
            return self.payment_qr_code.qr_code_image
        return self.qr_code
    
    def is_registration_open(self):
        """Check if registration is still open."""
        return self.status == 'approved' and self.event_date > timezone.now() and self.total_registrations < self.capacity
    
    def get_available_spots(self):
        """Get remaining available spots."""
        return max(0, self.capacity - self.total_registrations)
    
    def update_hotness_score(self):
        """Calculate and update hotness score."""
        # Weighted: 60% registrations, 40% ratings
        reg_score = min(self.total_registrations / max(self.capacity, 1) * 100, 100)
        rating_score = self.average_rating * 20  # Convert 0-5 to 0-100
        
        self.hotness_score = (reg_score * 0.6) + (rating_score * 0.4)
        self.save(update_fields=['hotness_score'])


class Registration(models.Model):
    """Event registration model."""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    team_name = models.CharField(max_length=100, blank=True)
    team_members = models.ManyToManyField(User, related_name='team_registrations', blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_verification_code = models.CharField(max_length=100, blank=True, help_text="UPI Transaction ID")
    upi_id = models.CharField(max_length=100, blank=True, help_text="UPI ID used for transaction")
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_registrations')
    verified_at = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'registrations'
        unique_together = [['event', 'user']]
        ordering = ['-registered_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.event.title}"
    
    def verify_payment(self, verifier):
        """Verify payment and update registration."""
        self.is_verified = True
        self.payment_status = 'verified'
        self.verified_by = verifier
        self.verified_at = timezone.now()
        self.save()
        
        # Update event registration count
        if self.is_verified:
            self.event.total_registrations += 1
            self.event.save(update_fields=['total_registrations'])
            self.event.update_hotness_score()


class EventRecommendation(models.Model):
    """Event recommendations for users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='recommendations')
    score = models.FloatField(default=0.0)
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'event_recommendations'
        unique_together = [['user', 'event']]
        ordering = ['-score']
    
    def __str__(self):
        return f"{self.user.username} - {self.event.title} (Score: {self.score})"

