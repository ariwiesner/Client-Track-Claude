from django.core.management.base import BaseCommand

from core.services import google_calendar


class Command(BaseCommand):
    help = "Pull new events from every connected user's Google Calendar into Meeting rows."

    def handle(self, *args, **options):
        count = google_calendar.pull_events()
        self.stdout.write(f'Pulled {count} new meeting(s) from Google Calendar.')
