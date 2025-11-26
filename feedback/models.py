from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import User
from events.models import Event, Registration


class Feedback(models.Model):
    """Feedback model for events."""
    EMOTION_CHOICES = [
        ('😊', 'Happy'),
        ('😢', 'Sad'),
        ('😮', 'Surprised'),
        ('😍', 'Love'),
        ('😴', 'Bored'),
        ('🤔', 'Thoughtful'),
        ('😎', 'Cool'),
        ('🙂', 'Neutral'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    registration = models.ForeignKey(Registration, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=500, blank=True)
    emotion = models.CharField(max_length=10, choices=EMOTION_CHOICES, default='🙂')
    sentiment_score = models.FloatField(null=True, blank=True, help_text="AI-generated sentiment score (-1 to 1)")
    sentiment_label = models.CharField(max_length=20, blank=True, help_text="AI-generated sentiment label")
    is_anonymous = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'feedback'
        unique_together = [['event', 'user']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback for {self.event.title} - {self.rating} stars"
    
    def save(self, *args, **kwargs):
        """Update event average rating on save."""
        super().save(*args, **kwargs)
        self.update_event_rating()
    
    def update_event_rating(self):
        """Update event's average rating."""
        avg_rating = Feedback.objects.filter(event=self.event).aggregate(
            avg=models.Avg('rating')
        )['avg'] or 0.0
        
        self.event.average_rating = round(avg_rating, 2)
        self.event.save(update_fields=['average_rating'])
        self.event.update_hotness_score()


class FeedbackAnalytics(models.Model):
    """Aggregated feedback analytics."""
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='analytics')
    total_feedbacks = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    positive_sentiment_count = models.IntegerField(default=0)
    neutral_sentiment_count = models.IntegerField(default=0)
    negative_sentiment_count = models.IntegerField(default=0)
    emotion_distribution = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'feedback_analytics'
        verbose_name_plural = 'Feedback Analytics'
    
    def __str__(self):
        return f"Analytics for {self.event.title}"

