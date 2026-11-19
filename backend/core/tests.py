import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from core.models import Client
from core.services import rivhit


def _response(data=None, error_code=0, client_message=None):
    mock = Mock()
    mock.raise_for_status = Mock()
    mock.json.return_value = {
        'error_code': error_code,
        'client_message': client_message,
        'data': data or {},
    }
    return mock


DOCUMENT_TYPE_LIST = {
    'document_type_list': [
        {'document_type': 1, 'document_name': 'חשבונית מס', 'is_invoice_receipt': False, 'is_accounting': True},
        {'document_type': 2, 'document_name': 'חשבונית מס קבלה', 'is_invoice_receipt': True, 'is_accounting': True},
        {'document_type': 3, 'document_name': 'חשבונית מס זיכוי', 'is_invoice_receipt': False, 'is_accounting': True},
        {'document_type': 4, 'document_name': 'תעודת משלוח', 'is_invoice_receipt': False, 'is_accounting': False},
    ],
}


@override_settings(RIVHIT_API_TOKEN='test-token')
class RivhitServiceTests(TestCase):
    def test_format_date_uses_ddmmyyyy_with_no_separators(self):
        self.assertEqual(rivhit._format_date(datetime.date(2026, 1, 5)), '05012026')

    @patch('core.services.rivhit.requests.post')
    def test_fetch_customers_keyed_by_id(self, mock_post):
        mock_post.return_value = _response({
            'customer_list': [
                {'customer_id': 101, 'last_name': 'Cohen', 'first_name': 'Dan', 'city': 'Tel Aviv', 'extra_field': 'ignored'},
            ],
        })

        customers = rivhit.fetch_customers()

        self.assertEqual(customers['101']['last_name'], 'Cohen')
        self.assertEqual(customers['101']['city'], 'Tel Aviv')
        self.assertNotIn('extra_field', customers['101'])

    @patch('core.services.rivhit.requests.post')
    def test_fetch_invoice_document_types_excludes_credit_notes_and_non_accounting(self, mock_post):
        mock_post.return_value = _response(DOCUMENT_TYPE_LIST)

        types = rivhit.fetch_invoice_document_types()

        self.assertEqual(set(types.keys()), {1, 2})

    @patch('core.services.rivhit.requests.post')
    def test_fetch_invoice_totals_only_counts_invoice_types(self, mock_post):
        def side_effect(url, json, timeout):
            method = url.rsplit('/', 1)[-1]
            if method == 'Document.TypeList':
                return _response(DOCUMENT_TYPE_LIST)
            return _response({
                'document_list': [
                    {'document_type': 1, 'amount': 100, 'customer_id': 1},
                    {'document_type': 2, 'amount': 50, 'customer_id': 1},
                    {'document_type': 3, 'amount': 30, 'customer_id': 1},
                    {'document_type': 4, 'amount': 999, 'customer_id': 1},
                    {'document_type': 1, 'amount': 200, 'customer_id': 2},
                ],
            })
        mock_post.side_effect = side_effect

        totals = rivhit.fetch_invoice_totals_by_customer(
            datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)
        )

        self.assertEqual(totals, {'1': 150, '2': 200})

    @patch('core.services.rivhit.requests.post')
    def test_call_raises_on_error_code(self, mock_post):
        mock_post.return_value = _response(error_code=3, client_message='Invalid token')

        with self.assertRaises(rivhit.RivhitError):
            rivhit.fetch_customers()

    def test_match_customers_by_name_indexes_business_name_and_full_name(self):
        customers = {
            '1': {'last_name': 'חנות הפרחים', 'first_name': ''},
            '2': {'last_name': 'כהן', 'first_name': 'דני'},
        }

        index = rivhit.match_customers_by_name(customers)

        self.assertEqual(index['חנות הפרחים'], '1')
        self.assertEqual(index['דני כהן'], '2')
        self.assertEqual(index['כהן'], '2')

    def test_match_customers_by_name_drops_ambiguous_matches(self):
        customers = {
            '1': {'last_name': 'כהן', 'first_name': ''},
            '2': {'last_name': 'כהן', 'first_name': ''},
        }

        index = rivhit.match_customers_by_name(customers)

        self.assertNotIn('כהן', index)

    @patch('core.services.rivhit.requests.post')
    def test_sync_clients_matches_by_name_when_no_id_is_set(self, mock_post):
        client = Client.objects.create(name='חנות הפרחים', hourly_rate=100)

        def side_effect(url, json, timeout):
            method = url.rsplit('/', 1)[-1]
            if method == 'Customer.List':
                return _response({
                    'customer_list': [
                        {'customer_id': 42, 'last_name': 'חנות הפרחים', 'first_name': '', 'city': 'Haifa'},
                    ],
                })
            if method == 'Document.TypeList':
                return _response(DOCUMENT_TYPE_LIST)
            if method == 'Document.List':
                return _response({
                    'document_list': [{'document_type': 1, 'amount': 500, 'customer_id': 42}],
                })
            if method == 'Customer.Balance':
                return _response({'balance': 75.5})
            raise AssertionError(f'unexpected method {method}')
        mock_post.side_effect = side_effect

        matched, unmatched = rivhit.sync_clients(year=2026)

        self.assertEqual(matched, 1)
        self.assertEqual(unmatched, [])
        client.refresh_from_db()
        self.assertEqual(client.rivhit_customer_id, '42')
        self.assertEqual(client.rivhit_total_invoiced, Decimal('500'))
        self.assertEqual(client.rivhit_customer_data['city'], 'Haifa')
        self.assertEqual(client.rivhit_customer_data['balance'], 75.5)
        self.assertIsNotNone(client.rivhit_synced_at)

    @patch('core.services.rivhit.requests.post')
    def test_sync_clients_keeps_existing_id_even_if_name_no_longer_matches(self, mock_post):
        # Client was renamed on our side (or matched manually) after the
        # original name-match — the stored id should still win over a
        # fresh (now-failing) name lookup.
        client = Client.objects.create(name='שם חדש שלא תואם', hourly_rate=100, rivhit_customer_id='42')

        def side_effect(url, json, timeout):
            method = url.rsplit('/', 1)[-1]
            if method == 'Customer.List':
                return _response({
                    'customer_list': [{'customer_id': 42, 'last_name': 'שם ישן בריווחית', 'first_name': ''}],
                })
            if method == 'Document.TypeList':
                return _response(DOCUMENT_TYPE_LIST)
            if method == 'Document.List':
                return _response({'document_list': []})
            if method == 'Customer.Balance':
                return _response({'balance': 0})
            raise AssertionError(f'unexpected method {method}')
        mock_post.side_effect = side_effect

        matched, unmatched = rivhit.sync_clients(year=2026)

        self.assertEqual(matched, 1)
        self.assertEqual(unmatched, [])
        client.refresh_from_db()
        self.assertEqual(client.rivhit_customer_id, '42')

    @patch('core.services.rivhit.requests.post')
    def test_sync_clients_reports_clients_with_no_match(self, mock_post):
        Client.objects.create(name='לקוח שלא קיים בריווחית', hourly_rate=100)

        def side_effect(url, json, timeout):
            method = url.rsplit('/', 1)[-1]
            if method == 'Customer.List':
                return _response({'customer_list': []})
            if method == 'Document.TypeList':
                return _response(DOCUMENT_TYPE_LIST)
            if method == 'Document.List':
                return _response({'document_list': []})
            raise AssertionError(f'unexpected method {method}')
        mock_post.side_effect = side_effect

        matched, unmatched = rivhit.sync_clients(year=2026)

        self.assertEqual(matched, 0)
        self.assertEqual(unmatched, ['לקוח שלא קיים בריווחית'])
