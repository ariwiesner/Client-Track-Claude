"""One-off import of clients from the WhatsApp-received רשימת מיוצגים Excel file.

Groups rows by שם תיק (client name must be unique in this system). The first
row for each name becomes the main client record; any additional rows for
that same name (different מספר תיק / נושא מס / etc.) are appended to the
notes field instead of creating duplicate clients. Exact duplicate rows
(identical on every field) are skipped entirely and reported.
"""
import os
import sys
from collections import defaultdict

import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import openpyxl
from core.models import Client

EXCEL_PATH = (
    r'C:\Users\ארי ויזנר\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm'
    r'\LocalState\sessions\52B1E575613605C358958F4E56AA94DCCF5B3A3D\transfers\2026-29'
    r'\19_07_2026 רשימת מיוצגים מקוצרת.xlsx'
)
HOURLY_RATE = 150

wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
ws = wb['Table1']
rows = list(ws.iter_rows(values_only=True))
header, data_rows = rows[0], rows[1:]

# header: מספר תיק, נושא מס, שם תיק, משרד, חוליה, ס.תיק, מייצג, תחילת ייצוג, תוקף 91, פרטי בנק

groups = defaultdict(list)
for r in data_rows:
    case_number, tax_subject, name, _office, unit, sub_case, rep, rep_start, valid_91, bank = (
        (v.strip() if isinstance(v, str) else v) for v in r
    )
    if not name:
        continue
    groups[name].append({
        'case_number': case_number or '',
        'tax_subject': tax_subject or '',
        'unit': unit or '',
        'sub_case': sub_case or '',
        'representative': rep or '',
        'representation_start': rep_start or '',
        'validity_91': valid_91 or '',
        'bank_details': bank or '',
    })

created, updated, exact_dupes_skipped = 0, 0, 0
dupe_report = []

for name, entries in groups.items():
    # de-dupe exact repeats for the same name
    seen = []
    unique_entries = []
    for e in entries:
        fp = tuple(e.values())
        if fp in seen:
            exact_dupes_skipped += 1
            continue
        seen.append(fp)
        unique_entries.append(e)

    main = unique_entries[0]
    extra = unique_entries[1:]

    notes_lines = []
    if extra:
        dupe_report.append((name, main['case_number'], len(extra)))
        for e in extra:
            notes_lines.append(
                f"תיק נוסף — מספר תיק: {e['case_number']}, נושא מס: {e['tax_subject']}, "
                f"חוליה: {e['unit']}, ס.תיק: {e['sub_case']}, מייצג: {e['representative']}, "
                f"תחילת ייצוג: {e['representation_start']}"
            )
    notes = '\n'.join(notes_lines)

    defaults = {
        'case_number': main['case_number'],
        'tax_subject': main['tax_subject'],
        'unit': main['unit'],
        'sub_case': main['sub_case'],
        'representative': main['representative'],
        'representation_start': main['representation_start'],
        'validity_91': main['validity_91'],
        'bank_details': main['bank_details'],
        'notes': notes,
        'phone': '',
    }

    obj, was_created = Client.objects.get_or_create(
        name=name,
        defaults={**defaults, 'hourly_rate': HOURLY_RATE},
    )
    if was_created:
        created += 1
    else:
        for k, v in defaults.items():
            setattr(obj, k, v)
        obj.save()
        updated += 1

with open(
    os.path.join(os.path.dirname(__file__), '..', 'scratch', 'import_report.txt'),
    'w', encoding='utf-8',
) as f:
    f.write(f"Created: {created}\n")
    f.write(f"Updated: {updated}\n")
    f.write(f"Exact duplicate rows skipped: {exact_dupes_skipped}\n")
    f.write(f"Clients with multiple תיקים (merged into notes): {len(dupe_report)}\n\n")
    f.write("--- Multi-case clients (name | main מספר תיק | extra תיקים count) ---\n")
    for name, case_number, count in dupe_report:
        f.write(f"{name} | {case_number} | +{count}\n")

print("done")
