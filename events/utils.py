"""Utility functions for events."""
from django.db.models import Q, Count, Avg
from django.conf import settings
from django.core.files.base import ContentFile
from .models import Event, Registration, EventRecommendation
from users.models import User
from feedback.models import Feedback
import logging
import requests
import base64
import random
import textwrap
from io import BytesIO

logger = logging.getLogger(__name__)

# Minimal lexicon for ultra-lightweight sentiment analysis.
POSITIVE_WORDS = {
    'great', 'awesome', 'exciting', 'fun', 'amazing', 'incredible', 'wonderful',
    'fantastic', 'positive', 'excellent', 'engaging', 'cool', 'uplifting',
    'rewarding', 'supportive', 'helpful', 'enjoyable', 'beneficial', 'inspiring'
}
NEGATIVE_WORDS = {
    'bad', 'boring', 'sad', 'terrible', 'awful', 'worse', 'worst', 'negative',
    'stressful', 'tiring', 'annoying', 'confusing', 'difficult', 'problematic',
    'angry', 'frustrating', 'painful', 'unhappy', 'depressing', 'hate'
}


def analyze_basic_sentiment(text):
    """
    Extremely small heuristic sentiment scorer.

    We simply count positive and negative lexicon hits and classify by score,
    allowing us to offer instant feedback with zero external dependencies.
    """
    if not text:
        return {
            'score': 0,
            'label': 'neutral',
            'confidence': 0.0,
            'positive_hits': 0,
            'negative_hits': 0,
        }

    tokens = [
        token.strip(".,!?\"'()[]{}").lower()
        for token in text.split()
        if token.strip()
    ]

    positive_hits = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative_hits = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    score = positive_hits - negative_hits

    if score > 1:
        label = 'positive'
    elif score < -1:
        label = 'negative'
    else:
        label = 'neutral'

    total_hits = positive_hits + negative_hits
    confidence = min(total_hits / max(len(tokens), 1), 1.0)

    return {
        'score': score,
        'label': label,
        'confidence': round(confidence, 3),
        'positive_hits': positive_hits,
        'negative_hits': negative_hits,
    }

# Optional PIL import
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageFont = None

# Optional Google Generative AI (Gemini) import
GENAI_AVAILABLE = False
GENAI_API_KEY = None
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
    GENAI_API_KEY = getattr(settings, 'GEMINI_API_KEY', None) or getattr(settings, 'OPENAI_API_KEY', None)
    if GENAI_API_KEY:
        try:
            genai.configure(api_key=GENAI_API_KEY)
        except Exception:
            pass
except Exception:
    GENAI_AVAILABLE = False


def calculate_recommendations(user):
    """Calculate event recommendations for a user."""
    if not user.is_student():
        return
    
    # Get user's department
    user_dept = user.department
    
    # Get user's registered events
    registered_events = Registration.objects.filter(
        user=user,
        is_verified=True
    ).values_list('event_id', flat=True)
    
    # Get user's feedback to understand preferences
    user_feedback = Feedback.objects.filter(user=user).values('event__category', 'event__department')
    preferred_categories = [f['event__category'] for f in user_feedback if f['event__category']]
    preferred_depts = [f['event__department'] for f in user_feedback if f['event__department']]
    
    # Get available events (not registered, approved, future)
    from django.utils import timezone
    available_events = Event.objects.filter(
        status='approved',
        event_date__gt=timezone.now()
    ).exclude(id__in=registered_events)
    
    # Calculate recommendation scores
    recommendations = []
    for event in available_events:
        score = 0.0
        reason_parts = []
        
        # Department match (40% weight)
        if user_dept and event.department == user_dept:
            score += 40.0
            reason_parts.append("Same department")
        
        # Category preference (30% weight)
        if event.category in preferred_categories:
            score += 30.0
            reason_parts.append("Preferred category")
        
        # Hotness score (20% weight)
        score += event.hotness_score * 0.2
        if event.hotness_score > 50:
            reason_parts.append("Popular event")
        
        # Availability (10% weight)
        available_spots = event.get_available_spots()
        if available_spots > 0:
            availability_score = min(available_spots / event.capacity * 10, 10)
            score += availability_score
        
        if score > 0:
            EventRecommendation.objects.update_or_create(
                user=user,
                event=event,
                defaults={
                    'score': score,
                    'reason': ', '.join(reason_parts) if reason_parts else "Recommended for you"
                }
            )


def _build_banner_filename(event, prefix='event_ai_banner'):
    """Create deterministic banner filename."""
    if hasattr(event, 'id') and event.id:
        return f'event_{event.id}_{prefix}.png'
    from django.utils import timezone
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    return f'{prefix}_{timestamp}.png'


def _font_line_height(font):
    """Best-effort line height for any Pillow font."""
    if hasattr(font, 'size') and font.size:
        return font.size
    if hasattr(font, 'getbbox'):
        bbox = font.getbbox('Ag')
        if bbox:
            return bbox[3] - bbox[1]
    if hasattr(font, 'getmetrics'):
        ascent, descent = font.getmetrics()
        return ascent + descent
    return 20


def generate_simple_banner(event, reason='fallback'):
    """Create a simple text-based banner using Pillow only."""
    if not PIL_AVAILABLE:
        return {
            'success': False,
            'error': 'Pillow is required for banner generation. Please install pillow.',
        }

    width, height = 900, 900

    # --- Background: deep teal gradient to mimic provided reference ---
    start_color = (4, 37, 64)
    end_color = (8, 88, 133)
    img = Image.new('RGB', (width, height), start_color)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Subtle abstract network nodes/lines
    nodes = []
    for _ in range(45):
        x = random.randint(0, width)
        y = random.randint(0, height)
        nodes.append((x, y))
        radius = random.randint(2, 4)
        node_color = (255, 255, 255, 120)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=node_color)

    for _ in range(55):
        a, b = random.sample(nodes, 2)
        alpha = random.randint(30, 80)
        line_color = (255, 255, 255, alpha)
        draw.line([a, b], fill=line_color, width=1)

    # Text preparation
    def load_font(size, bold=False):
        if not PIL_AVAILABLE:
            return None
        font_candidates = [
            ("arialbd.ttf" if bold else "arial.ttf"),
            ("Calibri Bold.ttf" if bold else "Calibri.ttf"),
            ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        ]
        for font_name in font_candidates:
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    tiny_font = load_font(26)
    small_font = load_font(32)
    medium_font = load_font(44)
    large_font = load_font(90, bold=True)

    # Helper to center text
    def draw_centered(text, font, y, color=(255, 255, 255)):
        if not text:
            return y
        text = text.upper()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) / 2
        draw.text((x, y), text, font=font, fill=color)
        return y + _font_line_height(font) + 5

    top_label = (event.department or 'Campus Nexus').upper()
    event_date = event.event_date.strftime('%d %b') if event.event_date else ''
    location = event.location or ''
    year = event.event_date.strftime('%Y') if event.event_date else str(timezone.now().year)

    current_y = 90
    current_y = draw_centered(top_label, small_font, current_y, color=(200, 230, 255))
    if event_date:
        current_y = draw_centered(event_date.upper(), tiny_font, current_y, color=(200, 230, 255))

    # Title block with divider
    current_y += 60
    title_text = (event.title or 'Tech Event').upper()
    title_lines = textwrap.wrap(title_text, width=12) or [title_text]
    for line in title_lines[:2]:
        current_y = draw_centered(line, large_font, current_y, color=(255, 255, 255))

    # Stylized divider
    draw_centered('─' * 10, tiny_font, current_y, color=(200, 230, 255))
    current_y += 40

    current_y = draw_centered(year, medium_font, current_y, color=(200, 230, 255))
    current_y = draw_centered('─' * 4, tiny_font, current_y, color=(200, 230, 255))
    current_y += 30

    if location:
        current_y = draw_centered(location, medium_font, current_y + 20, color=(210, 235, 255))

    # Limit description to a short sentence
    description = (event.description or '').strip()
    if description:
        if len(description) > 140:
            description = description[:137].rsplit(' ', 1)[0] + '...'
    else:
        description = 'Experience the best of campus innovation.'
    current_y = draw_centered(description, tiny_font, current_y + 20, color=(210, 235, 255))

    # Website / CTA near bottom
    cta = event.qr_code_data or 'www.campusnexus.edu'
    draw_centered(cta.lower(), small_font, height - 100, color=(200, 230, 255))

    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    return {
        'success': True,
        'image_file': ContentFile(img_buffer.read(), name=_build_banner_filename(event, prefix='simple_banner')),
        'message': 'Simple banner generated locally.' if reason == 'fallback' else reason,
        'generated_via': reason,
    }


def generate_event_banner_ai(event):
    """Generate event banner; falls back to a simple local design when AI is unavailable."""
    if not PIL_AVAILABLE:
        return {
            'success': False,
            'error': 'PIL/Pillow library not available. Please install Pillow: pip install Pillow'
        }

    if not GENAI_AVAILABLE or not GENAI_API_KEY:
        logger.info('Gemini API unavailable; using simple banner fallback.')
        return generate_simple_banner(event)
    
    try:
        # Create a detailed prompt for banner generation
        prompt = f"""Create a vibrant, professional event banner/poster for a campus event with the following details:
        
Event Title: {event.title}
Category: {event.get_category_display()}
Department: {event.department}
Date: {event.event_date.strftime('%B %d, %Y at %I:%M %p')}
Location: {event.location}
Description: {event.description[:200]}...

Style requirements:
- Modern, eye-catching design suitable for campus events
- Professional and vibrant colors
- Include event title prominently
- Include date and location
- Banner dimensions: 1200x400 pixels (landscape orientation)
- Clean, readable text
- Engaging visual elements related to the event category
- Suitable for digital display and printing
"""
        
        # Try to use Google Generative AI image generation if available.
        # Prefer the newer `google.genai` client (models.generate_content) and
        # fall back to the older `google.generativeai.images.generate` path.
        try:
            # First attempt: new GenAI client from `google.genai`
            try:
                from google import genai as ggenai
                from google.genai import types as gtypes

                client = ggenai.Client()
                model_to_use = getattr(settings, 'GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')

                # Call the newer models.generate_content API with a prompt.
                # The SDK may return parts that include inline image data which
                # can be converted to a PIL.Image via `part.as_image()`.
                response = client.models.generate_content(
                    model=model_to_use,
                    contents=[prompt],
                )

                img = None
                for part in getattr(response, 'parts', []) or []:
                    # If SDK exposes inline image helper, prefer that
                    if getattr(part, 'inline_data', None) is not None:
                        try:
                            possible = part.as_image()
                            if isinstance(possible, Image.Image):
                                img = possible
                            else:
                                img = Image.open(BytesIO(possible))
                        except Exception:
                            # Try raw attributes
                            raw = getattr(part, 'image', None) or getattr(part, 'b64', None)
                            if raw:
                                if isinstance(raw, str):
                                    img = Image.open(BytesIO(base64.b64decode(raw)))
                                else:
                                    img = Image.open(BytesIO(raw))
                        if img:
                            break

                    # Some parts may contain a direct URL in text
                    if getattr(part, 'text', None) and isinstance(part.text, str) and part.text.startswith('http'):
                        try:
                            r = requests.get(part.text)
                            r.raise_for_status()
                            img = Image.open(BytesIO(r.content))
                            break
                        except Exception:
                            continue

                if img is not None:
                    banner_img = img.resize((1200, 400), Image.Resampling.LANCZOS)
                    img_buffer = BytesIO()
                    banner_img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    filename = _build_banner_filename(event)
                    return {
                        'success': True,
                        'image_file': ContentFile(img_buffer.read(), name=filename),
                        'message': 'Banner generated successfully (genai client)'
                    }
            except Exception:
                # If the newer client isn't available or fails, fall through
                # to the older/installed SDK path below.
                pass

            # Second attempt: older `google.generativeai` style SDK (images.generate)
            model_name = getattr(settings, 'GEMINI_IMAGE_MODEL', 'image-bison')

            # Attempt to call the images API on the installed `genai` import
            if hasattr(genai, 'images') and callable(getattr(genai, 'images').generate):
                try:
                    resp = genai.images.generate(
                        model=model_name,
                        prompt=prompt,
                        size="1792x1024",
                    )

                    # Attempt to extract a URL or binary data from the response
                    image_url = None
                    if isinstance(resp, dict):
                        data = resp.get('data') or resp.get('candidates') or resp.get('outputs')
                        if data and len(data) > 0:
                            first = data[0]
                            image_url = first.get('url') or first.get('image') or first.get('b64_json')
                    else:
                        data = getattr(resp, 'data', None)
                        if data and len(data) > 0:
                            first = data[0]
                            image_url = getattr(first, 'url', None) or getattr(first, 'image', None)

                    if image_url is None:
                        raise ValueError('No image URL returned from Gemini image API')

                    # If response is base64 JSON, decode
                    if isinstance(image_url, str) and image_url.startswith('data:image'):
                        header, b64 = image_url.split(',', 1)
                        img_data = base64.b64decode(b64)
                    elif isinstance(image_url, str) and image_url.startswith('http'):
                        img_response = requests.get(image_url)
                        img_response.raise_for_status()
                        img_data = img_response.content
                    else:
                        img_data = base64.b64decode(image_url)

                    img = Image.open(BytesIO(img_data))
                    banner_img = img.resize((1200, 400), Image.Resampling.LANCZOS)

                    img_buffer = BytesIO()
                    banner_img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)

                    filename = _build_banner_filename(event)

                    return {
                        'success': True,
                        'image_file': ContentFile(img_buffer.read(), name=filename),
                        'message': 'Banner generated successfully'
                    }
                except Exception as api_error:
                    logger.error(f"Gemini image API error: {api_error}")
                    raise
            else:
                # SDK image helper not present — inform the user
                raise NotImplementedError('Gemini image generation via installed SDK is not available. Please install/upgrade the google generative AI package or use an external image generation service.')
        except Exception as e:
            # Bubble up with helpful messages but still deliver a banner
            logger.error(f"Banner generation error: {e}")
            error_str = str(e)

            if 'billing' in error_str.lower() or 'limit' in error_str.lower() or 'quota' in error_str.lower():
                return generate_simple_banner(event, reason='Generated locally because Gemini quota was hit.')
            if 'unauthorized' in error_str.lower() or 'invalid' in error_str.lower() or 'api key' in error_str.lower():
                return generate_simple_banner(event, reason='Generated locally because the Gemini API key was invalid.')

            # Otherwise fall back with context so admins know why
            return generate_simple_banner(event, reason=f'Generated locally because Gemini failed ({error_str}).')
        
        # Extract image URL from response
        if not response.data or len(response.data) == 0:
            raise ValueError("No image data returned from Gemini image API")
        
        image_url = response.data[0].url
        if not image_url:
            raise ValueError("No image URL in response")
        
        # Download the image
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        # Convert to PIL Image and resize to banner dimensions (1200x400)
        img = Image.open(BytesIO(img_response.content))
        # Resize to banner dimensions (landscape)
        banner_img = img.resize((1200, 400), Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        img_buffer = BytesIO()
        banner_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Generate filename - use event ID if available, otherwise use timestamp
        filename = _build_banner_filename(event)
        
        return {
            'success': True,
            'image_file': ContentFile(img_buffer.read(), name=filename),
            'message': 'Banner generated successfully'
        }
        
    except Exception as e:
        logger.error(f"Banner generation error: {e}")
        
        # Provide user-friendly error messages
        error_str = str(e)
        
        # Check for billing-related errors
        if 'billing' in error_str.lower() or 'limit' in error_str.lower() or 'quota' in error_str.lower():
            return generate_simple_banner(event, reason='Generated locally because Gemini quota was hit.')
        
        # Check for authentication errors
        if 'unauthorized' in error_str.lower() or 'invalid' in error_str.lower() or 'api key' in error_str.lower():
            return generate_simple_banner(event, reason='Generated locally because API key was invalid.')
        
        # Check for rate limit errors
        if 'rate limit' in error_str.lower():
            return generate_simple_banner(event, reason='Generated locally because Gemini rate limit was exceeded.')
        
        # Generic error - fall back to local template with a friendly note
        logger.warning('Gemini generation failed, using fallback: %s', error_str)
        return generate_simple_banner(
            event,
            reason='Banner generated with built-in template (Gemini unavailable).'
        )


def generate_event_poster(event):
    """Generate event poster using AI (placeholder for Gemini integration)."""
    # This would integrate with Gemini image models or similar for poster generation
    # For now, return a placeholder
    return {
        'poster_url': None,
        'status': 'pending'
    }

