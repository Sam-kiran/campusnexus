#!/usr/bin/env python
"""Quick test script for chatbot routing."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campusnexus.settings')
django.setup()

from chatbot.utils import process_chatbot_query
from users.models import User

user = User.objects.filter(role='student').first()
if not user:
    print("No student user found!")
    exit(1)

queries = [
    'my events',
    'i registered for events',
    'are there any upcoming events?',
    'show me tech events',
    'what events are happening tomorrow?'
]

print("Testing chatbot query routing:\n")
for q in queries:
    result = process_chatbot_query(q, user)
    print(f"Query: '{q}'")
    print(f"  -> Type: {result.get('type')}")
    print(f"  -> Events found: {len(result.get('data', []))}")
    print(f"  -> Response: {result.get('text')[:80]}...")
    print()

