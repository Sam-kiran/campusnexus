from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import User, Leaderboard
from .utils import validate_supabase_auth, create_supabase_user
import json
import random
from .models import EmailVerification

# Optional Celery task for sending verification emails
try:
    from .tasks import send_verification_email
except Exception:
    send_verification_email = None


def home(request):
    """Home page - redirects based on user role."""
    if request.user.is_authenticated:
        if request.user.is_student():
            return redirect('dashboard:student_dashboard')
        elif request.user.is_management():
            return redirect('dashboard:management_dashboard')
        elif request.user.is_admin_or_organizer():
            return redirect('dashboard:admin_dashboard')
    return redirect('users:login')


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Login view with optional Supabase integration."""
    if request.user.is_authenticated:
        return redirect('users:home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')
        
        from django.conf import settings
        
        # Try Supabase if configured, otherwise use Django auth
        if settings.SUPABASE_URL:
            # Validate with Supabase
            supabase_user = validate_supabase_auth(email, password)
            
            if supabase_user:
                try:
                    # Get Django user
                    user = User.objects.get(email=email)
                    if user.role != role:
                        messages.error(request, 'Invalid role for this account.')
                        return render(request, 'users/login.html')
                    
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    if user.is_student():
                        return redirect('dashboard:student_dashboard')
                    elif user.is_management():
                        return redirect('dashboard:management_dashboard')
                    else:
                        return redirect('dashboard:admin_dashboard')
                except User.DoesNotExist:
                    messages.error(request, 'User not found. Please sign up first.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            # Use Django's built-in authentication
            try:
                user = User.objects.get(email=email)
                if user.role != role:
                    messages.error(request, 'Invalid role for this account.')
                    return render(request, 'users/login.html')
                
                # Check password using Django's authentication
                if user.check_password(password):
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    if user.is_student():
                        return redirect('dashboard:student_dashboard')
                    elif user.is_management():
                        return redirect('dashboard:management_dashboard')
                    else:
                        return redirect('dashboard:admin_dashboard')
                else:
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please sign up first.')
    
    return render(request, 'users/login.html')


@require_http_methods(["GET", "POST"])
def signup_view(request):
    """Signup view with optional Supabase integration."""
    if request.user.is_authenticated:
        return redirect('users:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')
        department = request.POST.get('department', '')
        student_id = request.POST.get('student_id', '')
        
        # Note: Admin/Organizer signup is allowed for development/testing
        # In production, you may want to restrict this or require approval
        
        # Validate college email
        from django.conf import settings
        if not email.endswith(settings.COLLEGE_EMAIL_DOMAIN):
            messages.error(request, f'Email must be from {settings.COLLEGE_EMAIL_DOMAIN} domain.')
            return render(request, 'users/signup.html')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'users/signup.html')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'This username is already taken.')
            return render(request, 'users/signup.html')
        
        # Handle student_id - only required for students, and must be unique
        student_id_value = None
        if role == 'student':
            student_id = student_id.strip() if student_id else ''
            if student_id:
                # Check if student_id already exists
                if User.objects.filter(student_id=student_id).exists():
                    messages.error(request, 'This student ID is already registered. Please use a different student ID or contact support.')
                    return render(request, 'users/signup.html')
                student_id_value = student_id
            # If student but no student_id provided, that's okay (optional)
        # For admin/organizer, student_id is always None
        
        # Try Supabase if configured, otherwise use Django-only signup
        if settings.SUPABASE_URL:
            # Create user in Supabase
            supabase_user = create_supabase_user(email, password)
            
            if not supabase_user:
                messages.error(request, 'Error creating account. Please try again.')
                return render(request, 'users/signup.html')
        
        # Create Django user (works with or without Supabase)
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                department=department,
                student_id=student_id_value,
            )

            # Create leaderboard entry for students only
            if role == 'student':
                Leaderboard.objects.create(user=user)

            # Generate verification code and send email
            code = f"{random.randint(100000, 999999)}"
            expires_at = timezone.now() + timedelta(hours=24)
            EmailVerification.objects.create(user=user, code=code, expires_at=expires_at)

            # Try to send via Celery task if available, otherwise send synchronously
            try:
                if send_verification_email:
                    send_verification_email.delay(user.id, code)
                else:
                    # Fallback - render and send synchronously
                    message = render_to_string('users/verification_email.txt', {'user': user, 'code': code, 'site_name': 'CampusNexus'})
                    send_mail('Verify your email for CampusNexus', message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            except Exception:
                # if sending fails, continue but show message
                pass

            # Store pending verification user id in session and prompt for verification
            request.session['verification_user_id'] = user.id
            messages.success(request, 'Account created. Please check your email for a verification code.')
            return redirect('users:verify_email')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'users/signup.html')
    
    return render(request, 'users/signup.html')


@login_required
def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:login')


@api_view(['GET'])
@permission_classes([AllowAny])
def check_email(request):
    """API endpoint to check if email exists."""
    email = request.GET.get('email')
    if email:
        exists = User.objects.filter(email=email).exists()
        return Response({'exists': exists})
    return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)


@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    """Password reset request view."""
    if request.user.is_authenticated:
        return redirect('users:home')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        college_domain = settings.COLLEGE_EMAIL_DOMAIN.replace('@', '')
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'users/password_reset.html', {'college_domain': college_domain})
        
        # Validate college email
        if not email.endswith(settings.COLLEGE_EMAIL_DOMAIN):
            messages.error(request, f'Email must be from {settings.COLLEGE_EMAIL_DOMAIN} domain.')
            return render(request, 'users/password_reset.html', {'college_domain': college_domain})
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            messages.success(request, 'If an account with that email exists, we have sent password reset instructions.')
            return redirect('users:password_reset_done')
        
        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        reset_url = request.build_absolute_uri(f'/password-reset-confirm/{uid}/{token}/')
        
        # Send email
        subject = 'Password Reset Request - CampusNexus'
        message = render_to_string('users/password_reset_email.html', {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'CampusNexus',
        })
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=message,
            )
            messages.success(request, 'If an account with that email exists, we have sent password reset instructions.')
            return redirect('users:password_reset_done')
        except Exception as e:
            messages.error(request, f'Error sending email: {str(e)}. Please try again later or contact support.')
            college_domain = settings.COLLEGE_EMAIL_DOMAIN.replace('@', '')
            return render(request, 'users/password_reset.html', {'college_domain': college_domain})
    
    college_domain = settings.COLLEGE_EMAIL_DOMAIN.replace('@', '')
    return render(request, 'users/password_reset.html', {'college_domain': college_domain})


@require_http_methods(["GET", "POST"])
def verify_email(request):
    """Verify the email using a one-time code sent to the user."""
    user_id = request.session.get('verification_user_id')
    if not user_id:
        messages.error(request, 'No verification pending. Please sign up first.')
        return redirect('users:signup')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('users:signup')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        try:
            ev = EmailVerification.objects.filter(user=user, code=code, used=False).order_by('-created_at').first()
            if ev and ev.is_valid():
                ev.used = True
                ev.save()
                user.is_verified = True
                user.save()
                # Log the user in after verification
                login(request, user)
                messages.success(request, 'Email verified and you are now logged in.')
                # cleanup session
                request.session.pop('verification_user_id', None)
                if user.is_student():
                    return redirect('dashboard:student_dashboard')
                elif user.is_management():
                    return redirect('dashboard:management_dashboard')
                else:
                    return redirect('dashboard:admin_dashboard')
            else:
                messages.error(request, 'Invalid or expired verification code.')
        except Exception:
            messages.error(request, 'Error verifying code. Please try again.')

    return render(request, 'users/verify_email.html', {'email': user.email})


@require_http_methods(["POST"])
def resend_verification(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        messages.error(request, 'No verification pending.')
        return redirect('users:signup')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('users:signup')

    code = f"{random.randint(100000, 999999)}"
    expires_at = timezone.now() + timedelta(hours=24)
    EmailVerification.objects.create(user=user, code=code, expires_at=expires_at)

    try:
        if send_verification_email:
            send_verification_email.delay(user.id, code)
        else:
            message = render_to_string('users/verification_email.txt', {'user': user, 'code': code, 'site_name': 'CampusNexus'})
            send_mail('Verify your email for CampusNexus', message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        messages.success(request, 'Verification code resent. Please check your email.')
    except Exception as e:
        messages.error(request, f'Error sending verification email: {str(e)}')

    return redirect('users:verify_email')

