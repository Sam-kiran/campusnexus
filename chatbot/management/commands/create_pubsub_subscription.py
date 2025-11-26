from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create a Pub/Sub subscription (push or pull) and grant Gmail publish rights to the topic.'

    def add_arguments(self, parser):
        parser.add_argument('--project', type=str, help='GCP project id')
        parser.add_argument('--topic', type=str, help='Full topic name: projects/PROJECT_ID/topics/TOPIC_NAME')
        parser.add_argument('--subscription', type=str, help='Subscription id (name) to create')
        parser.add_argument('--push-endpoint', type=str, help='Optional push endpoint HTTPS URL for push subscriptions')
        parser.add_argument('--ack-deadline', type=int, default=30, help='Ack deadline seconds')

    def handle(self, *args, **options):
        project = options.get('project') or os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('PROJECT_ID')
        topic = options.get('topic') or getattr(settings, 'GMAIL_PUBSUB_TOPIC', None)
        subscription_id = options.get('subscription')
        push_endpoint = options.get('push_endpoint')
        ack_deadline = options.get('ack_deadline')

        if not topic:
            raise CommandError('Pub/Sub topic required. Provide --topic or set GMAIL_PUBSUB_TOPIC in settings or PROJECT_ID env vars.')
        if not subscription_id:
            raise CommandError('Subscription id required. Provide --subscription argument.')

        # Check credentials
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not cred_path or not os.path.exists(cred_path):
            raise CommandError('Google credentials not found. Please set GOOGLE_APPLICATION_CREDENTIALS to your service account JSON path and try again.')

        # Import Google Cloud Pub/Sub client lazily
        try:
            from google.cloud import pubsub_v1
            from google.iam.v1 import iam_policy_pb2, policy_pb2
        except Exception as e:
            raise CommandError(f'google-cloud-pubsub library required. Install it: pip install google-cloud-pubsub. Error: {e}')

        # Create subscription
        subscriber = pubsub_v1.SubscriberClient()
        publisher = pubsub_v1.PublisherClient()

        # Compose subscription path
        # If topic is provided as short name, allow both
        # Expect topic like 'projects/PROJECT_ID/topics/TOPIC_NAME'
        topic_path = topic

        subscription_path = subscriber.subscription_path(project, subscription_id)

        try:
            if push_endpoint:
                push_config = pubsub_v1.types.PushConfig(push_endpoint=push_endpoint)
                subscriber.create_subscription(name=subscription_path, topic=topic_path, push_config=push_config, ack_deadline_seconds=ack_deadline)
                self.stdout.write(self.style.SUCCESS(f'Created push subscription: {subscription_path} -> {topic_path} (push endpoint: {push_endpoint})'))
            else:
                subscriber.create_subscription(name=subscription_path, topic=topic_path, ack_deadline_seconds=ack_deadline)
                self.stdout.write(self.style.SUCCESS(f'Created pull subscription: {subscription_path} -> {topic_path}'))
        except Exception as e:
            # If already exists, inform and continue
            if 'already exists' in str(e):
                self.stdout.write(self.style.WARNING(f'Subscription already exists: {subscription_path}'))
            else:
                raise CommandError(f'Error creating subscription: {e}')

        # Grant publisher role to gmail-api-push@system.gserviceaccount.com on the topic
        try:
            topic_resource = topic_path
            policy = publisher.get_iam_policy(request={"resource": topic_resource})
            member = 'serviceAccount:gmail-api-push@system.gserviceaccount.com'
            role = 'roles/pubsub.publisher'

            # Check if binding exists
            binding_exists = False
            for b in policy.bindings:
                if b.role == role and member in b.members:
                    binding_exists = True
                    break

            if not binding_exists:
                policy.bindings.add(role=role, members=[member])
                publisher.set_iam_policy(request={"resource": topic_resource, "policy": policy})
                self.stdout.write(self.style.SUCCESS(f'Added IAM binding {role} for {member} on {topic_resource}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'IAM binding already present for {member} on {topic_resource}'))
        except Exception as e:
            raise CommandError(f'Error setting IAM policy on topic: {e}')
