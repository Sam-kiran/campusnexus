from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from .utils import process_chatbot_query, generate_event_with_ai, generate_event_poster_ai
from events.models import Event
import json


@login_required
def chatbot_view(request):
    """Chatbot interface."""
    return render(request, 'chatbot/chatbot.html')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot_query(request):
    """Handle chatbot queries."""
    query = request.data.get('query', '')
    user = request.user
    
    if not query:
        return Response({'error': 'Query required'}, status=400)
    
    # Process query
    try:
        response = process_chatbot_query(query, user)
    except Exception as e:
        # Log the exception and return a JSON error so frontend doesn't try to parse HTML
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error processing chatbot query")
        return Response({'error': 'Internal server error processing query'}, status=500)

    # Ensure response is a dict-like object
    if not isinstance(response, dict):
        return Response({'error': 'Invalid response from chatbot processor'}, status=500)

    return Response({
        'response': response.get('text', ''),
        'data': response.get('data', []),
        'type': response.get('type', 'text')
    })


@login_required
def ai_assistant_view(request):
    """AI Assistant for event creation (Admin/Organizer only)."""
    if not request.user.is_admin_or_organizer():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    return render(request, 'chatbot/ai_assistant.html')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event_with_ai(request):
    """Create event using AI assistant."""
    if not request.user.is_admin_or_organizer():
        return Response({'error': 'Access denied'}, status=403)
    
    event_name = request.data.get('event_name')
    rules = request.data.get('rules', '')
    team_size = int(request.data.get('team_size', 1))
    location = request.data.get('location', '')
    is_team_event = team_size > 1
    
    if not event_name:
        return Response({'error': 'Event name required'}, status=400)
    
    # Generate event using AI
    result = generate_event_with_ai(
        event_name=event_name,
        rules=rules,
        team_size=team_size,
        location=location,
        is_team_event=is_team_event,
        user=request.user
    )
    
    if result.get('success'):
        return Response({
            'success': True,
            'event_id': result['event'].id,
            'message': 'Event created successfully!'
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'Failed to create event')
        }, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_poster_with_ai(request):
    """Generate event poster using AI."""
    if not request.user.is_admin_or_organizer():
        return Response({'error': 'Access denied'}, status=403)
    
    event_id = request.data.get('event_id')
    if not event_id:
        return Response({'error': 'Event ID required'}, status=400)
    
    try:
        event = Event.objects.get(id=event_id)
        if event.created_by != request.user and not request.user.is_admin():
            return Response({'error': 'Permission denied'}, status=403)
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=404)
    
    # Generate poster
    result = generate_event_poster_ai(event)
    
    if result.get('success'):
        return Response({
            'success': True,
            'poster_url': result.get('poster_url'),
            'message': 'Poster generated successfully!'
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'Failed to generate poster')
        }, status=400)

