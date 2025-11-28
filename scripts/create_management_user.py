import os
import sys
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campusnexus.settings')

import django
django.setup()

from users.models import User

USERNAME = os.environ.get('MG_USERNAME', 'manager1')
EMAIL = os.environ.get('MG_EMAIL', 'manager1@saividya.ac.in')
PASSWORD = os.environ.get('MG_PASSWORD', 'SecurePass123')

if User.objects.filter(email=EMAIL).exists():
    user = User.objects.get(email=EMAIL)
    print('User already exists:', user.id, user.username, user.email, user.role)
else:
    user = User.objects.create_user(username=USERNAME, email=EMAIL, password=PASSWORD, role='management')
    user.is_verified = True
    user.save()
    print('Created user:', user.id, user.username, user.email, user.role)
