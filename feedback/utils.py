"""Utility functions for feedback processing."""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Initialize sentiment analyzer (lazy loading)
_sentiment_analyzer = None

# Try to import transformers, but make it optional
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers library not available. Sentiment analysis will be disabled.")


def get_sentiment_analyzer():
    """Get or initialize sentiment analyzer."""
    global _sentiment_analyzer
    if not TRANSFORMERS_AVAILABLE:
        return None
    
    if _sentiment_analyzer is None:
        try:
            _sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=-1  # Use CPU, set to 0 for GPU
            )
        except Exception as e:
            logger.error(f"Error initializing sentiment analyzer: {e}")
            return None
    return _sentiment_analyzer


def analyze_sentiment(text):
    """Analyze sentiment of feedback text using BERT model."""
    if not text or len(text.strip()) == 0:
        return {'score': 0.0, 'label': 'neutral'}
    
    if not TRANSFORMERS_AVAILABLE:
        # Simple keyword-based sentiment if transformers not available
        text_lower = text.lower()
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'love', 'enjoyed', 'fantastic']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'disappointed', 'poor', 'worst']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            return {'score': 0.5, 'label': 'positive'}
        elif neg_count > pos_count:
            return {'score': -0.5, 'label': 'negative'}
        else:
            return {'score': 0.0, 'label': 'neutral'}
    
    try:
        analyzer = get_sentiment_analyzer()
        if not analyzer:
            return {'score': 0.0, 'label': 'neutral'}
        
        result = analyzer(text)[0]
        
        # Map result to our labels
        label_map = {
            'LABEL_0': 'negative',
            'LABEL_1': 'neutral',
            'LABEL_2': 'positive'
        }
        
        label = label_map.get(result['label'], 'neutral')
        score = result['score']
        
        # Convert to -1 to 1 scale
        if label == 'negative':
            score = -score
        elif label == 'neutral':
            score = 0.0
        
        return {
            'score': score,
            'label': label
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {'score': 0.0, 'label': 'neutral'}


def update_feedback_analytics(event):
    """Update feedback analytics for an event."""
    from django.db import models
    from .models import Feedback, FeedbackAnalytics
    
    feedbacks = Feedback.objects.filter(event=event)
    
    analytics, created = FeedbackAnalytics.objects.get_or_create(event=event)
    
    analytics.total_feedbacks = feedbacks.count()
    analytics.average_rating = feedbacks.aggregate(models.Avg('rating'))['rating__avg'] or 0.0
    analytics.positive_sentiment_count = feedbacks.filter(sentiment_label='positive').count()
    analytics.neutral_sentiment_count = feedbacks.filter(sentiment_label='neutral').count()
    analytics.negative_sentiment_count = feedbacks.filter(sentiment_label='negative').count()
    
    # Emotion distribution
    emotion_dist = {}
    for emotion_code, _ in Feedback.EMOTION_CHOICES:
        emotion_dist[emotion_code] = feedbacks.filter(emotion=emotion_code).count()
    analytics.emotion_distribution = emotion_dist
    
    analytics.save()

