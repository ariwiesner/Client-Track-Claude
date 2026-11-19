from django.core.management.base import BaseCommand, CommandError

from core.services import fee_import


class Command(BaseCommand):
    help = (
        "Import each client's fixed annual fee from the office's שכ\"ט Excel "
        "workbook (sheets 'שכט <year>'), matching rows to Client by name. "
        "Only exact and high-confidence name matches are applied automatically "
        "— everything else is listed for manual review, nothing is guessed."
    )

    def add_arguments(self, parser):
        parser.add_argument('xlsx_path', help='Path to the דיווחים חודשיים.xlsx workbook')
        parser.add_argument(
            '--years', nargs='+', type=int, default=None,
            help='Which שכט <year> sheets to import (default: every one found)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Show what would be imported/skipped without writing anything",
        )

    def handle(self, *args, **options):
        try:
            result = fee_import.import_annual_fees(
                options['xlsx_path'],
                years=options['years'],
                dry_run=options['dry_run'],
            )
        except fee_import.FeeImportError as exc:
            raise CommandError(str(exc))

        verb = 'Would import' if options['dry_run'] else 'Imported'
        self.stdout.write(f'{verb} {len(result.applied)} client-year fee(s).')

        if result.ambiguous:
            self.stdout.write(f'\nSkipped {len(result.ambiguous)} ambiguous match(es):')
            for row in result.ambiguous:
                candidates = ', '.join(f'{c["name"]} ({c["score"]:.0f}%)' for c in row['candidates'])
                self.stdout.write(f'  {row["excel_name"]!r} [{row["year"]}] -> {candidates}')

        if result.no_match:
            self.stdout.write(f'\nSkipped {len(result.no_match)} client(s) with no match:')
            for row in result.no_match:
                self.stdout.write(f'  {row["excel_name"]!r} [{row["year"]}]')
