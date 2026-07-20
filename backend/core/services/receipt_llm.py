import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rapidfuzz import fuzz, process

from core.models import Client, Receipt

# Mirrors helper/config.py's MATCH_CONFIDENCE_THRESHOLD — same fuzzy-match
# approach as the desktop helper's client matching, duplicated here since
# the two apps share no common module.
MATCH_CONFIDENCE_THRESHOLD = 85

_CATEGORY_VALUES = {value for value, _label in Receipt.CATEGORY_CHOICES}


class ExtractionError(Exception):
    """Raised on Gemini/network failure or an unparseable response."""


def extract_receipt(image_file) -> dict:
    """Reads a receipt photo (a freshly uploaded file, or a FieldFile
    reopened from storage for a retry) and returns extracted fields.
    Read-only against the database — never creates/updates rows itself.
    """
    image_file.seek(0)
    try:
        Image.open(image_file).verify()
    except UnidentifiedImageError as exc:
        raise ExtractionError('הקובץ שהועלה אינו תמונה תקינה') from exc
    image_file.seek(0)

    mime_type = getattr(image_file, 'content_type', None) or 'image/jpeg'
    raw = _call_gemini(image_file.read(), mime_type)
    coerced = _coerce_response(raw)

    client_id, score, suggestion = _match_client(coerced.pop('client_name_guess'))
    coerced['client_id'] = client_id
    coerced['client_match_score'] = score
    coerced['client_suggestion'] = suggestion
    return coerced


def _call_gemini(image_bytes: bytes, mime_type: str) -> dict:
    if not settings.GEMINI_API_KEY:
        raise ExtractionError('GEMINI_API_KEY אינו מוגדר בשרת')

    from google import genai
    from google.genai import types

    category_lines = '\n'.join(f'- {value}: {label}' for value, label in Receipt.CATEGORY_CHOICES)

    # Deliberately NOT given the office's client list: earlier versions of
    # this prompt included it as "grounding" and asked the model to guess
    # the closest match, which just invited it to invent a plausible-looking
    # name from that list even when the receipt didn't actually name any
    # client. Matching against real clients happens purely server-side in
    # _match_client — this call only transcribes what's actually printed.
    prompt = f"""You are reading a business receipt (קבלה) photo for an Israeli bookkeeping office.
Extract these fields and return STRICT JSON only, no markdown, no commentary:
{{
  "client_name_guess": string or null,
  "amount": number or null,
  "receipt_number": string or "",
  "receipt_date": "YYYY-MM-DD" or null,
  "category": one of the category ids below
}}

client_name_guess must be a name or business actually printed on THIS
receipt (e.g. a "לכבוד" / customer / recipient / billed-to field) — copy it
as written. If no such name is legible anywhere on the receipt, use null.
Do not guess, invent, or substitute any other name.

Fixed category ids to choose from (pick the closest, default to "other" if unsure):
{category_lines}

If a field is unreadable, use null (or "" for receipt_number)."""

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(response_mime_type='application/json'),
        )
        return json.loads(response.text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ExtractionError('לא ניתן היה לפענח את תשובת המודל') from exc
    except Exception as exc:  # noqa: BLE001 — surface any SDK/network failure uniformly
        raise ExtractionError(f'שגיאה בפנייה למודל: {exc}') from exc


def _coerce_response(raw: dict) -> dict:
    amount = raw.get('amount')
    try:
        amount = str(Decimal(str(amount))) if amount is not None else None
    except (InvalidOperation, TypeError, ValueError):
        amount = None

    category = raw.get('category')
    if category not in _CATEGORY_VALUES:
        category = Receipt.CATEGORY_OTHER

    receipt_date = raw.get('receipt_date')
    if not isinstance(receipt_date, str):
        receipt_date = None

    return {
        'client_name_guess': raw.get('client_name_guess') or None,
        'amount': amount,
        'receipt_number': raw.get('receipt_number') or '',
        'receipt_date': receipt_date,
        'category': category,
    }


def _match_client(candidate: str | None):
    """Fuzzy-matches candidate against active clients.

    Returns (client_id, score, suggestion): client_id/score are only set
    when the match clears MATCH_CONFIDENCE_THRESHOLD (safe to auto-fill).
    suggestion is the best candidate regardless of threshold — a "closest
    match" hint the worker can confirm with one click even when it's not
    confident enough to auto-select.
    """
    if not candidate:
        return None, None, None

    names = dict(Client.objects.filter(is_active=True).values_list('name', 'id'))
    if not names:
        return None, None, None

    best = process.extractOne(candidate, names.keys(), scorer=fuzz.WRatio)
    if not best:
        return None, None, None
    name, score, _ = best
    suggestion = {'client_id': names[name], 'name': name, 'score': score}
    if score < MATCH_CONFIDENCE_THRESHOLD:
        return None, None, suggestion
    return names[name], score, suggestion
