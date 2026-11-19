from django.core.management.base import BaseCommand

from core.services import rivhit


class Command(BaseCommand):
    help = "Match every Client to a Rivhit customer by name and pull their profile/invoice totals."

    def handle(self, *args, **options):
        matched, unmatched = rivhit.sync_clients()
        self.stdout.write(f'Synced Rivhit data for {matched} client(s).')
        if unmatched:
            self.stdout.write(
                f'No Rivhit match found for {len(unmatched)} client(s): ' + ', '.join(unmatched)
            )
