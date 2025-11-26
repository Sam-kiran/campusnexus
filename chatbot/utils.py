"""Utility functions for chatbot and AI assistant."""
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, F
from datetime import datetime, timedelta
from events.models import Event, Registration, EventRecommendation
from feedback.models import Feedback
from users.models import Leaderboard
import logging
import json
import re

logger = logging.getLogger(__name__)

# Lightweight FAQ responses so the chatbot stays useful without external AI APIs.
BASIC_FAQ_RESPONSES = [
    {
        'keywords': ['register', 'how'],
        'response': (
            "To register for an event:\n"
            "1. Visit the Events page and pick an approved event.\n"
            "2. Click \"Register\", fill in your details, and submit the payment info.\n"
            "3. Track the status on the event page—organizers verify payments manually."
        )
    },
    {
        'keywords': ['payment', 'status'],
        'response': (
            "Payment verification can take a little time. Once an organizer confirms your UPI transaction, "
            "you will see \"Verified\" next to that registration."
        )
    },
    {
        'keywords': ['team', 'event'],
        'response': (
            "For team events, the team leader registers on CampusNexus, enters a team name, "
            "and selects the required number of teammates. Everyone still needs an account, "
            "but only the leader submits the form."
        )
    },
    {
        'keywords': ['feedback'],
        'response': (
            "Feedback opens after an event is over. Head to the Feedback section or ask \"What events need feedback?\" "
            "to see what's pending."
        )
    },
    {
        'keywords': ['leaderboard'],
        'response': (
            "Leaderboard points come from attending events and sharing feedback. Ask \"What's my rank?\" "
            "to see your current stats."
        )
    },
    {
        'keywords': ['help'],
        'response': (
            "Need ideas? Try one of these:\n"
            "- \"Show me tech events this week\"\n"
            "- \"What events am I registered for?\"\n"
            "- \"Do I owe any feedback?\"\n"
            "- \"What's my leaderboard rank?\""
        )
    },
]

# Try to import Google's Generative AI (Gemini) client, fallback to OpenAI if needed
GENAI_AVAILABLE = False
GENAI_API_KEY = None
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
    # Prefer a dedicated GEMINI_API_KEY, otherwise fall back to OPENAI_API_KEY for quick tests
    GENAI_API_KEY = getattr(settings, 'GEMINI_API_KEY', None) or getattr(settings, 'OPENAI_API_KEY', None)
    if GENAI_API_KEY:
        try:
            genai.configure(api_key=GENAI_API_KEY)
        except Exception:
            # Some older/newer versions may not require configure; ignore configuration errors
            pass
except Exception:
    GENAI_AVAILABLE = False
    logger.warning("Google Generative AI library not available. AI features will be limited.")


def process_chatbot_query(query, user):
    """Process chatbot query with intelligent routing and deep search."""
    query_lower = query.lower().strip()
    
    # Context detection - check if user is asking about their own data
    # Use word boundaries to avoid false matches (e.g., "there" containing "i")
    query_words = set(query_lower.split())
    
    # Check for explicit personal phrases first (these are definitely personal)
    explicit_personal = (
        'my events' in query_lower or
        'my registrations' in query_lower or
        'i registered' in query_lower or
        'i signed up' in query_lower or
        'i have' in query_lower or
        'i am' in query_lower or
        query_lower.startswith('my ') or
        query_lower.startswith('i ')
    )
    
    # Check for personal pronouns, but only if not part of a general query phrase
    # "show me" or "tell me" are not personal queries
    general_phrases = ['show me', 'tell me', 'give me', 'help me', 'let me']
    is_general_phrase = any(phrase in query_lower for phrase in general_phrases)
    
    # Only treat as personal if explicit personal phrase OR (personal pronoun AND not a general phrase)
    is_personal_query = (
        explicit_personal or
        (any(word in query_words for word in ['my', 'i']) and not is_general_phrase)
    )
    
    # Determine query type with better pattern matching
    if is_personal_query and user.is_student():
        # Personal queries for students
        if any(word in query_lower for word in ['register', 'registration', 'signed up', 'enrolled']):
            return handle_registration_query(query, user)
        elif any(word in query_lower for word in ['feedback', 'rate', 'rating', 'review']):
            return handle_feedback_query(query, user)
        elif any(word in query_lower for word in ['event', 'events']):
            return handle_my_events_query(query, user)
        else:
            return handle_personal_info_query(query, user)
    
    # Feedback queries should take precedence so we don't treat them as generic event searches
    elif any(word in query_lower for word in ['feedback', 'rate', 'rating', 'review', 'comment']):
        return handle_feedback_query(query, user)
    
    # Event search queries
    elif any(word in query_lower for word in [
        'event', 'events', 'show', 'list', 'find', 'search', 'upcoming',
        'happening', 'when', 'where', 'what events', 'which events'
    ]):
        return handle_event_query(query, user)
    
    # Registration queries
    elif any(word in query_lower for word in ['register', 'registration', 'sign up', 'enroll']):
        return handle_registration_query(query, user)
    
    # Leaderboard queries
    elif any(word in query_lower for word in ['leaderboard', 'rank', 'ranking', 'points', 'score']):
        return handle_leaderboard_query(query, user)
    
    # Help queries
    elif any(word in query_lower for word in ['help', 'assist', 'how', 'what can', 'what do']):
        return handle_help_query(query, user)
    
    # General queries
    else:
        return handle_general_query(query, user)


def handle_event_query(query, user):
    """Handle event-related queries with deep search."""
    query_lower = query.lower()
    
    # Start with all approved events
    events = Event.objects.filter(status='approved')
    
    # Date filtering - check this FIRST before text search
    now = timezone.now()
    date_filter_applied = False
    
    # Check for specific date queries first
    if 'today' in query_lower:
        events = events.filter(event_date__date=now.date())
        date_filter_applied = True
    elif 'tomorrow' in query_lower:
        tomorrow = now + timedelta(days=1)
        events = events.filter(event_date__date=tomorrow.date())
        date_filter_applied = True
    elif 'this week' in query_lower:
        week_end = now + timedelta(days=7)
        events = events.filter(event_date__gte=now, event_date__lte=week_end)
        date_filter_applied = True
    elif 'next week' in query_lower:
        week_start = now + timedelta(days=7)
        week_end = now + timedelta(days=14)
        events = events.filter(event_date__gte=week_start, event_date__lte=week_end)
        date_filter_applied = True
    elif 'month' in query_lower and ('this' in query_lower or 'next' in query_lower):
        month_end = now + timedelta(days=30)
        events = events.filter(event_date__gte=now, event_date__lte=month_end)
        date_filter_applied = True
    elif 'upcoming' in query_lower or 'future' in query_lower or 'coming' in query_lower:
        # Show all upcoming events (future dates)
        events = events.filter(event_date__gte=now)
        date_filter_applied = True
    elif 'past' in query_lower or 'completed' in query_lower or 'previous' in query_lower:
        events = events.filter(event_date__lt=now)
        date_filter_applied = True
    
    # If query asks about events in general (like "are there any events?", "any upcoming events?")
    # and no specific date filter was applied, default to upcoming events
    if not date_filter_applied:
        if any(phrase in query_lower for phrase in [
            'any events', 'are there', 'show events', 'list events', 
            'what events', 'upcoming events', 'future events', 'any upcoming'
        ]):
            # Default to upcoming events for general queries
            events = events.filter(event_date__gte=now)
            date_filter_applied = True
    
    # Extract search terms from query (only if not a simple general query)
    is_simple_query = any(phrase in query_lower for phrase in [
        'any events', 'are there', 'show events', 'list events', 
        'what events', 'upcoming events', 'future events', 'any upcoming'
    ])
    
    if not is_simple_query:
        search_terms = extract_search_terms(query)
        
        # Deep search in multiple fields
        if search_terms:
            q_objects = Q()
            for term in search_terms:
                q_objects |= (
                    Q(title__icontains=term) |
                    Q(description__icontains=term) |
                    Q(department__icontains=term) |
                    Q(location__icontains=term) |
                    Q(category__icontains=term) |
                    Q(rules__icontains=term)
                )
            events = events.filter(q_objects)
    
    # Category filtering
    categories = []
    category_keywords = {
        'tech': ['tech', 'technology', 'coding', 'programming', 'software', 'computer', 'hackathon'],
        'sports': ['sports', 'sport', 'game', 'games', 'athletic', 'tournament'],
        'cultural': ['cultural', 'culture', 'festival', 'fest', 'music', 'dance', 'art'],
        'academic': ['academic', 'lecture', 'seminar', 'workshop', 'conference'],
        'workshop': ['workshop', 'training', 'session'],
        'competition': ['competition', 'contest', 'challenge', 'tournament'],
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            categories.append(category)
    
    if categories:
        events = events.filter(category__in=categories)
    
    # Location filtering
    location_keywords = ['location', 'where', 'venue', 'place', 'at']
    if any(keyword in query_lower for keyword in location_keywords):
        # Try to extract location from query
        location_match = re.search(r'(?:at|in|location|venue|place)\s+([A-Za-z0-9\s]+)', query, re.IGNORECASE)
        if location_match:
            location_term = location_match.group(1).strip()
            events = events.filter(location__icontains=location_term)
    
    # Department filtering
    if 'department' in query_lower or 'dept' in query_lower:
        dept_match = re.search(r'(?:department|dept)\s+([A-Za-z0-9\s]+)', query, re.IGNORECASE)
        if dept_match:
            dept_term = dept_match.group(1).strip()
            events = events.filter(department__icontains=dept_term)
    
    # Fee filtering
    if 'free' in query_lower:
        events = events.filter(fee=0)
    elif 'paid' in query_lower or 'fee' in query_lower:
        events = events.filter(fee__gt=0)
    
    # Hot events
    if 'hot' in query_lower or 'popular' in query_lower or 'trending' in query_lower:
        events = events.filter(hotness_score__gte=50).order_by('-hotness_score')
    else:
        events = events.order_by('event_date')
    
    # Get count before limiting
    event_count = events.count()
    
    # Limit results
    events = events[:20]
    
    if event_count > 0:
        event_list = [{
            'id': event.id,
            'title': event.title,
            'date': event.event_date.strftime('%Y-%m-%d %H:%M'),
            'location': event.location,
            'category': event.get_category_display(),
            'department': event.department,
            'fee': float(event.fee),
            'capacity': event.capacity,
            'registrations': event.total_registrations,
            'rating': event.average_rating,
            'hotness': event.hotness_score,
        } for event in events]
        
        count_text = f"{event_count} event(s)" if event_count <= 20 else f"{event_count} events (showing first 20)"
        return {
            'text': f"I found {count_text} matching your query:",
            'data': event_list,
            'type': 'events'
        }
    else:
        # Provide more helpful error message based on query type
        suggestions = []
        if 'upcoming' in query_lower or 'future' in query_lower:
            suggestions.append("- Check if there are any approved events scheduled")
            suggestions.append("- Try asking about specific categories (tech, sports, cultural)")
        elif 'today' in query_lower or 'tomorrow' in query_lower:
            suggestions.append("- Try asking about events this week or next week")
        else:
            suggestions.append("- Tech events tomorrow")
            suggestions.append("- Free events this week")
            suggestions.append("- Events in [location]")
            suggestions.append("- Hot/popular events")
        
        return {
            'text': f"I couldn't find any events matching your query. Try asking about:\n" + "\n".join(suggestions),
            'data': [],
            'type': 'text'
        }


def handle_my_events_query(query, user):
    """Handle queries about user's own events."""
    if not user.is_student():
        return {
            'text': "Only students can view their registered events.",
            'data': [],
            'type': 'text'
        }
    
    query_lower = query.lower()
    
    # Get user's registrations
    registrations = Registration.objects.filter(
        user=user
    ).select_related('event')
    
    # Filter by date
    now = timezone.now()
    if 'upcoming' in query_lower or 'future' in query_lower:
        registrations = registrations.filter(event__event_date__gte=now)
    elif 'past' in query_lower or 'completed' in query_lower:
        registrations = registrations.filter(event__event_date__lt=now)
    elif 'today' in query_lower:
        registrations = registrations.filter(event__event_date__date=now.date())
    elif 'tomorrow' in query_lower:
        tomorrow = now + timedelta(days=1)
        registrations = registrations.filter(event__event_date__date=tomorrow.date())
    
    # Search in event details
    search_terms = extract_search_terms(query)
    if search_terms:
        q_objects = Q()
        for term in search_terms:
            q_objects |= (
                Q(event__title__icontains=term) |
                Q(event__description__icontains=term) |
                Q(event__category__icontains=term) |
                Q(event__location__icontains=term)
            )
        registrations = registrations.filter(q_objects)
    
    registrations = registrations.order_by('event__event_date')[:20]
    
    if registrations.exists():
        event_list = [{
            'id': reg.event.id,
            'title': reg.event.title,
            'date': reg.event.event_date.strftime('%Y-%m-%d %H:%M'),
            'location': reg.event.location,
            'category': reg.event.get_category_display(),
            'status': 'Verified' if reg.is_verified else 'Awaiting verification',
            'payment_status': reg.get_payment_status_display(),
        } for reg in registrations]
        
        return {
            'text': f"You are registered for {len(event_list)} event(s):",
            'data': event_list,
            'type': 'registrations'
        }
    else:
        return {
            'text': "You haven't registered for any events matching your query. Browse events to get started!",
            'data': [],
            'type': 'text'
        }


def handle_registration_query(query, user):
    """Handle registration-related queries."""
    if not user.is_student():
        return {
            'text': "Only students can register for events. Please check the events page to register.",
            'data': [],
            'type': 'text'
        }
    
    # Get user's registrations
    registrations = Registration.objects.filter(
        user=user
    ).select_related('event').order_by('-registered_at')[:10]
    
    if registrations.exists():
        reg_list = [{
            'id': reg.event.id,
            'title': reg.event.title,
            'date': reg.event.event_date.strftime('%Y-%m-%d %H:%M'),
            'status': 'Verified' if reg.is_verified else 'Awaiting verification',
            'payment_status': reg.get_payment_status_display(),
        } for reg in registrations]
        
        return {
            'text': f"You are registered for {len(reg_list)} event(s):",
            'data': reg_list,
            'type': 'registrations'
        }
    else:
        return {
            'text': "You haven't registered for any events yet. Browse events to get started!",
            'data': [],
            'type': 'text'
        }


def handle_feedback_query(query, user):
    """Handle feedback-related queries."""
    if not user.is_student():
        return {
            'text': "Only students can submit feedback.",
            'data': [],
            'type': 'text'
        }
    
    # Get events needing feedback
    registrations = Registration.objects.filter(
        user=user,
        is_verified=True,
        event__event_date__lte=timezone.now()
    ).select_related('event')
    
    events_needing_feedback = []
    for reg in registrations:
        if not Feedback.objects.filter(event=reg.event, user=user).exists():
            events_needing_feedback.append(reg.event)
    
    if events_needing_feedback:
        event_list = [{
            'id': event.id,
            'title': event.title,
            'date': event.event_date.strftime('%Y-%m-%d'),
        } for event in events_needing_feedback[:10]]
        
        return {
            'text': f"You have {len(events_needing_feedback)} event(s) waiting for feedback:",
            'data': event_list,
            'type': 'feedback_needed'
        }
    else:
        return {
            'text': "You're all caught up! No events need feedback right now.",
            'data': [],
            'type': 'text'
        }


def handle_leaderboard_query(query, user):
    """Handle leaderboard queries."""
    if not user.is_student():
        return {
            'text': "Leaderboard is only available for students.",
            'data': [],
            'type': 'text'
        }
    
    try:
        leaderboard = Leaderboard.objects.get(user=user)
        rank = Leaderboard.objects.filter(
            Q(total_points__gt=leaderboard.total_points) |
            (Q(total_points=leaderboard.total_points) & Q(total_events_attended__gt=leaderboard.total_events_attended))
        ).count() + 1
        
        return {
            'text': f"Your Leaderboard Stats:\n- Rank: #{rank}\n- Total Points: {leaderboard.total_points}\n- Events Attended: {leaderboard.total_events_attended}\n- Feedbacks Given: {leaderboard.total_feedback_given}",
            'data': [],
            'type': 'text'
        }
    except Leaderboard.DoesNotExist:
        return {
            'text': "You don't have a leaderboard entry yet. Register for events and give feedback to earn points!",
            'data': [],
            'type': 'text'
        }


def handle_personal_info_query(query, user):
    """Handle personal information queries."""
    if user.is_student():
        try:
            leaderboard = Leaderboard.objects.get(user=user)
            reg_count = Registration.objects.filter(user=user, is_verified=True).count()
            feedback_count = Feedback.objects.filter(user=user).count()
            
            return {
                'text': f"Your Profile:\n- Username: {user.username}\n- Department: {user.department or 'Not set'}\n- Events Registered: {reg_count}\n- Feedbacks Given: {feedback_count}\n- Total Points: {leaderboard.total_points}",
                'data': [],
                'type': 'text'
            }
        except Leaderboard.DoesNotExist:
            return {
                'text': f"Your Profile:\n- Username: {user.username}\n- Department: {user.department or 'Not set'}\n- Role: {user.get_role_display()}",
                'data': [],
                'type': 'text'
            }
    else:
        return {
            'text': f"Your Profile:\n- Username: {user.username}\n- Role: {user.get_role_display()}\n- Department: {user.department or 'Not set'}",
            'data': [],
            'type': 'text'
        }


def handle_help_query(query, user):
    """Handle help queries."""
    help_text = """I can help you with:

**Event Search:**
- "Show me tech events tomorrow"
- "Find free events this week"
- "What events are happening in [location]?"
- "Show me hot/popular events"
- "Events in [department]"

**My Events (Students):**
- "What events am I registered for?"
- "Show me my upcoming events"
- "My past events"

**Registration:**
- "What events have I registered for?"
- "Am I registered for [event name]?"

**Feedback:**
- "What events need feedback?"
- "Do I have any pending feedback?"

**Leaderboard:**
- "What's my rank?"
- "How many points do I have?"

**General:**
- "Tell me about myself"
- "What can you do?"

Try asking me anything about events!"""
    
    return {
        'text': help_text,
        'data': [],
        'type': 'text'
    }


def handle_general_query(query, user):
    """Handle general queries using Gemini (Google Generative AI) or intelligent fallback."""
    query_lower = query.lower()

    # Try to extract event-related information even from general queries
    if any(word in query_lower for word in ['event', 'events']):
        # Re-route to event query
        return handle_event_query(query, user)

    faq_answer = get_basic_answer(query_lower)
    if faq_answer:
        return {
            'text': faq_answer,
            'data': [],
            'type': 'text'
        }

    if GENAI_AVAILABLE and GENAI_API_KEY:
        try:
            # Get context about user and events for better responses
            context = get_user_context(user)

            system_prompt = (
                f"You are a helpful assistant for CampusNexus, a campus event management system.\n"
                f"User context: {context}\n"
                "Help users with event-related queries. Be concise and helpful."
            )

            # Use Google Generative AI chat API if available
            model_name = getattr(settings, 'GEMINI_MODEL', 'chat-bison')
            try:
                response = genai.chat.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.7,
                    max_output_tokens=200
                )

                # Response extraction: prefer last or first candidate content
                generated = None
                if hasattr(response, 'last') and getattr(response, 'last'):
                    # Some versions return an object with 'last'
                    generated = response.last
                elif isinstance(response, dict):
                    # dict-style response
                    candidates = response.get('candidates') or response.get('outputs')
                    if candidates and len(candidates) > 0:
                        candidate = candidates[0]
                        generated = candidate.get('content') or candidate.get('text')
                else:
                    # Fallback to string representation
                    generated = str(response)

                text_out = ''
                if isinstance(generated, dict):
                    # Newer SDKs may nest content
                    text_out = generated.get('content', '') or generated.get('text', '') or ''
                else:
                    text_out = generated or ''

                return {
                    'text': text_out.strip(),
                    'data': [],
                    'type': 'text'
                }
            except Exception as e:
                logger.error(f"Gemini/Generative AI error: {e}")
        except Exception as e:
            logger.error(f"Generative AI error preparing request: {e}")
    
    # Fallback response
    return {
        'text': "I can help you with events, registrations, feedback, and more. Try asking:\n- 'Show me events'\n- 'What events am I registered for?'\n- 'What events need feedback?'\nOr type 'help' for more options.",
        'data': [],
        'type': 'text'
    }


def get_basic_answer(query_lower):
    """Return a canned response for common queries when AI isn't available."""
    for entry in BASIC_FAQ_RESPONSES:
        if all(keyword in query_lower for keyword in entry['keywords']):
            return entry['response']
    return None


def extract_search_terms(query):
    """Extract meaningful search terms from query."""
    # Remove common stop words and date/time keywords
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 
        'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'where', 'when', 'why', 'how', 
        'show', 'me', 'my', 'find', 'search', 'list', 'get', 'give', 'any', 'there', 'are', 'there',
        'upcoming', 'future', 'coming', 'past', 'completed', 'previous', 'today', 'tomorrow', 'week', 'month',
        'events', 'event'  # Remove generic event words too
    }
    
    # Extract words
    words = re.findall(r'\b\w+\b', query.lower())
    
    # Filter out stop words and short words
    terms = [word for word in words if word not in stop_words and len(word) > 2]
    
    return terms


def get_user_context(user):
    """Get context about user for AI responses."""
    context_parts = [f"User: {user.username}, Role: {user.get_role_display()}"]
    
    if user.is_student():
        reg_count = Registration.objects.filter(user=user, is_verified=True).count()
        context_parts.append(f"Registered for {reg_count} events")
        
        try:
            leaderboard = Leaderboard.objects.get(user=user)
            context_parts.append(f"Rank: {leaderboard.rank}, Points: {leaderboard.total_points}")
        except:
            pass
    
    return ", ".join(context_parts)


def generate_event_with_ai(event_name, rules, team_size, location, is_team_event, user):
    """Generate event details using AI."""
    if not GENAI_AVAILABLE or not GENAI_API_KEY:
        return {
            'success': False,
            'error': 'Gemini API key not configured or generative client not available'
        }
    
    try:
        prompt = f"""
        Create a detailed event description for a campus event with the following details:
        - Event Name: {event_name}
        - Rules: {rules}
        - Team Size: {team_size} {'(Team Event)' if is_team_event else '(Solo Event)'}
        - Location: {location}
        
        Generate:
        1. A comprehensive description (2-3 paragraphs)
        2. Suggested category (tech, sports, cultural, academic, workshop, seminar, competition, other)
        3. Suggested department
        4. Additional rules or guidelines if needed
        
        Return as JSON with keys: description, category, department, additional_rules
        """
        
        # Use Gemini / Google Generative AI chat endpoint
        model_name = getattr(settings, 'GEMINI_MODEL', 'chat-bison')
        response = genai.chat.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an event planning assistant. Generate detailed event information in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_output_tokens=300
        )

        # Parse response safely
        response_text = ''
        if isinstance(response, dict):
            candidates = response.get('candidates') or response.get('outputs')
            if candidates and len(candidates) > 0:
                candidate = candidates[0]
                response_text = candidate.get('content') or candidate.get('text') or ''
        else:
            # SDK objects may have a .last or similar
            if hasattr(response, 'last') and getattr(response, 'last'):
                maybe = getattr(response, 'last')
                if isinstance(maybe, dict):
                    response_text = maybe.get('content') or maybe.get('text') or ''
                else:
                    response_text = str(maybe)
            else:
                response_text = str(response)
        
        # Try to extract JSON
        try:
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            event_data = json.loads(response_text)
        except:
            # Fallback if JSON parsing fails
            event_data = {
                'description': response_text,
                'category': 'other',
                'department': user.department or 'General',
                'additional_rules': rules
            }
        
        # Create event
        from events.models import Event
        event = Event.objects.create(
            title=event_name,
            description=event_data.get('description', f'Event: {event_name}'),
            category=event_data.get('category', 'other'),
            department=event_data.get('department', user.department or 'General'),
            rules=event_data.get('additional_rules', rules) or rules,
            location=location,
            capacity=team_size * 10,  # Default capacity
            is_team_event=is_team_event,
            team_size=team_size,
            created_by=user,
            status='pending',
        )
        
        return {
            'success': True,
            'event': event
        }
    except Exception as e:
        logger.error(f"AI event generation error: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def generate_event_poster_ai(event):
    """Generate event poster using AI (DALL-E)."""
    if not GENAI_AVAILABLE or not GENAI_API_KEY:
        return {
            'success': False,
            'error': 'Gemini API key not configured or generative client not available'
        }
    
    try:
        prompt = f"""
        Create a vibrant, modern event poster for:
        Title: {event.title}
        Category: {event.category}
        Date: {event.event_date.strftime('%B %d, %Y')}
        Location: {event.location}
        
        Style: Modern, colorful, eye-catching, suitable for campus events
        """
        
        # Note: This would use DALL-E API, but it requires image generation credits
        # For now, return a placeholder
        return {
            'success': True,
            'poster_url': None,
            'message': 'Poster generation feature requires DALL-E API access'
        }
    except Exception as e:
        logger.error(f"Poster generation error: {e}")
        return {
            'success': False,
            'error': str(e)
        }
