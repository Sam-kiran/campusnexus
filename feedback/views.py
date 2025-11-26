from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Avg, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Feedback, FeedbackAnalytics
from events.models import Event, Registration
from .utils import analyze_sentiment, update_feedback_analytics
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings


@login_required
def feedback_create(request, event_id):
    """Create feedback for an event."""
    if not request.user.is_student():
        messages.error(request, 'Only students can submit feedback.')
        return redirect('events:event_detail', event_id=event_id)
    
    event = get_object_or_404(Event, id=event_id, status='approved')
    
    # Check if user registered and event is completed
    try:
        registration = Registration.objects.get(event=event, user=request.user, is_verified=True)
    except Registration.DoesNotExist:
        messages.error(request, 'You must be registered and verified to submit feedback.')
        return redirect('events:event_detail', event_id=event_id)
    
    # Check if feedback already exists
    if Feedback.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, 'You have already submitted feedback for this event.')
        return redirect('events:event_detail', event_id=event_id)
    
    # Check if event is completed
    from django.utils import timezone
    if event.event_date > timezone.now():
        messages.error(request, 'Event has not completed yet.')
        return redirect('events:event_detail', event_id=event_id)
    
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '')
        emotion = request.POST.get('emotion', '🙂')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        
        # Validate comment length
        if len(comment) > 500:
            messages.error(request, 'Comment must be 500 characters or less.')
            return render(request, 'feedback/feedback_create.html', {'event': event})
        
        feedback = Feedback.objects.create(
            event=event,
            user=request.user,
            registration=registration,
            rating=rating,
            comment=comment,
            emotion=emotion,
            is_anonymous=is_anonymous,
        )
        
        # Analyze sentiment
        if comment:
            sentiment_result = analyze_sentiment(comment)
            feedback.sentiment_score = sentiment_result.get('score')
            feedback.sentiment_label = sentiment_result.get('label', 'neutral')
            feedback.save()
        
        # Update analytics
        update_feedback_analytics(event)

        # Notify organizer about new feedback
        try:
            organizer_email = event.created_by.email if event.created_by else None
            if organizer_email:
                subject = f'New feedback for your event: {event.title}'
                body = render_to_string('feedback/new_feedback_notification.txt', {'event': event, 'feedback': feedback})
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [organizer_email], fail_silently=True)
        except Exception:
            pass
        
        messages.success(request, 'Feedback submitted successfully!')
        return redirect('events:event_detail', event_id=event_id)
    
    return render(request, 'feedback/feedback_create.html', {
        'event': event,
        'emotions': Feedback.EMOTION_CHOICES,
    })


@login_required
def feedback_list(request, event_id):
    """List all feedbacks for an event."""
    event = get_object_or_404(Event, id=event_id)
    
    # Only admin/organizer can see all feedbacks
    if not request.user.is_admin_or_organizer():
        messages.error(request, 'You do not have permission to view this.')
        return redirect('events:event_detail', event_id=event_id)
    
    feedbacks = Feedback.objects.filter(event=event).select_related('user')
    
    context = {
        'event': event,
        'feedbacks': feedbacks,
        'average_rating': feedbacks.aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    return render(request, 'feedback/feedback_list.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def feedback_stats_api(request, event_id):
    """API endpoint for feedback statistics."""
    event = get_object_or_404(Event, id=event_id)
    
    if not request.user.is_admin_or_organizer():
        return Response({'error': 'Permission denied'}, status=403)
    
    feedbacks = Feedback.objects.filter(event=event)
    
    stats = {
        'total_feedbacks': feedbacks.count(),
        'average_rating': feedbacks.aggregate(Avg('rating'))['rating__avg'] or 0,
        'rating_distribution': {
            '5': feedbacks.filter(rating=5).count(),
            '4': feedbacks.filter(rating=4).count(),
            '3': feedbacks.filter(rating=3).count(),
            '2': feedbacks.filter(rating=2).count(),
            '1': feedbacks.filter(rating=1).count(),
        },
        'sentiment_distribution': {
            'positive': feedbacks.filter(sentiment_label='positive').count(),
            'neutral': feedbacks.filter(sentiment_label='neutral').count(),
            'negative': feedbacks.filter(sentiment_label='negative').count(),
        },
        'emotion_distribution': {}
    }
    
    # Emotion distribution
    for emotion_code, emotion_name in Feedback.EMOTION_CHOICES:
        stats['emotion_distribution'][emotion_code] = feedbacks.filter(emotion=emotion_code).count()
    
    return Response(stats)

