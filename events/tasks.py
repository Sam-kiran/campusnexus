"""Celery tasks for events."""
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import Event, Registration
from feedback.models import Feedback
from users.models import User


@shared_task
def send_pre_event_reminder(event_id):
    """Send reminder email before event."""
    try:
        event = Event.objects.get(id=event_id, status='approved')
        registrations = Registration.objects.filter(
            event=event,
            is_verified=True
        ).select_related('user')
        
        for registration in registrations:
            send_mail(
                subject=f'Reminder: {event.title} is tomorrow!',
                message=f"""
                Hi {registration.user.username},
                
                This is a reminder that you're registered for:
                
                Event: {event.title}
                Date: {event.event_date.strftime('%Y-%m-%d %H:%M')}
                Location: {event.location}
                
                We look forward to seeing you there!
                
                Best regards,
                CampusNexus Team
                """,
                from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
                recipient_list=[registration.user.email],
                fail_silently=False,
            )
    except Event.DoesNotExist:
        pass


@shared_task
def send_post_event_feedback_reminder(event_id):
    """Send feedback reminder after event."""
    try:
        event = Event.objects.get(id=event_id, status='approved')
        registrations = Registration.objects.filter(
            event=event,
            is_verified=True
        ).select_related('user')
        
        for registration in registrations:
            # Check if feedback already submitted
            if Feedback.objects.filter(event=event, user=registration.user).exists():
                continue
            
            send_mail(
                subject=f'Share your feedback: {event.title}',
                message=f"""
                Hi {registration.user.username},
                
                Thank you for attending {event.title}!
                
                We'd love to hear your thoughts. Please share your feedback:
                {event.get_absolute_url() if hasattr(event, 'get_absolute_url') else ''}
                
                Your feedback helps us improve future events.
                
                Best regards,
                CampusNexus Team
                """,
                from_email=None,
                recipient_list=[registration.user.email],
                fail_silently=False,
            )
    except Event.DoesNotExist:
        pass


@shared_task
def schedule_event_reminders():
    """Schedule reminders for upcoming events."""
    tomorrow = timezone.now() + timedelta(days=1)
    events = Event.objects.filter(
        status='approved',
        event_date__date=tomorrow.date()
    )
    
    for event in events:
        send_pre_event_reminder.delay(event.id)


@shared_task
def schedule_feedback_reminders():
    """Schedule feedback reminders for completed events."""
    yesterday = timezone.now() - timedelta(days=1)
    events = Event.objects.filter(
        status='approved',
        event_date__lte=yesterday,
        event_date__gte=yesterday - timedelta(days=1)
    )
    
    for event in events:
        send_post_event_feedback_reminder.delay(event.id)


@shared_task
def update_leaderboard():
    """Update leaderboard scores."""
    from users.models import Leaderboard
    
    for user in User.objects.filter(role='student'):
        leaderboard, created = Leaderboard.objects.get_or_create(user=user)
        
        # Count verified registrations
        leaderboard.total_events_attended = Registration.objects.filter(
            user=user,
            is_verified=True
        ).count()
        
        # Count feedback given
        leaderboard.total_feedback_given = Feedback.objects.filter(user=user).count()
        
        # Calculate points (10 per event + 5 per feedback)
        leaderboard.total_points = (
            leaderboard.total_events_attended * 10 +
            leaderboard.total_feedback_given * 5
        )
        
        leaderboard.save()
    
    # Update ranks
    leaderboards = Leaderboard.objects.order_by('-total_points', '-total_events_attended')
    for rank, leaderboard in enumerate(leaderboards, start=1):
        leaderboard.rank = rank
        leaderboard.save(update_fields=['rank'])

