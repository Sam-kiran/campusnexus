"""Celery beat schedule configuration."""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'schedule-event-reminders': {
        'task': 'events.tasks.schedule_event_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
    'schedule-feedback-reminders': {
        'task': 'events.tasks.schedule_feedback_reminders',
        'schedule': crontab(hour=10, minute=0),  # Run daily at 10 AM
    },
    'update-leaderboard': {
        'task': 'events.tasks.update_leaderboard',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
}

