from django.contrib import admin
from .models import Feedback, FeedbackAnalytics


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'rating', 'emotion', 'sentiment_label', 'is_anonymous', 'created_at']
    list_filter = ['rating', 'emotion', 'sentiment_label', 'is_anonymous', 'created_at']
    search_fields = ['event__title', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FeedbackAnalytics)
class FeedbackAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['event', 'total_feedbacks', 'average_rating', 'positive_sentiment_count', 'last_updated']
    readonly_fields = ['last_updated']

