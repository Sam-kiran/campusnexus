from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import google.auth
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a Gmail watch on the authenticated user to publish notifications to a Pub/Sub topic.'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='Email address of the Gmail account to watch (me for authenticated user)')
        parser.add_argument('--topic', type=str, help='Full Pub/Sub topic name: projects/PROJECT_ID/topics/TOPIC_NAME')
        parser.add_argument('--labelIds', nargs='*', help='Optional Gmail label IDs to watch')

    def handle(self, *args, **options):
        user = options.get('user') or 'me'
        topic = options.get('topic') or getattr(settings, 'GMAIL_PUBSUB_TOPIC', None)
        label_ids = options.get('labelIds') or []

        if not topic:
            raise CommandError('Pub/Sub topic name required. Provide --topic or set GMAIL_PUBSUB_TOPIC in settings.')

        # Use application default credentials or credentials JSON path
        try:
            creds, _ = google.auth.default()
        except Exception as e:
            raise CommandError(f'Error getting application default credentials: {e}')

        service = build('gmail', 'v1', credentials=creds)

        body = {
            'topicName': topic,
        }
        if label_ids:
            body['labelIds'] = label_ids

        try:
            result = service.users().watch(userId=user, body=body).execute()
            # result contains 'historyId' and 'expiration'
            self.stdout.write(self.style.SUCCESS(f'Watch started: {result}'))
            # Optionally store channel id in settings or DB. Gmail watch doesn't return channel id when using Pub/Sub.
        except Exception as e:
            raise CommandError(f'Error starting watch: {e}')
