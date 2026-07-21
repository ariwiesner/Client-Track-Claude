import threading

from django.core.management.base import BaseCommand

from core.services import meetings


class Command(BaseCommand):
    help = 'Send reminders for meetings whose reminder lead time has arrived.'

    def handle(self, *args, **options):
        count = meetings.send_due_reminders()
        # notify_meeting_reminder (via create_notification) fires the actual
        # push over a background daemon thread — fine for gunicorn, whose
        # process never exits, but this command's process exits right after
        # handle() returns, which would kill that thread mid-HTTP-call and
        # the push would never reach the browser. Wait for it here.
        for t in threading.enumerate():
            if t is not threading.main_thread():
                t.join(timeout=10)
        self.stdout.write(f'Sent {count} meeting reminder(s).')
