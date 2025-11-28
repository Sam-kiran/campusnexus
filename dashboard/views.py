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
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import csv


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
def management_dashboard(request):
    """Management dashboard with all admin features plus payment tracking."""
    if not request.user.is_management():
        messages.error(request, 'Access denied. Management role required.')
        return redirect('users:home')
    
    # Get all events (management has access to everything)
    events = Event.objects.all()
    
    # Statistics (same as admin)
    total_events = events.count()
    approved_events = events.filter(status='approved').count()
    pending_events = events.filter(status='pending').count()
    total_registrations = Registration.objects.filter(is_verified=True).count()
    total_feedbacks = Feedback.objects.count()
    
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
        'positive': Feedback.objects.filter(sentiment_label='positive').count(),
        'neutral': Feedback.objects.filter(sentiment_label='neutral').count(),
        'negative': Feedback.objects.filter(sentiment_label='negative').count(),
    }
    
    # Top events by registration
    top_events = events.order_by('-total_registrations')[:5]
    
    # PAYMENT TRACKING - Event-wise payment statistics
    payment_stats = []
    for event in events.order_by('-created_at'):
        registrations = Registration.objects.filter(event=event)
        verified_payments = registrations.filter(is_verified=True)
        pending_payments = registrations.filter(is_verified=False)
        
        total_revenue = verified_payments.count() * float(event.fee)
        pending_revenue = pending_payments.count() * float(event.fee)
        
        payment_stats.append({
            'event': event,
            'total_registrations': registrations.count(),
            'verified_payments': verified_payments.count(),
            'pending_payments': pending_payments.count(),
            'total_revenue': total_revenue,
            'pending_revenue': pending_revenue,
            'fee': event.fee,
        })
    
    # Overall payment summary
    all_registrations = Registration.objects.all()
    total_verified_payments = all_registrations.filter(is_verified=True).count()
    total_pending_payments = all_registrations.filter(is_verified=False).count()
    
    # Calculate total revenue
    total_revenue = sum(
        float(reg.event.fee) for reg in all_registrations.filter(is_verified=True)
    )
    pending_revenue = sum(
        float(reg.event.fee) for reg in all_registrations.filter(is_verified=False)
    )
    
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
        # Payment-specific data
        'payment_stats': payment_stats,
        'total_verified_payments': total_verified_payments,
        'total_pending_payments': total_pending_payments,
        'total_revenue': total_revenue,
        'pending_revenue': pending_revenue,
    }
    return render(request, 'dashboard/management_dashboard.html', context)


@login_required
def payment_detail(request, event_id):
    """Per-event payment details for management: list registrations with payment info."""
    if not request.user.is_management():
        messages.error(request, 'Access denied. Management role required.')
        return redirect('users:home')

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise Http404('Event not found')

    registrations = Registration.objects.filter(event=event).select_related('user').order_by('-registered_at')

    context = {
        'event': event,
        'registrations': registrations,
    }
    return render(request, 'dashboard/payment_detail.html', context)


@login_required
def payment_export(request):
    """Export payments CSV (and PDF placeholder) with optional filters: start_date, end_date, event_id."""
    if not request.user.is_management():
        messages.error(request, 'Access denied. Management role required.')
        return redirect('users:home')

    fmt = request.GET.get('format', 'csv')
    event_id = request.GET.get('event_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    qs = Registration.objects.select_related('event', 'user').order_by('-registered_at')
    if event_id:
        qs = qs.filter(event__id=event_id)
    if start_date:
        qs = qs.filter(registered_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(registered_at__date__lte=end_date)

    if fmt == 'csv':
        # Build CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Event', 'Event ID', 'User', 'User Email', 'Registered At', 'Verified', 'Verified By', 'Approval Reason', 'Payment Status', 'UPI ID', 'Transaction ID', 'Fee'])
        for reg in qs:
            writer.writerow([
                reg.event.title,
                reg.event.id,
                reg.user.username,
                reg.user.email,
                reg.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if reg.is_verified else 'No',
                (reg.verified_by.username if reg.verified_by else ''),
                (reg.verification_reason or ''),
                reg.get_payment_status_display(),
                reg.upi_id or '',
                reg.payment_verification_code or '',
                float(reg.event.fee),
            ])
        return response
    else:
        # PDF/export using existing utilities could be added; for now redirect back with message
        messages.error(request, 'Only CSV export currently supported.')
        return redirect('dashboard:management_dashboard')


@login_required
@csrf_exempt
def toggle_payment_verification(request, reg_id):
    """Toggle verification status for a registration (management action)."""
    if not request.user.is_management():
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        reg = Registration.objects.get(id=reg_id)
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    # Approve (verify) using model helper to ensure event counters and hotness update
    if not reg.is_verified:
        try:
            reg.verify_payment(request.user)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        return JsonResponse({'success': True, 'is_verified': True, 'verified_by': reg.verified_by.username if reg.verified_by else None})
    else:
        # Un-verify: revert verification and adjust event counters
        try:
            reg.is_verified = False
            reg.payment_status = 'pending'
            reg.verified_by = None
            reg.verification_reason = ''
            reg.verified_at = None
            reg.save()

            # Decrement event registration count safely
            if reg.event.total_registrations and reg.event.total_registrations > 0:
                reg.event.total_registrations = max(0, reg.event.total_registrations - 1)
                reg.event.save(update_fields=['total_registrations'])
                reg.event.update_hotness_score()
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        return JsonResponse({'success': True, 'is_verified': False})


@login_required
def approve_payment(request, reg_id):
    """Approve a payment with an optional reason (management action)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if not request.user.is_management():
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        reg = Registration.objects.get(id=reg_id)
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)

    reason = request.POST.get('reason') or request.POST.get('approval_reason') or ''

    if reg.is_verified:
        return JsonResponse({'error': 'Already verified'}, status=400)

    try:
        reg.verify_payment(request.user, reason=reason)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'is_verified': True, 'verified_by': reg.verified_by.username if reg.verified_by else None, 'reason': reg.verification_reason})


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
    # Allow admins, organizers and management users to export reports
    if not (request.user.is_admin_or_organizer() or request.user.is_management()):
        messages.error(request, 'Access denied.')
        return redirect('users:home')
    
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


@login_required
def hotness_api(request):
    """Return hotness per department for charts (accessible to authenticated users)."""
    # Aggregate hotness per department
    qs = Event.objects.all()
    dept_hotness = list(qs.values('department').annotate(total_hotness=Sum('hotness_score')).order_by('-total_hotness'))

    data = {
        'labels': [d['department'] or 'Unknown' for d in dept_hotness],
        'values': [float(d['total_hotness'] or 0) for d in dept_hotness]
    }
    return JsonResponse(data)

