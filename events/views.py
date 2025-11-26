from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.template.loader import render_to_string
from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Event, Registration, EventRecommendation, PaymentQRCode
from users.models import User
from .utils import (
    calculate_recommendations,
    generate_event_poster,
    analyze_basic_sentiment,
)
import json
import logging
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


def is_admin_or_organizer(user):
    return user.is_authenticated and user.is_admin_or_organizer()


@login_required
def event_list(request):
    """List all events with filtering."""
    events = Event.objects.filter(status='approved')
    
    # Filters
    category = request.GET.get('category')
    department = request.GET.get('department')
    search = request.GET.get('search')
    
    if category:
        events = events.filter(category=category)
    if department:
        events = events.filter(department=department)
    if search:
        events = events.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    # Hot events
    hot_events = events.filter(hotness_score__gte=50).order_by('-hotness_score')[:5]
    
    context = {
        'events': events.order_by('-event_date'),
        'hot_events': hot_events,
        'categories': Event.CATEGORY_CHOICES,
    }
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, event_id):
    """Event detail page with registration."""
    # Allow viewing if approved, or if user is creator/admin
    event = get_object_or_404(Event, id=event_id)
    
    # Check if user can view this event
    can_view = (
        event.status == 'approved' or
        request.user.is_admin() or
        (request.user.is_organizer() and event.created_by == request.user)
    )
    
    if not can_view:
        messages.error(request, 'This event is not available or pending approval.')
        return redirect('events:event_list')
    
    # Handle registration POST request
    if request.method == 'POST' and request.user.is_student():
        # Check if already registered
        if Registration.objects.filter(event=event, user=request.user).exists():
            messages.warning(request, 'You are already registered for this event.')
            return redirect('events:event_detail', event_id=event_id)
        
        # Check capacity
        if event.total_registrations >= event.capacity:
            messages.error(request, 'Event is full.')
            return redirect('events:event_detail', event_id=event_id)
        
        # Check if event date has passed
        if event.event_date <= timezone.now():
            messages.error(request, 'Event registration is closed.')
            return redirect('events:event_detail', event_id=event_id)
        
        # Validate team event requirements BEFORE creating registration
        if event.is_team_event:
            # Validate team name is provided
            team_name = request.POST.get('team_name', '').strip()
            if not team_name:
                messages.error(request, 'Team name is required for team events.')
                return redirect('events:event_detail', event_id=event_id)
            
            team_member_ids = request.POST.getlist('team_members')
            # Validate team size
            required_members = event.team_size - 1  # Excluding the current user
            if len(team_member_ids) != required_members:
                messages.error(request, f'Please select exactly {required_members} team member(s) (excluding yourself).')
                return redirect('events:event_detail', event_id=event_id)
            
            # Validate no duplicate team members
            if len(team_member_ids) != len(set(team_member_ids)):
                messages.error(request, 'You cannot select the same team member multiple times.')
                return redirect('events:event_detail', event_id=event_id)
            
            # Validate team members exist and are not already registered
            validated_members = []
            for member_id in team_member_ids:
                try:
                    member = User.objects.get(id=member_id, role='student')
                    # Check if member is already registered for this event
                    if Registration.objects.filter(event=event, user=member).exists():
                        messages.error(request, f'{member.username} is already registered for this event.')
                        return redirect('events:event_detail', event_id=event_id)
                    validated_members.append(member)
                except User.DoesNotExist:
                    messages.error(request, 'One or more selected team members are invalid.')
                    return redirect('events:event_detail', event_id=event_id)
        
        # Create registration after all validations pass
        registration = Registration.objects.create(
            event=event,
            user=request.user,
            team_name=request.POST.get('team_name', '').strip() if event.is_team_event else '',
            payment_verification_code=request.POST.get('payment_verification_code', ''),
            upi_id=request.POST.get('upi_id', ''),
        )
        
        if 'payment_screenshot' in request.FILES:
            registration.payment_screenshot = request.FILES['payment_screenshot']
            registration.save()
        
        # Add validated team members if team event
        if event.is_team_event:
            for member in validated_members:
                registration.team_members.add(member)
        
        # Send confirmation to student and notify organizer
        try:
            subject = f'Registration received: {event.title}'
            body = render_to_string('events/registration_confirmation.txt', {'event': event, 'registration': registration, 'user': request.user})
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [request.user.email], fail_silently=True)

            organizer_email = event.created_by.email if event.created_by else None
            if organizer_email:
                subject_org = f'New registration for your event: {event.title}'
                body_org = render_to_string('events/new_registration_notification.txt', {'event': event, 'registration': registration})
                send_mail(subject_org, body_org, settings.DEFAULT_FROM_EMAIL, [organizer_email], fail_silently=True)
        except Exception:
            pass

        messages.success(request, '✅ Successfully Registered! Your payment verification is pending. You will receive a confirmation once your payment is verified.')
        return redirect('events:event_detail', event_id=event_id)
    
    # Check if user is registered
    is_registered = False
    registration = None
    if request.user.is_student():
        try:
            registration = Registration.objects.get(event=event, user=request.user)
            is_registered = True
        except Registration.DoesNotExist:
            pass
    
    # Get recommendations
    recommendations = EventRecommendation.objects.filter(
        user=request.user,
        event__status='approved'
    ).select_related('event').order_by('-score')[:5] if request.user.is_student() else []
    
    # Get available team members for team events (always get them if it's a team event, even if user can't register)
    if event.is_team_event:
        if request.user.is_authenticated and request.user.is_student():
            # Exclude the current user from the list
            team_members = User.objects.filter(role='student').exclude(id=request.user.id)
        else:
            # For non-students or unauthenticated users, show all students (for display purposes)
            team_members = User.objects.filter(role='student')
    else:
        team_members = []
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'registration': registration,
        'recommendations': [rec.event for rec in recommendations],
        'available_spots': event.get_available_spots(),
        'now': timezone.now(),
        'team_members': team_members,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
@user_passes_test(is_admin_or_organizer)
def event_create(request):
    """Create new event."""
    if request.method == 'POST':
        try:
            # Parse datetime
            event_date_str = request.POST.get('event_date')
            if not event_date_str:
                messages.error(request, 'Event date is required.')
                return render(request, 'events/event_create.html', {
                    'categories': Event.CATEGORY_CHOICES,
                })
            
            # Convert datetime-local format (YYYY-MM-DDTHH:MM) to datetime
            try:
                # Try parsing with timezone
                event_date = parse_datetime(event_date_str.replace('T', ' '))
                if not event_date:
                    # Fallback: parse without timezone
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
                    # Make timezone aware
                    event_date = timezone.make_aware(event_date)
            except ValueError:
                # Try alternative format
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d %H:%M:%S')
                    event_date = timezone.make_aware(event_date)
                except ValueError:
                    messages.error(request, 'Invalid date format. Please use the date picker.')
                    return render(request, 'events/event_create.html', {
                        'categories': Event.CATEGORY_CHOICES,
                    })
            
            # Determine status - admin can create approved events directly
            if request.user.is_admin():
                status = 'approved'
            else:
                status = 'pending'
            
            # Handle QR code selection/upload
            payment_qr_code_id = request.POST.get('payment_qr_code_id', '').strip()
            qr_code_name = request.POST.get('qr_code_name', '').strip()
            
            payment_qr_code = None
            if payment_qr_code_id:
                # Use existing QR code
                try:
                    payment_qr_code = PaymentQRCode.objects.get(id=payment_qr_code_id, is_active=True)
                except PaymentQRCode.DoesNotExist:
                    pass
            elif 'qr_code' in request.FILES and qr_code_name:
                # Create new reusable QR code from upload
                payment_qr_code = PaymentQRCode.objects.create(
                    name=qr_code_name,
                    qr_code_image=request.FILES['qr_code'],
                    qr_code_data=request.POST.get('qr_code_data', ''),
                    created_by=request.user,
                )
            
            event = Event.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                department=request.POST.get('department'),
                category=request.POST.get('category'),
                rules=request.POST.get('rules'),
                event_date=event_date,
                location=request.POST.get('location'),
                capacity=int(request.POST.get('capacity', 1)),
                fee=float(request.POST.get('fee', 0)),
                is_team_event=request.POST.get('is_team_event') == 'on',
                team_size=int(request.POST.get('team_size', 1)) if request.POST.get('is_team_event') == 'on' else 1,
                qr_code_data=request.POST.get('qr_code_data', '') if not payment_qr_code else '',
                payment_qr_code=payment_qr_code,
                created_by=request.user,
                status=status,
            )
            
            # Handle direct QR code upload (if not using reusable QR code)
            if not payment_qr_code and 'qr_code' in request.FILES:
                event.qr_code = request.FILES['qr_code']
            
            # Handle banner - either upload or AI generation
            generate_ai_banner = request.POST.get('generate_ai_banner') == 'on'
            
            if 'banner' in request.FILES:
                # User uploaded their own banner
                event.banner = request.FILES['banner']
            elif generate_ai_banner:
                # Generate AI banner
                from .utils import generate_event_banner_ai
                banner_result = generate_event_banner_ai(event)
                if banner_result.get('success'):
                    event.banner = banner_result['image_file']
                    generated_note = banner_result.get('generated_via') or banner_result.get('message')
                    if generated_note:
                        messages.info(request, generated_note)
                else:
                    messages.warning(request, f'AI banner generation failed: {banner_result.get("error", "Unknown error")}. You can add a banner later by editing the event.')
            
            event.save()

            # Notify admins if event is pending approval
            if status == 'approved':
                messages.success(request, 'Event created and approved successfully!')
            else:
                messages.success(request, 'Event created successfully! Waiting for admin approval.')
                try:
                    admin_emails = list(User.objects.filter(role='admin').values_list('email', flat=True))
                    if admin_emails:
                        subject = f'New event awaiting approval: {event.title}'
                        body = render_to_string('events/new_event_for_approval.txt', {'event': event, 'creator': request.user})
                        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=True)
                except Exception:
                    pass
            
            return redirect('events:event_detail', event_id=event.id)
        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')
            import traceback
            logger.error(f"Event creation error: {traceback.format_exc()}")
            existing_qr_codes = PaymentQRCode.objects.filter(is_active=True).order_by('-created_at')
            return render(request, 'events/event_create.html', {
                'categories': Event.CATEGORY_CHOICES,
                'existing_qr_codes': existing_qr_codes,
            })
    
    # Get all existing payment QR codes for dropdown
    existing_qr_codes = PaymentQRCode.objects.filter(is_active=True).order_by('-created_at')
    
    return render(request, 'events/event_create.html', {
        'categories': Event.CATEGORY_CHOICES,
        'existing_qr_codes': existing_qr_codes,
    })


@login_required
@user_passes_test(is_admin_or_organizer)
def event_edit(request, event_id):
    """Edit existing event."""
    event = get_object_or_404(Event, id=event_id)
    
    if not (event.created_by == request.user or request.user.is_admin()):
        messages.error(request, 'You do not have permission to edit this event.')
        return redirect('events:event_detail', event_id=event.id)
    
    if request.method == 'POST':
        try:
            event.title = request.POST.get('title')
            event.description = request.POST.get('description')
            event.department = request.POST.get('department')
            event.category = request.POST.get('category')
            event.rules = request.POST.get('rules')
            
            # Parse datetime
            event_date_str = request.POST.get('event_date')
            if event_date_str:
                try:
                    # Try parsing with timezone
                    event_date = parse_datetime(event_date_str.replace('T', ' '))
                    if not event_date:
                        # Fallback: parse without timezone
                        event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
                        # Make timezone aware
                        event_date = timezone.make_aware(event_date)
                    event.event_date = event_date
                except ValueError:
                    # Try alternative format
                    try:
                        event_date = datetime.strptime(event_date_str, '%Y-%m-%d %H:%M:%S')
                        event.event_date = timezone.make_aware(event_date)
                    except ValueError:
                        messages.error(request, 'Invalid date format. Please use the date picker.')
            
            event.location = request.POST.get('location')
            event.capacity = int(request.POST.get('capacity', 1))
            event.fee = float(request.POST.get('fee', 0))
            event.is_team_event = request.POST.get('is_team_event') == 'on'
            event.team_size = int(request.POST.get('team_size', 1)) if event.is_team_event else 1
            
            # Handle QR code selection/upload
            payment_qr_code_id = request.POST.get('payment_qr_code_id', '').strip()
            qr_code_name = request.POST.get('qr_code_name', '').strip()
            
            if payment_qr_code_id:
                # Use existing QR code
                try:
                    event.payment_qr_code = PaymentQRCode.objects.get(id=payment_qr_code_id, is_active=True)
                    event.qr_code_data = ''  # Clear data if using reusable QR code
                except PaymentQRCode.DoesNotExist:
                    pass
            elif 'qr_code' in request.FILES and qr_code_name:
                # Create new reusable QR code from upload
                payment_qr_code = PaymentQRCode.objects.create(
                    name=qr_code_name,
                    qr_code_image=request.FILES['qr_code'],
                    qr_code_data=request.POST.get('qr_code_data', ''),
                    created_by=request.user,
                )
                event.payment_qr_code = payment_qr_code
                event.qr_code_data = ''
            elif 'qr_code' in request.FILES:
                # Direct upload without creating reusable QR code
                event.qr_code = request.FILES['qr_code']
                event.payment_qr_code = None
                event.qr_code_data = request.POST.get('qr_code_data', '')
            else:
                # Keep existing or use data
                event.qr_code_data = request.POST.get('qr_code_data', '')
            
            # Handle banner - either upload or AI generation
            generate_ai_banner = request.POST.get('generate_ai_banner') == 'on'
            
            if 'banner' in request.FILES:
                # User uploaded their own banner
                event.banner = request.FILES['banner']
            elif generate_ai_banner:
                # Generate AI banner
                from .utils import generate_event_banner_ai
                banner_result = generate_event_banner_ai(event)
                if banner_result.get('success'):
                    event.banner = banner_result['image_file']
                    generated_note = banner_result.get('generated_via') or banner_result.get('message')
                    if generated_note:
                        messages.info(request, generated_note)
                else:
                    messages.warning(request, f'AI banner generation failed: {banner_result.get("error", "Unknown error")}. You can add a banner later by editing the event.')
            
            event.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('events:event_detail', event_id=event.id)
        except Exception as e:
            messages.error(request, f'Error updating event: {str(e)}')
            import traceback
            logger.error(f"Event update error: {traceback.format_exc()}")
    
    # Get all existing payment QR codes for dropdown
    existing_qr_codes = PaymentQRCode.objects.filter(is_active=True).order_by('-created_at')
    
    return render(request, 'events/event_edit.html', {
        'event': event,
        'categories': Event.CATEGORY_CHOICES,
        'existing_qr_codes': existing_qr_codes,
    })


@login_required
@user_passes_test(is_admin_or_organizer)
def event_delete(request, event_id):
    """Delete event."""
    event = get_object_or_404(Event, id=event_id)
    
    if not (event.created_by == request.user or request.user.is_admin()):
        messages.error(request, 'You do not have permission to delete this event.')
        return redirect('events:event_detail', event_id=event.id)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('events:event_list')
    
    return render(request, 'events/event_confirm_delete.html', {'event': event})


@login_required
@user_passes_test(lambda u: u.is_admin())
def event_approve(request, event_id):
    """Approve event (Admin only)."""
    event = get_object_or_404(Event, id=event_id, status='pending')
    
    if request.method == 'POST':
        event.status = 'approved'
        event.approved_by = request.user
        event.approved_at = timezone.now()
        event.save()
        messages.success(request, 'Event approved successfully!')
        # Notify organizer about approval
        try:
            organizer = event.created_by
            subject = f'Your event has been approved: {event.title}'
            body = render_to_string('events/event_approved.txt', {'event': event, 'admin': request.user})
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [organizer.email], fail_silently=True)
        except Exception:
            pass
    
    return redirect('events:event_detail', event_id=event.id)


@login_required
@user_passes_test(lambda u: u.is_admin())
def event_reject(request, event_id):
    """Reject event with a reason (Admin only)."""
    event = get_object_or_404(Event, id=event_id, status='pending')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        # Mark as cancelled and record approval metadata
        event.status = 'cancelled'
        event.approved_by = request.user
        event.approved_at = timezone.now()
        event.save()

        # Notify organizer with reason
        try:
            organizer = event.created_by
            subject = f'Your event was not approved: {event.title}'
            body = render_to_string('events/event_rejected.txt', {'event': event, 'admin': request.user, 'reason': reason})
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [organizer.email], fail_silently=True)
        except Exception:
            pass

        messages.success(request, 'Event rejected and organizer notified.')

    return redirect('events:event_detail', event_id=event.id)


@login_required
def event_register(request, event_id):
    """Register for an event."""
    if not request.user.is_student():
        messages.error(request, 'Only students can register for events.')
        return redirect('events:event_detail', event_id=event_id)
    
    event = get_object_or_404(Event, id=event_id, status='approved')
    
    # Check if already registered
    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('events:event_detail', event_id=event_id)
    
    # Check capacity
    if event.total_registrations >= event.capacity:
        messages.error(request, 'Event is full.')
        return redirect('events:event_detail', event_id=event_id)
    
    # Check if event date has passed
    if event.event_date <= timezone.now():
        messages.error(request, 'Event registration is closed.')
        return redirect('events:event_detail', event_id=event_id)
    
    if request.method == 'POST':
        # Validate team event requirements BEFORE creating registration
        if event.is_team_event:
            # Validate team name is provided
            team_name = request.POST.get('team_name', '').strip()
            if not team_name:
                messages.error(request, 'Team name is required for team events.')
                return redirect('events:event_register', event_id=event_id)
            
            team_member_ids = request.POST.getlist('team_members')
            # Validate team size
            required_members = event.team_size - 1  # Excluding the current user
            if len(team_member_ids) != required_members:
                messages.error(request, f'Please select exactly {required_members} team member(s) (excluding yourself).')
                return redirect('events:event_register', event_id=event_id)
            
            # Validate no duplicate team members
            if len(team_member_ids) != len(set(team_member_ids)):
                messages.error(request, 'You cannot select the same team member multiple times.')
                return redirect('events:event_register', event_id=event_id)
            
            # Validate team members exist and are not already registered
            validated_members = []
            for member_id in team_member_ids:
                try:
                    member = User.objects.get(id=member_id, role='student')
                    # Check if member is already registered for this event
                    if Registration.objects.filter(event=event, user=member).exists():
                        messages.error(request, f'{member.username} is already registered for this event.')
                        return redirect('events:event_register', event_id=event_id)
                    validated_members.append(member)
                except User.DoesNotExist:
                    messages.error(request, 'One or more selected team members are invalid.')
                    return redirect('events:event_register', event_id=event_id)
        
        # Create registration after all validations pass
        registration = Registration.objects.create(
            event=event,
            user=request.user,
            team_name=request.POST.get('team_name', '').strip() if event.is_team_event else '',
            payment_verification_code=request.POST.get('payment_verification_code', ''),
            upi_id=request.POST.get('upi_id', ''),
        )
        
        if 'payment_screenshot' in request.FILES:
            registration.payment_screenshot = request.FILES['payment_screenshot']
            registration.save()
        
        # Add validated team members if team event
        if event.is_team_event:
            for member in validated_members:
                registration.team_members.add(member)

        # Send confirmation to student and notify organizer
        try:
            # Student confirmation
            subject = f'Registration received: {event.title}'
            body = render_to_string('events/registration_confirmation.txt', {'event': event, 'registration': registration, 'user': request.user})
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [request.user.email], fail_silently=True)

            # Notify organizer
            organizer_email = event.created_by.email if event.created_by else None
            if organizer_email:
                subject_org = f'New registration for your event: {event.title}'
                body_org = render_to_string('events/new_registration_notification.txt', {'event': event, 'registration': registration})
                send_mail(subject_org, body_org, settings.DEFAULT_FROM_EMAIL, [organizer_email], fail_silently=True)
        except Exception:
            pass

        messages.success(request, '✅ Successfully Registered! Your payment verification is pending. You will receive a confirmation once your payment is verified.')
        return redirect('events:event_detail', event_id=event_id)
    
    # Get available team members for team events
    if event.is_team_event:
        if request.user.is_authenticated and request.user.is_student():
            # Exclude the current user from the list
            team_members = User.objects.filter(role='student').exclude(id=request.user.id)
        else:
            # For non-students or unauthenticated users, show all students (for display purposes)
            team_members = User.objects.filter(role='student')
    else:
        team_members = []
    
    return render(request, 'events/event_register.html', {
        'event': event,
        'team_members': team_members,
    })


@login_required
@user_passes_test(is_admin_or_organizer)
def verify_payment(request, registration_id):
    """Verify payment for registration."""
    registration = get_object_or_404(Registration, id=registration_id)
    
    if request.method == 'POST':
        registration.verify_payment(request.user)
        messages.success(request, 'Payment verified successfully!')
        return redirect('events:event_detail', event_id=registration.event.id)
    
    return render(request, 'events/verify_payment.html', {'registration': registration})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hot_events_api(request):
    """API endpoint for hot events."""
    events = Event.objects.filter(
        status='approved',
        hotness_score__gte=50
    ).order_by('-hotness_score')[:10]
    
    data = [{
        'id': event.id,
        'title': event.title,
        'hotness_score': event.hotness_score,
        'total_registrations': event.total_registrations,
        'average_rating': event.average_rating,
    } for event in events]
    
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations_api(request):
    """API endpoint for event recommendations."""
    if not request.user.is_student():
        return Response({'error': 'Only for students'}, status=status.HTTP_403_FORBIDDEN)
    
    # Calculate recommendations if not exists
    calculate_recommendations(request.user)
    
    recommendations = EventRecommendation.objects.filter(
        user=request.user,
        event__status='approved'
    ).select_related('event').order_by('-score')[:10]
    
    data = [{
        'event_id': rec.event.id,
        'event_title': rec.event.title,
        'score': rec.score,
        'reason': rec.reason,
    } for rec in recommendations]
    
    return Response(data)


@login_required
@require_http_methods(['POST'])
def sentiment_analysis_api(request):
    """Basic sentiment check for free-form text (event descriptions, etc.)."""
    text = request.POST.get('text', '').strip()

    if not text:
        return JsonResponse({'error': 'Please provide some text to analyze.'}, status=400)

    result = analyze_basic_sentiment(text)
    summary = {
        'positive': 'Keep the upbeat tone! 🎉',
        'negative': 'Consider softening the language a bit.',
        'neutral': 'Looks neutral—feel free to add more excitement if needed.',
    }

    return JsonResponse({
        'label': result['label'],
        'score': result['score'],
        'confidence': result['confidence'],
        'positive_hits': result['positive_hits'],
        'negative_hits': result['negative_hits'],
        'tip': summary.get(result['label'], ''),
    })

