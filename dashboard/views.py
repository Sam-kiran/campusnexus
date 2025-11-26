from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import json

from events.models import Event, Registration
from feedback.models import Feedback, FeedbackAnalytics
from users.models import User, Leaderboard
from .utils import generate_analytics_report, export_to_csv, export_to_pdf


@login_required
def student_dashboard(request):
    """Student dashboard."""
    if not request.user.is_student():
        messages.error(request, 'Access denied.')
        return redirect('users:home')
    
    # Get user's registrations
    registrations = Registration.objects.filter(
        user=request.user,
        is_verified=True
    ).select_related('event').order_by('-registered_at')
    
    # Upcoming events
    upcoming_registrations = [
        reg for reg in registrations 
        if reg.event.event_date > timezone.now() and reg.event.status == 'approved'
    ]

    # If the user has no personal upcoming registrations, show general upcoming events
    upcoming_events = []
    if not upcoming_registrations:
        upcoming_events = list(Event.objects.filter(
            status='approved',
            event_date__gt=timezone.now()
        ).order_by('event_date')[:5])
    
    # Past events
    past_registrations = [
        reg for reg in registrations 
        if reg.event.event_date <= timezone.now() or reg.event.status == 'completed'
    ]
    
    # Events needing feedback
    events_needing_feedback = []
    for reg in past_registrations:
        if not Feedback.objects.filter(event=reg.event, user=request.user).exists():
            events_needing_feedback.append(reg.event)
    
    # Get leaderboard position
    try:
        leaderboard = Leaderboard.objects.get(user=request.user)
        rank = Leaderboard.objects.filter(total_points__gt=leaderboard.total_points).count() + 1
        leaderboard.rank = rank
        leaderboard.save()
    except Leaderboard.DoesNotExist:
        leaderboard = Leaderboard.objects.create(user=request.user)
        rank = Leaderboard.objects.count()
    
    # Get hot events
    hot_events = Event.objects.filter(
        status='approved',
        hotness_score__gte=50,
        event_date__gt=timezone.now()
    ).order_by('-hotness_score')[:5]
    
    # Get recommendations
    from events.utils import calculate_recommendations
    calculate_recommendations(request.user)
    from events.models import EventRecommendation
    recommendations = EventRecommendation.objects.filter(
        user=request.user,
        event__status='approved',
        event__event_date__gt=timezone.now()
    ).select_related('event').order_by('-score')[:5]
    
    context = {
        'upcoming_registrations': upcoming_registrations[:5],
        'upcoming_events': upcoming_events,
        'past_registrations': past_registrations[:5],
        'events_needing_feedback': events_needing_feedback[:5],
        'leaderboard': leaderboard,
        'rank': rank,
        'hot_events': hot_events,
        'recommendations': [rec.event for rec in recommendations],
    }
    return render(request, 'dashboard/student_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """Admin/Organizer dashboard."""
    if not request.user.is_admin_or_organizer():
        messages.error(request, 'Access denied.')
        return redirect('users:home')
    
    # Get events based on role
    if request.user.is_admin():
        events = Event.objects.all()
    else:
        events = Event.objects.filter(created_by=request.user)
    
    # Statistics
    total_events = events.count()
    approved_events = events.filter(status='approved').count()
    pending_events = events.filter(status='pending').count()
    total_registrations = Registration.objects.filter(
        event__in=events,
        is_verified=True
    ).count()
    total_feedbacks = Feedback.objects.filter(event__in=events).count()
    
    # Recent events
    recent_events = events.order_by('-created_at')[:10]
    
    # Department-wise stats
    dept_stats = events.values('department').annotate(
        count=Count('id'),
        registrations=Sum('total_registrations')
    ).order_by('-count')
    
    # Category-wise stats
    category_stats = events.values('category').annotate(
        count=Count('id'),
        avg_rating=Avg('average_rating')
    ).order_by('-count')
    
    # Time-based trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    events_trend = events.filter(created_at__gte=thirty_days_ago).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    # Sentiment analysis summary
    sentiment_stats = {
        'positive': Feedback.objects.filter(
            event__in=events,
            sentiment_label='positive'
        ).count(),
        'neutral': Feedback.objects.filter(
            event__in=events,
            sentiment_label='neutral'
        ).count(),
        'negative': Feedback.objects.filter(
            event__in=events,
            sentiment_label='negative'
        ).count(),
    }
    
    # Top performing events
    top_events = events.filter(status='approved').order_by('-hotness_score')[:10]
    
    context = {
        'total_events': total_events,
        'approved_events': approved_events,
        'pending_events': pending_events,
        'total_registrations': total_registrations,
        'total_feedbacks': total_feedbacks,
        'recent_events': recent_events,
        'dept_stats': list(dept_stats),
        'category_stats': list(category_stats),
        'events_trend': list(events_trend),
        'sentiment_stats': sentiment_stats,
        'top_events': top_events,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def leaderboard_view(request):
    """Leaderboard view for students."""
    leaderboard = Leaderboard.objects.select_related('user').order_by('-total_points', '-total_events_attended')[:100]
    
    # Get current user's rank
    try:
        user_leaderboard = Leaderboard.objects.get(user=request.user)
        user_rank = Leaderboard.objects.filter(
            Q(total_points__gt=user_leaderboard.total_points) |
            (Q(total_points=user_leaderboard.total_points) & Q(total_events_attended__gt=user_leaderboard.total_events_attended))
        ).count() + 1
    except Leaderboard.DoesNotExist:
        user_rank = None
    
    context = {
        'leaderboard': leaderboard,
        'user_rank': user_rank,
    }
    return render(request, 'dashboard/leaderboard.html', context)


@login_required
def export_report(request, format_type='csv'):
    """Export analytics report."""
    if not request.user.is_admin_or_organizer():
        messages.error(request, 'Access denied.')
        return redirect('dashboard:admin_dashboard')
    
    # Get events based on role
    if request.user.is_admin():
        events = Event.objects.all()
    else:
        events = Event.objects.filter(created_by=request.user)
    
    if format_type == 'csv':
        response = export_to_csv(events, request.user)
        return response
    elif format_type == 'pdf':
        response = export_to_pdf(events, request.user)
        return response
    else:
        messages.error(request, 'Invalid format.')
        return redirect('dashboard:admin_dashboard')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_api(request):
    """API endpoint for dashboard analytics."""
    if not request.user.is_admin_or_organizer():
        return Response({'error': 'Permission denied'}, status=403)
    
    # Get events based on role
    if request.user.is_admin():
        events = Event.objects.all()
    else:
        events = Event.objects.filter(created_by=request.user)
    
    # Department stats
    dept_stats = list(events.values('department').annotate(
        count=Count('id'),
        registrations=Sum('total_registrations')
    ).order_by('-count'))
    
    # Category stats
    category_stats = list(events.values('category').annotate(
        count=Count('id'),
        avg_rating=Avg('average_rating')
    ).order_by('-count'))
    
    # Time trends (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    events_trend = list(events.filter(created_at__gte=seven_days_ago).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day'))
    
    # Sentiment trends
    sentiment_trends = list(Feedback.objects.filter(
        event__in=events,
        created_at__gte=seven_days_ago
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day', 'sentiment_label').annotate(count=Count('id')).order_by('day'))
    
    return Response({
        'department_stats': dept_stats,
        'category_stats': category_stats,
        'events_trend': events_trend,
        'sentiment_trends': sentiment_trends,
    })

