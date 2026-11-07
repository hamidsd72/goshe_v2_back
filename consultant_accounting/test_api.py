from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Message, Transaction
from call.models import CallLog


class ConsultantRevenueTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='consultant-test')
        self.admin = get_user_model().objects.create_user(
            username='admin-test', is_superuser=True)
        self.client = APIClient()
        self.url = '/consultants/{}/revenue/'.format(self.user.pk)

    def test_permissions_for_anonymous_regular_staff_and_superuser(self):
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
        for staff in (False, True):
            self.user.is_staff = staff
            self.client.force_authenticate(self.user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_totals_are_scoped_to_user_and_deduct_w_once(self):
        CallLog.objects.create(authorId=self.user, call_amount=1000000)
        CallLog.objects.create(authorId=self.admin, call_amount=999999)
        Message.objects.create(sendTo=self.user, amount=200000)
        Message.objects.create(sendTo=self.admin, amount=999999)
        Transaction.objects.create(userId=self.user, type='w', amount=30000)
        Transaction.objects.create(userId=self.user, type='w', amount=500000)
        Transaction.objects.create(userId=self.user, type='s', amount=900000)
        Transaction.objects.create(userId=self.admin, type='w', amount=999999)
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['balance'], -380000)
        self.assertEqual(response.data['deductions'], 530000)
        self.assertEqual(Transaction.objects.count(), 4)

    def test_missing_user_returns_404(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/consultants/999999/revenue/').status_code, 404)


class ConsultantReportTests(TestCase):
    def setUp(self):
        from api.models import Author
        self.admin = get_user_model().objects.create_user(username='report-admin', is_superuser=True)
        self.user = get_user_model().objects.create_user(username='09120000000', first_name='Test', last_name='Consultant')
        Author.objects.create(userId=self.user, shaba='IR123')
        Author.objects.create(userId=self.user, shaba='IR456')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_report_filters_and_duplicate_author_accounts(self):
        response = self.client.get('/report/', {'search': 'Consultant'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        row = response.data['results'][0]
        self.assertTrue(row['iban_ambiguous'])
        self.assertEqual(row['iban'], '')
        self.assertIsNone(row['tax'])
        self.assertEqual(self.client.get('/report/', {'search': 'missing'}).data['results'], [])

    def test_invalid_filters_and_permissions(self):
        for params in ({'start': 'invalid'}, {'consultant': '-1'},
                       {'start': '2026-11-07', 'end': '2026-11-01'}):
            self.assertEqual(self.client.get('/report/', params).status_code, 400)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/report/').status_code, 403)

    def test_period_carries_opening_balance_and_includes_end_day(self):
        from datetime import date
        from .reports import date_boundary
        call = CallLog.objects.create(authorId=self.user, call_amount=1000000)
        CallLog.objects.filter(pk=call.pk).update(created_at=date_boundary(date(2026, 10, 1)))
        payment = Transaction.objects.create(userId=self.user, type='w', amount=10000)
        Transaction.objects.filter(pk=payment.pk).update(created_at=date_boundary(date(2026, 10, 2)))
        message = Message.objects.create(sendTo=self.user, amount=20000)
        Message.objects.filter(pk=message.pk).update(created_at=date_boundary(date(2026, 11, 7)))
        payment = Transaction.objects.create(userId=self.user, type='w', amount=15000)
        Transaction.objects.filter(pk=payment.pk).update(created_at=date_boundary(date(2026, 11, 7)))
        response = self.client.get('/report/', {'start': '2026-11-01', 'end': '2026-11-07'})
        row = response.data['results'][0]
        self.assertEqual(row['opening_balance'], 40000)
        self.assertEqual(row['gross_earnings'], 10000)
        self.assertEqual(row['paid_in_period'], 15000)
        self.assertEqual(row['balance'], 35000)
        self.assertEqual(row['settlement_status'], 'partial')


class BankExportTests(TestCase):
    def setUp(self):
        from api.models import Author
        self.admin = get_user_model().objects.create_user(username='bank-admin', is_superuser=True)
        self.user = get_user_model().objects.create_user(username='bank-user', first_name='زهرا', last_name='حسین پور')
        self.author = Author.objects.create(userId=self.user, shaba='IR760140040004110176408212')
        CallLog.objects.create(authorId=self.user, call_amount=40000000)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def preview(self):
        return self.client.post('/bank/preview/', {'selected': [self.user.pk]}, format='json')

    def download(self, token):
        return self.client.post('/bank/download/', {'token': token}, format='json')

    def test_export_is_read_only_and_matches_preview(self):
        preview = self.preview()
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data['total_rial'], 20000000)
        response = self.download(preview.data['token'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'IR760140040004110176408212,20000000,زهرا,حسین پور,حقوق,\r\n'.encode('utf-8'))
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(self.download(preview.data['token']).status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_changed_balance_or_iban_requires_new_preview(self):
        token = self.preview().data['token']
        Transaction.objects.create(userId=self.user, type='w', amount=100)
        self.assertEqual(self.download(token).status_code, 409)
        token = self.preview().data['token']
        self.author.shaba = ''
        self.author.save()
        self.assertEqual(self.download(token).status_code, 409)

    def test_invalid_selection_and_iban_are_reported(self):
        self.author.shaba = 'invalid'
        self.author.save()
        preview = self.preview().data
        self.assertEqual(preview['rows'], [])
        self.assertEqual(len(preview['excluded']), 1)
        self.assertIsNone(preview['token'])
        self.assertEqual(self.client.post('/bank/preview/', {'selected': []}, format='json').status_code, 400)

    def test_permissions_and_tampered_or_expired_token(self):
        from unittest.mock import patch
        from django.core import signing
        token = self.preview().data['token']
        self.assertEqual(self.download(token + 'x').status_code, 400)
        with patch('django.core.signing.time.time', return_value=0):
            expired = signing.dumps({'admin': self.admin.pk, 'rows': []}, salt='consultant-bank-export')
        self.assertEqual(self.download(expired).status_code, 400)
        other = get_user_model().objects.create_user(username='bank-admin-other', is_superuser=True)
        self.client.force_authenticate(other)
        self.assertEqual(self.download(token).status_code, 403)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.preview().status_code, 403)
        self.assertEqual(self.download(token).status_code, 403)


class DetailedReportTests(TestCase):
    def setUp(self):
        from api.models import Author
        self.admin = get_user_model().objects.create_user(username='export-admin', is_superuser=True)
        self.user = get_user_model().objects.create_user(username='09120000001', first_name='زهرا', last_name='حسین پور')
        Author.objects.create(userId=self.user)
        CallLog.objects.create(authorId=self.user, call_amount=1000000)
        Transaction.objects.create(userId=self.user, type='w', amount=10000)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_all_report_types_and_legacy_labels(self):
        for kind in ('performance', 'deductions', 'payments', 'balances', 'settlements'):
            response = self.client.get('/reports/', {'report_type': kind})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['currency'], 'toman')
            self.assertEqual(response.data['tax_status'], 'pending')
        payments = self.client.get('/reports/', {'report_type': 'payments'}).data['rows']
        self.assertEqual(payments[0]['event_kind'], 'کسورات قدیمی w')
        self.assertEqual(payments[0]['bank_reference'], '')
        self.assertEqual(self.client.get('/reports/', {'report_type': 'settlements'}).data['rows'], [])

    def test_exports_are_read_only_and_access_is_admin_only(self):
        for kind, mime in [('xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'), ('print', 'application/json')]:
            response = self.client.get('/reports/export/', {'file_type': kind})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Type'].startswith(mime))
            self.assertEqual(response['Cache-Control'], 'no-store')
            if kind == 'print':
                self.assertIn('<!doctype html>', response.data['html'])
        self.assertEqual(Transaction.objects.count(), 1)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/reports/').status_code, 403)
        self.assertEqual(self.client.get('/reports/export/', {'file_type': 'xlsx'}).status_code, 403)

    def test_filters_apply_to_report_and_events(self):
        for kind in ('performance', 'payments'):
            response = self.client.get('/reports/', {'report_type': kind, 'search': 'missing'})
            self.assertEqual(response.data['rows'], [])
            response = self.client.get('/reports/', {'report_type': kind, 'consultant': self.user.pk})
            self.assertEqual(len(response.data['rows']), 1)

    def test_invalid_report_and_date_inputs_return_400(self):
        for params in ({'report_type': 'unknown'}, {'end': '9999-12-31'},
                       {'start': '2026-11-07', 'end': '2026-11-01'}):
            self.assertEqual(self.client.get('/reports/', params).status_code, 400)
        self.assertEqual(self.client.get('/reports/export/', {'file_type': 'pdf'}).status_code, 400)
