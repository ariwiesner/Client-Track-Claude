from datetime import timedelta

from django.utils import timezone

from core.models import Meeting
from core.services import notifications


def send_due_reminders():
    """Check every not-yet-reminded upcoming meeting and fire a notification
    for any whose lead time has arrived. Small table (one office's
    meetings) — plain Python filtering avoids fragile ORM duration-arithmetic
    across the SQLite/Postgres backends this app runs on locally vs. in prod.
    """
    now = timezone.now()
    sent = 0
    for meeting in Meeting.objects.filter(reminder_sent=False, start_time__gt=now):
        remind_at = meeting.start_time - timedelta(minutes=meeting.reminder_minutes_before)
        if remind_at <= now:
            notifications.notify_meeting_reminder(meeting)
            meeting.reminder_sent = True
            meeting.save(update_fields=['reminder_sent'])
            sent += 1
    return sent
