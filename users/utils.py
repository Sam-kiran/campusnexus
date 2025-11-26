"""Utility functions for user authentication with Supabase."""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Optional Supabase import
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None


def get_supabase_client():
    """Get Supabase client instance."""
    if not SUPABASE_AVAILABLE:
        return None
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return supabase
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        return None


def validate_supabase_auth(email: str, password: str) -> dict:
    """Validate user credentials with Supabase."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            return response.user
        return None
    except Exception as e:
        logger.error(f"Supabase auth error: {e}")
        return None


def create_supabase_user(email: str, password: str) -> dict:
    """Create a new user in Supabase."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            return response.user
        return None
    except Exception as e:
        logger.error(f"Supabase signup error: {e}")
        return None


def verify_supabase_token(token: str) -> dict:
    """Verify Supabase authentication token."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.auth.get_user(token)
        if response.user:
            return response.user
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

