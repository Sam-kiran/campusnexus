from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create a Pub/Sub subscription and optionally grant Gmail publish rights on the topic.'

    def add_arguments(self, parser):
        parser.add_argument('--project', type=str, help='GCP project id')
        parser.add_argument('--topic', type=str, help='Pub/Sub topic name (can be full: projects/PROJECT_ID/topics/TOPIC)')
        parser.add_argument('--subscription', type=str, help='Subscription name (short name, not full path)')
        parser.add_argument('--push-endpoint', type=str, help='Push endpoint (https url) for push subscription')
        parser.add_argument('--mode', choices=['push', 'pull'], default='pull', help='Subscription mode')
        parser.add_argument('--grant-gmail-publisher', action='store_true', help='Grant pubsub.publisher to gmail-api-push@system.gserviceaccount.com on the topic')

    def handle(self, *args, **options):
        project = options.get('project') or getattr(settings, 'GCP_PROJECT_ID', None)
        topic = options.get('topic') or getattr(settings, 'GMAIL_PUBSUB_TOPIC', None)
        subscription = options.get('subscription')
        push_endpoint = options.get('push_endpoint')
        mode = options.get('mode')
        grant = options.get('grant_gmail_publisher')

        if not topic:
            raise CommandError('Topic name required. Provide --topic or set GMAIL_PUBSUB_TOPIC in settings.')

        # Accept full topic name or short topic
        # topic_full should be projects/{project}/topics/{topic}
        if topic.startswith('projects/'):
            topic_full = topic
            try:
                # extract project from topic if missing
                project = topic.split('/')[1]
            except Exception:
                pass
        else:
            if not project:
                raise CommandError('Project id is required when topic is not fully-qualified. Provide --project or set GCP_PROJECT_ID in settings.')
            topic_full = f'projects/{project}/topics/{topic}'

        if not subscription:
            raise CommandError('Subscription name required. Provide --subscription SUB_NAME')

        # Check for GOOGLE_APPLICATION_CREDENTIALS or application default credentials
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not cred_path:
            raise CommandError('Google credentials not found. Set the environment variable GOOGLE_APPLICATION_CREDENTIALS to the service account JSON path and try again.')

        try:
            from google.cloud import pubsub_v1
            from google.api_core.exceptions import AlreadyExists
        except Exception as e:
            raise CommandError(f'google-cloud-pubsub library not installed: {e}. Run pip install google-cloud-pubsub')

        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()

        # Create subscription path
        sub_path = subscriber.subscription_path(project, subscription)

        try:
            if mode == 'pull':
                subscriber.create_subscription(name=sub_path, topic=topic_full)
                self.stdout.write(self.style.SUCCESS(f'Pull subscription created: {sub_path}'))
            else:
                if not push_endpoint:
                    raise CommandError('Push endpoint required for push mode (--push-endpoint)')
                push_config = pubsub_v1.types.PushConfig(push_endpoint=push_endpoint)
                subscriber.create_subscription(name=sub_path, topic=topic_full, push_config=push_config)
                self.stdout.write(self.style.SUCCESS(f'Push subscription created: {sub_path} -> {push_endpoint}'))
        except AlreadyExists:
            self.stdout.write(self.style.WARNING(f'Subscription already exists: {sub_path}'))
        except Exception as e:
            raise CommandError(f'Error creating subscription: {e}')

        if grant:
            try:
                # Add IAM binding for gmail-api-push@system.gserviceaccount.com as pubsub.publisher
                policy = publisher.get_iam_policy(request={'resource': topic_full})
                binding_found = False
                member = 'serviceAccount:gmail-api-push@system.gserviceaccount.com'
                for b in policy.bindings:
                    if b.role == 'roles/pubsub.publisher':
                        if member in b.members:
                            binding_found = True
                            break
                        else:
                            b.members.append(member)
                            binding_found = True
                            break

                if not binding_found:
                    policy.bindings.add(role='roles/pubsub.publisher', members=[member])

                publisher.set_iam_policy(request={'resource': topic_full, 'policy': policy})
                self.stdout.write(self.style.SUCCESS(f'Granted roles/pubsub.publisher to {member} on {topic_full}'))
            except Exception as e:
                raise CommandError(f'Error updating IAM policy on topic: {e}')

        self.stdout.write(self.style.SUCCESS('Done'))
