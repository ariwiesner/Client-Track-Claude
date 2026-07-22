import datetime
import logging
import os

# Google returns previously-granted scopes alongside newly-requested ones
# (e.g. the old calendar.readonly grant from testing quickstart.py), which
# oauthlib otherwise treats as a fatal scope-mismatch instead of a warning.
# Must be set before oauthlib's session/token parsing runs.
os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', '1')

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.models import GoogleCalendarCredential, Meeting

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


def _client_config():
    return {
        'web': {
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [settings.GOOGLE_OAUTH_REDIRECT_URI],
        }
    }


def build_auth_flow():
    # autogenerate_code_verifier=False: PKCE's verifier lives on the Flow
    # instance in memory, but start and callback are two separate HTTP
    # requests that each build their own Flow — a verifier generated during
    # start() is never available to callback(), so exchange always failed
    # with "Missing code verifier". PKCE protects public clients that can't
    # hold a secret; this is a confidential server-side client (has a
    # client_secret), so skipping it is a standard, safe simplification.
    return Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
        autogenerate_code_verifier=False,
    )


def save_credentials(user, flow_credentials):
    GoogleCalendarCredential.objects.update_or_create(
        user=user,
        defaults={
            'refresh_token': flow_credentials.refresh_token,
            'access_token': flow_credentials.token,
            'token_expiry': flow_credentials.expiry,
        },
    )


def get_credentials(user):
    """Live google.oauth2.credentials.Credentials for this user, refreshing
    and persisting a new access token if the stored one has expired. Returns
    None if the user never connected a Google account — every caller in this
    module treats that as "sync is a no-op for them", not an error.
    """
    if not user:
        return None
    try:
        stored = user.google_calendar_credential
    except GoogleCalendarCredential.DoesNotExist:
        return None

    creds = Credentials(
        token=stored.access_token,
        refresh_token=stored.refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=SCOPES,
    )
    if not creds.valid:
        creds.refresh(Request())
        stored.access_token = creds.token
        stored.token_expiry = creds.expiry
        stored.save(update_fields=['access_token', 'token_expiry'])
    return creds


def _service(user):
    creds = get_credentials(user)
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)


def _event_body(meeting):
    end = meeting.end_time or (meeting.start_time + datetime.timedelta(hours=1))
    return {
        'summary': meeting.title,
        'description': meeting.notes,
        'start': {'dateTime': meeting.start_time.isoformat()},
        'end': {'dateTime': end.isoformat()},
    }


def push_create(meeting):
    if meeting.google_event_id:
        return
    service = _service(meeting.created_by)
    if not service:
        return
    try:
        event = service.events().insert(calendarId='primary', body=_event_body(meeting)).execute()
    except HttpError:
        logger.exception('Failed to create Google Calendar event for meeting %s', meeting.id)
        return
    meeting.google_event_id = event['id']
    meeting.synced_at = timezone.now()
    meeting.save(update_fields=['google_event_id', 'synced_at'])


def push_update(meeting):
    if not meeting.google_event_id:
        push_create(meeting)
        return
    service = _service(meeting.created_by)
    if not service:
        return
    try:
        service.events().update(
            calendarId='primary', eventId=meeting.google_event_id, body=_event_body(meeting)
        ).execute()
    except HttpError:
        logger.exception('Failed to update Google Calendar event for meeting %s', meeting.id)
        return
    meeting.synced_at = timezone.now()
    meeting.save(update_fields=['synced_at'])


def push_delete(meeting):
    if not meeting.google_event_id:
        return
    service = _service(meeting.created_by)
    if not service:
        return
    try:
        service.events().delete(calendarId='primary', eventId=meeting.google_event_id).execute()
    except HttpError as error:
        if error.resp.status != 410:  # already gone on Google's side — fine
            logger.exception('Failed to delete Google Calendar event for meeting %s', meeting.id)


def _parse_event_start(event_time):
    if 'dateTime' in event_time:
        return datetime.datetime.fromisoformat(event_time['dateTime'])
    # All-day event: only a date, no time — treat as starting at midnight.
    return timezone.make_aware(
        datetime.datetime.strptime(event_time['date'], '%Y-%m-%d')
    )


def pull_events():
    """Mirror upcoming events from every connected Google Calendar into
    local Meeting rows, skipping ones already linked by google_event_id so
    repeated runs don't create duplicates. New meetings created this way are
    marked reminder_sent so our own reminder pipeline doesn't duplicate
    whatever reminder Google already sends for them.
    """
    created = 0
    for cred in GoogleCalendarCredential.objects.select_related('user').all():
        service = _service(cred.user)
        if not service:
            continue
        known_ids = set(
            Meeting.objects.exclude(google_event_id='').values_list('google_event_id', flat=True)
        )
        now = timezone.now().isoformat()
        try:
            events = (
                service.events()
                .list(
                    calendarId='primary', timeMin=now, singleEvents=True,
                    orderBy='startTime', maxResults=50,
                )
                .execute()
                .get('items', [])
            )
        except HttpError:
            logger.exception('Failed to pull Google Calendar events for %s', cred.user)
            continue

        for event in events:
            if event['id'] in known_ids or event.get('status') == 'cancelled':
                continue
            start = event.get('start') or {}
            if 'dateTime' not in start and 'date' not in start:
                continue
            Meeting.objects.create(
                title=event.get('summary') or '(ללא כותרת)',
                notes=event.get('description', ''),
                start_time=_parse_event_start(start),
                created_by=cred.user,
                google_event_id=event['id'],
                synced_at=timezone.now(),
                reminder_sent=True,
            )
            created += 1
    return created
