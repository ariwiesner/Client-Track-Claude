import datetime
import logging

import requests
from django.conf import settings
from django.utils import timezone

from core.models import Client

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30

# Fields Rivhit's Customer.List/Customer.Get return (per the official
# "Rivhit Online REST Service API" doc, section 1.1/1.5) that are worth
# showing on a client's page. 'balance' isn't in that list — it comes from
# a separate Customer.Balance call — and gets merged in alongside these.
CUSTOMER_FIELDS = [
    'last_name', 'first_name', 'street', 'city', 'zipcode', 'phone', 'fax',
    'email', 'id_number', 'vat_number', 'customer_type', 'price_list_id',
    'agent_id', 'discount_percent', 'acc_ref', 'comments',
]

# Credit notes (חשבונית מס זיכוי) have no dedicated flag in
# Document.TypeList — is_accounting is true for them same as real invoices
# — so they're told apart by name, same as a human would in Rivhit's UI.
CREDIT_NOTE_KEYWORD = 'זיכוי'


class RivhitError(Exception):
    pass


def _call(method, payload):
    if not settings.RIVHIT_API_TOKEN:
        raise RivhitError('RIVHIT_API_TOKEN is not configured')

    url = settings.RIVHIT_API_BASE_URL.rstrip('/') + '/' + method
    body = {'api_token': settings.RIVHIT_API_TOKEN, **payload}
    response = requests.post(url, json=body, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    result = response.json()

    if result.get('error_code'):
        raise RivhitError(
            f"Rivhit {method} failed ({result.get('error_code')}): "
            f"{result.get('client_message') or result.get('debug_message')}"
        )
    return result.get('data', {})


def _format_date(date):
    # Rivhit's date request params use an unseparated DDMMYYYY string, not
    # ISO-8601 — see e.g. Document.List's date_from/date_to.
    return f'{date.day:02d}{date.month:02d}{date.year:04d}'


def _normalize_name(name):
    return ' '.join((name or '').split()).strip().casefold()


def fetch_customers():
    """{str(customer_id): {field: value}} for every customer in the Rivhit
    account (Customer.List with no filter returns all of them).
    """
    data = _call('Customer.List', {})
    return {
        str(c['customer_id']): {field: c.get(field) for field in CUSTOMER_FIELDS}
        for c in data.get('customer_list', [])
    }


def match_customers_by_name(customers):
    """{normalized_name: customer_id}. A client's business name usually
    lives alone in Rivhit's last_name field ("שם משפחה / עסק" — last
    name/business), so each customer is indexed under that, and also under
    first_name+last_name combined in case it's an individual. A name
    matched by more than one customer is dropped rather than guessed —
    attaching the wrong customer would silently show one client another's
    revenue.
    """
    index = {}
    ambiguous = set()
    for customer_id, customer in customers.items():
        last = customer.get('last_name') or ''
        first = customer.get('first_name') or ''
        candidates = {_normalize_name(last), _normalize_name(f'{first} {last}')}
        for name in candidates:
            if not name:
                continue
            if name in index and index[name] != customer_id:
                ambiguous.add(name)
            else:
                index[name] = customer_id
    for name in ambiguous:
        index.pop(name, None)
    return index


def fetch_customer_balance(customer_id):
    data = _call('Customer.Balance', {'customer_id': int(customer_id)})
    return data.get('balance')


def fetch_invoice_document_types():
    """{document_type: document_name} for every document type that counts
    toward "money invoiced" — accounting documents (Document.TypeList's
    is_accounting) excluding credit notes. Delivery notes, quotes, and
    orders are is_accounting=false and drop out on their own.
    """
    data = _call('Document.TypeList', {})
    return {
        t['document_type']: t['document_name']
        for t in data.get('document_type_list', [])
        if t.get('is_accounting') and CREDIT_NOTE_KEYWORD not in (t.get('document_name') or '')
    }


def fetch_invoice_totals_by_customer(from_date, to_date):
    """{str(customer_id): total} of invoice documents (see
    fetch_invoice_document_types) issued between from_date and to_date
    (inclusive, datetime.date objects).
    """
    invoice_types = fetch_invoice_document_types()
    if not invoice_types:
        return {}

    data = _call('Document.List', {
        'date_from': _format_date(from_date),
        'date_to': _format_date(to_date),
    })

    totals = {}
    for doc in data.get('document_list', []):
        if doc.get('document_type') not in invoice_types:
            continue
        customer_id = str(doc.get('customer_id'))
        totals[customer_id] = totals.get(customer_id, 0) + doc.get('amount', 0)
    return totals


def sync_clients(year=None):
    """Match every Client to a Rivhit customer — by its already-stored
    rivhit_customer_id if one was set (manually, or by a previous sync) and
    it still exists in Rivhit, otherwise by matching names — then cache
    that customer's profile, balance, and this year's invoice total.
    Once a client is matched its id sticks, so later renames on either side
    don't cause it to hop between customers.
    Returns (matched_count, [name for every client that couldn't be matched]).
    """
    year = year or timezone.now().year
    from_date = datetime.date(year, 1, 1)
    to_date = datetime.date(year, 12, 31)

    customers = fetch_customers()
    name_index = match_customers_by_name(customers)
    totals = fetch_invoice_totals_by_customer(from_date, to_date)

    matched = 0
    unmatched = []
    now = timezone.now()
    for client in Client.objects.all():
        customer_id = client.rivhit_customer_id if client.rivhit_customer_id in customers else None
        if not customer_id:
            customer_id = name_index.get(_normalize_name(client.name))
        if not customer_id:
            unmatched.append(client.name)
            continue

        customer_data = dict(customers.get(customer_id, {}))
        try:
            customer_data['balance'] = fetch_customer_balance(customer_id)
        except RivhitError:
            logger.exception('Failed to fetch Rivhit balance for client %s', client.pk)

        Client.objects.filter(pk=client.pk).update(
            rivhit_customer_id=customer_id,
            rivhit_customer_data=customer_data,
            rivhit_total_invoiced=totals.get(customer_id, 0),
            rivhit_synced_at=now,
        )
        matched += 1
    return matched, unmatched
