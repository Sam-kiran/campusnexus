import base64
import json
import logging
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

logger = logging.getLogger(__name__)


@csrf_exempt
def gmail_pubsub_push(request):
    """Endpoint to receive Pub/Sub push messages from Gmail -> Pub/Sub -> push subscription.

    Pub/Sub push will POST JSON with a `message` field containing `data` as base64.
    The decoded `data` will typically include JSON with `emailAddress` and `historyId`.
    """
    # Recommended: verify HTTPS + Google auth in production (JWT verification)
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        logger.error(f'Invalid JSON on Pub/Sub push: {e}')
        return HttpResponseBadRequest('Invalid JSON')

    # Pub/Sub push format: {"message": {"data": "BASE64", "messageId": "..."}, "subscription": "..."}
    message = payload.get('message') or {}
    data_b64 = message.get('data')

    if not data_b64:
        logger.warning('Pub/Sub push missing message.data')
        return HttpResponseBadRequest('Missing message.data')

    try:
        decoded = base64.b64decode(data_b64).decode('utf-8')
        msg = json.loads(decoded)
    except Exception as e:
        logger.error(f'Error decoding Pub/Sub message data: {e}')
        return HttpResponseBadRequest('Invalid message data')

    # Example msg from Gmail watch: {"emailAddress":"user@domain","historyId":"12345"}
    email_address = msg.get('emailAddress')
    history_id = msg.get('historyId')

    # Optional: verify X-Goog-Channel-Id header matches expected channel id stored in settings or DB
    expected_channel = getattr(settings, 'GMAIL_PUBSUB_CHANNEL_ID', None)
    received_channel = request.headers.get('X-Goog-Channel-Id') or request.META.get('HTTP_X_GOOG_CHANNEL_ID')
    if expected_channel and received_channel and expected_channel != received_channel:
        logger.warning(f'Channel id mismatch: expected={expected_channel} got={received_channel}')
        # continue processing or reject depending on security policy

    # TODO: process notification => e.g., mark user/unread, fetch new messages via Gmail API using historyId
    logger.info(f'Received Gmail Pub/Sub notification for {email_address}, historyId={history_id}')

    # Acknowledge the POST
    return JsonResponse({'status': 'ok'})
