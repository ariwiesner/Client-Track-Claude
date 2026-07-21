import io
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
    original_bytes = image_file.read()
    raw = _call_gemini(original_bytes, mime_type)
    all_names = list(raw.get('possible_names') or [])

    if _best_score(all_names) < MATCH_CONFIDENCE_THRESHOLD:
        # A sideways/rotated photo: the model reliably keeps reading a big,
        # prominent letterhead name sideways just fine, but can silently
        # miss a smaller customer-name field entirely — confirmed by
        # testing the same real receipt both ways (a rotation that finds
        # only the seller's name looks identical to "found a name" unless
        # we actually check whether it matches a real client). So keep
        # trying other orientations — accumulating candidate names across
        # all of them rather than stopping at the first non-empty list —
        # until one clears the confidence threshold or we run out of
        # rotations to try. Asking the model to self-report its own
        # rotation was unreliable (tested separately), hence brute-forcing
        # it instead. Only the numeric fields from the very first, already-
        # reliable attempt are kept — rotating doesn't improve those and
        # risks a worse read.
        for angle in (90, 180, 270):
            retry_raw = _call_gemini(_rotate_image_bytes(original_bytes, angle), 'image/png')
            all_names.extend(retry_raw.get('possible_names') or [])
            if _best_score(all_names) >= MATCH_CONFIDENCE_THRESHOLD:
                break

    coerced = _coerce_response(raw)
    coerced.pop('possible_names', None)

    client_id, score, suggestion = _match_client(all_names)
    coerced['client_id'] = client_id
    coerced['client_match_score'] = score
    coerced['client_suggestion'] = suggestion
    return coerced


def _best_score(candidates: list[str]) -> float:
    _, _, suggestion = _match_client(candidates)
    return suggestion['score'] if suggestion else 0


def _rotate_image_bytes(image_bytes: bytes, angle: int) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    rotated = img.rotate(angle, expand=True)
    out = io.BytesIO()
    rotated.convert('RGB').save(out, format='PNG')
    return out.getvalue()


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
    #
    # Also deliberately NOT asking the model to decide *which* printed name
    # is "the client" (vs. the seller) — that depends on business context
    # it doesn't have. A receipt from a client who's a self-employed
    # tradesperson may have that client's own name as the prominent
    # top-of-page letterhead, indistinguishable in principle from a normal
    # seller letterhead. So instead: surface every plausible name on the
    # page as a candidate, and let server-side fuzzy-matching against the
    # real client list (the actual source of truth for "who is a client")
    # decide which one, if any, is real.
    prompt = f"""You are reading a business receipt (קבלה) photo for an Israeli bookkeeping office.
The photo may be printed, typed, or HANDWRITTEN (including cursive) — read
handwritten text just as carefully as printed text; do not skip a field or
give up just because it's handwritten or the handwriting is messy.

Extract these fields and return STRICT JSON only, no markdown, no commentary:
{{
  "possible_names": array of strings (can be empty),
  "amount": number or null,
  "receipt_number": string or "",
  "receipt_date": "YYYY-MM-DD" or null,
  "category": one of the category ids below
}}

possible_names: list EVERY distinct person or business name printed or
handwritten anywhere on the receipt — a prominent name/header at the top,
a store/seller letterhead, a customer/recipient field, a handwritten name
near a signature, anywhere. Do not try to judge which one (if any) is "the
customer" versus "the seller" — just list every name-like string you see,
copied exactly as written. Include a name even if it's the only/most
prominent text on the page. Empty list only if truly no name appears
anywhere.

receipt_date: receipts are often handwritten with short date formats like
"6/5/26" or "27.4.26" — read these carefully digit by digit even when
handwritten, and convert to YYYY-MM-DD (a 2-digit year like "26" means
2026). Israeli date order is DD/MM/YY, not MM/DD/YY. Only use null if no
date is legible anywhere on the receipt at all.

amount: handwritten Israeli receipts/invoices often show shekels and
agorot (cents) as two separate stacked numbers or two columns (e.g. a
subtotal row, a VAT/מע"מ row, and a total row), not as one number with a
decimal point. If you see a total made of separate shekel and agorot
parts, combine them as a proper decimal (e.g. shekel part "531" + agorot
part "00" is 531.00, NOT 53100). A typical receipt amount is tens to a
few thousand ש"ח — if your reading implies tens of thousands or more,
re-check whether you accidentally concatenated separate rows/columns
into one integer instead of treating the last two digits as agorot.

Fixed category ids to choose from (pick the closest, default to "other" if unsure):
{category_lines}

If a field is genuinely unreadable, use null (or "" for receipt_number,
or [] for possible_names) — but make a real effort on every field first,
especially handwritten ones, before giving up."""

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

    possible_names = raw.get('possible_names')
    if not isinstance(possible_names, list):
        possible_names = []

    return {
        'possible_names': [n for n in possible_names if isinstance(n, str) and n.strip()],
        'amount': amount,
        'receipt_number': raw.get('receipt_number') or '',
        'receipt_date': receipt_date,
        'category': category,
    }


def _match_client(candidates: list[str]):
    """Fuzzy-matches each candidate name against active clients and keeps
    the best-scoring one overall — the model surfaces every name it sees
    on the page (seller letterhead, customer field, handwritten note, all
    of it) without judging which is "the client", so this is what actually
    decides that, against the real client list.

    Returns (client_id, score, suggestion): client_id/score are only set
    when the best match clears MATCH_CONFIDENCE_THRESHOLD (safe to
    auto-fill). suggestion is the best candidate regardless of threshold —
    a "closest match" hint the worker can confirm with one click even when
    it's not confident enough to auto-select.
    """
    if not candidates:
        return None, None, None

    names = dict(Client.objects.filter(is_active=True).values_list('name', 'id'))
    if not names:
        return None, None, None

    # token_sort_ratio, not WRatio: WRatio's partial-match blending scores
    # two completely unrelated business names as ~85% just for sharing a
    # generic suffix like 'בע"מ' — confirmed directly (ratio/token_sort_ratio
    # both said ~35% for the same pair). That's fine when there's only ever
    # one real candidate name to check (the old single-name design), but
    # now every name on the page (including the seller's, unrelated to any
    # client) gets checked, so a scorer that doesn't inflate shared-suffix
    # overlap matters a lot more here.
    best_overall = None
    for candidate in candidates:
        match = process.extractOne(candidate, names.keys(), scorer=fuzz.token_sort_ratio)
        if match and (best_overall is None or match[1] > best_overall[1]):
            best_overall = match

    if not best_overall:
        return None, None, None
    name, score, _ = best_overall
    suggestion = {'client_id': names[name], 'name': name, 'score': score}
    if score < MATCH_CONFIDENCE_THRESHOLD:
        return None, None, suggestion
    return names[name], score, suggestion
