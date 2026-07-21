import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from core.models import PushSubscription

logger = logging.getLogger(__name__)


def send_push(notification):
    if not settings.VAPID_PRIVATE_KEY:
        return  # push isn't configured on this deployment — skip silently

    payload = json.dumps({'title': 'מעקב לקוחות', 'body': notification.message})
    claims = {'sub': f'mailto:{settings.VAPID_CLAIMS_EMAIL}'}

    for sub in PushSubscription.objects.all():
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=dict(claims),
            )
        except WebPushException as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (404, 410):
                sub.delete()  # expired/revoked — self-prune
            else:
                logger.warning('Push send failed for subscription %s: %s', sub.id, exc)
        except Exception:
            logger.exception('Unexpected error sending push for subscription %s', sub.id)
