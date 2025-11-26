"""
WSGI config for CampusNexus project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campusnexus.settings')

application = get_wsgi_application()
# Export `app` for platforms that expect the WSGI callable to be named `app`.
app = application

