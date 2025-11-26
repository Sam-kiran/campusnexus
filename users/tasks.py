"""Celery tasks for user-related jobs (email sending)."""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import EmailVerification, User

@shared_task
def send_verification_email(user_id: int, code: str):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return False

    subject = 'Verify your email for CampusNexus'
    message = render_to_string('users/verification_email.txt', {
        'user': user,
        'code': code,
        'site_name': 'CampusNexus',
    })

    # send as plain text and html_message left empty; simple implementation
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=message,
    )
    return True
