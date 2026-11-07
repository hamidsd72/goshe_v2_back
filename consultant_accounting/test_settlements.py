from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Author, Transaction
from call.models import CallLog
from .models import SettlementBatch, SettlementPayment
from .services import get_consultant_revenue


class SettlementTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='settlement-admin', is_superuser=True)
        self.user = get_user_model().objects.create_user(username='settlement-user', first_name='زهرا', last_name='حسین پور')
        Author.objects.create(userId=self.user, shaba='IR760140040004110176408212')
        CallLog.objects.create(authorId=self.user, call_amount=2000000)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.paid_at = (timezone.now() - timedelta(minutes=1)).isoformat()

    def preview(self, amount=40000):
        return self.client.post('/settlements/preview/', {
            'payments': [{'user_id': self.user.pk, 'amount_toman': amount}]}, format='json')

    def payload(self, token):
        return {'token': token, 'bank_reference': 'BANK-001', 'paid_at': self.paid_at,
                'bank_transfer_completed': True}

    def confirm(self, data):
        return self.client.post('/settlements/confirm/', data, format='json')

    def test_partial_payment_and_exact_retry(self):
        preview = self.preview()
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)
        data = self.payload(preview.data['token'])
        response = self.confirm(data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.confirm(data).data, response.data)
        self.assertEqual(SettlementBatch.objects.count(), 1)
        self.assertEqual(SettlementPayment.objects.count(), 1)
        self.assertEqual(Transaction.objects.get().amount, 40000)
        self.assertEqual(get_consultant_revenue(self.user.pk)['balance'], 60000)
        batch = SettlementBatch.objects.get()
        self.assertEqual(batch.confirmed_by, self.admin)
        self.assertAlmostEqual((batch.paid_at - timezone.now()).total_seconds(), -60, delta=10)

    def test_two_previews_cannot_overdraw_account(self):
        first = self.payload(self.preview(70000).data['token'])
        second = self.payload(self.preview(70000).data['token'])
        second['bank_reference'] = 'BANK-002'
        self.assertEqual(self.confirm(first).status_code, 200)
        self.assertEqual(self.confirm(second).status_code, 409)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_reused_reference_or_changed_retry_cannot_create_document(self):
        data = self.payload(self.preview(20000).data['token'])
        self.assertEqual(self.confirm(data).status_code, 200)
        data['bank_reference'] = 'BANK-CHANGED'
        self.assertEqual(self.confirm(data).status_code, 409)
        data = self.payload(self.preview(20000).data['token'])
        self.assertEqual(self.confirm(data).status_code, 409)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_validation_and_permission_checks(self):
        self.assertEqual(self.preview(100001).status_code, 400)
        token = self.preview().data['token']
        data = self.payload(token)
        data['bank_transfer_completed'] = False
        self.assertEqual(self.confirm(data).status_code, 400)
        data = self.payload(token)
        data['paid_at'] = (timezone.now() + timedelta(days=1)).isoformat()
        self.assertEqual(self.confirm(data).status_code, 400)
        self.assertEqual(self.confirm(self.payload(token + 'x')).status_code, 400)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.preview().status_code, 403)
        self.assertEqual(self.confirm(self.payload(token)).status_code, 403)
        self.assertEqual(self.client.get('/settlements/').status_code, 403)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_document_failure_rolls_back_legacy_transaction(self):
        data = self.payload(self.preview().data['token'])
        with patch('consultant_accounting.settlements.SettlementPayment.objects.create', side_effect=IntegrityError):
            self.assertEqual(self.confirm(data).status_code, 409)
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(SettlementBatch.objects.count(), 0)

    def test_immutable_documents_and_linked_transaction(self):
        self.confirm(self.payload(self.preview().data['token']))
        document = SettlementPayment.objects.get()
        for operation in (document.delete, document.save,
                          lambda: SettlementPayment.objects.all().update(amount_toman=1),
                          lambda: SettlementPayment.objects.all().delete(),
                          document.transaction.save):
            with self.assertRaises(ModelValidationError):
                operation()
        self.assertEqual(document.transaction.amount, 40000)

    def test_reversal_is_separate_and_idempotent(self):
        self.confirm(self.payload(self.preview().data['token']))
        original = SettlementPayment.objects.get()
        payload = {'request_id': str(uuid4()), 'bank_reference': 'REV-001',
                   'paid_at': self.paid_at, 'reason': 'ثبت اشتباه واریز', 'correction_confirmed': True}
        url = '/settlements/{}/reverse/'.format(original.pk)
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(url, payload, format='json').data, response.data)
        self.assertEqual(SettlementPayment.objects.count(), 2)
        self.assertEqual(get_consultant_revenue(self.user.pk)['balance'], 100000)
        self.assertEqual(Transaction.objects.filter(amount=-40000).count(), 1)
        payload['request_id'] = str(uuid4())
        payload['bank_reference'] = 'REV-002'
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 409)
        original.refresh_from_db()
        self.assertEqual(original.amount_toman, 40000)

    def test_report_uses_actual_paid_date(self):
        data = self.payload(self.preview().data['token'])
        actual = timezone.now() - timedelta(days=5)
        data['paid_at'] = actual.isoformat()
        self.assertEqual(self.confirm(data).status_code, 200)
        from .reports import build_report
        from .reports import TEHRAN_TIMEZONE
        day = actual.astimezone(TEHRAN_TIMEZONE).date()
        report = build_report(start=day, end=day)
        self.assertEqual(report['results'][0]['paid_in_period'], 40000)


class ConcurrentSettlementTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_overlapping_settlements_cannot_pay_same_balance_twice(self):
        from .settlements import preview_settlement, confirm_settlement, SettlementConflict
        admin = get_user_model().objects.create_user(username='concurrent-admin', is_superuser=True)
        user = get_user_model().objects.create_user(username='concurrent-user', first_name='زهرا', last_name='حسین پور')
        Author.objects.create(userId=user, shaba='IR760140040004110176408212')
        CallLog.objects.create(authorId=user, call_amount=2000000)
        tokens = [preview_settlement(admin, [{'user_id': user.pk, 'amount_toman': 70000}])['token']
                  for _ in range(2)]
        barrier = Barrier(2)
        paid_at = timezone.now() - timedelta(minutes=1)

        def confirm(index):
            connections.close_all()
            try:
                worker_admin = get_user_model().objects.get(pk=admin.pk)
                barrier.wait(timeout=10)
                try:
                    confirm_settlement(worker_admin, tokens[index], 'CONCURRENT-{}'.format(index), paid_at)
                    return 'paid'
                except SettlementConflict:
                    return 'conflict'
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(confirm, range(2)))
        self.assertCountEqual(results, ['paid', 'conflict'])
        self.assertEqual(SettlementPayment.objects.count(), 1)
        self.assertEqual(get_consultant_revenue(user.pk)['balance'], 30000)

    def race(self, callbacks):
        barrier = Barrier(len(callbacks))

        def run(callback):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return callback()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(callbacks)) as pool:
            return list(pool.map(run, callbacks))

    def account(self):
        admin = get_user_model().objects.create_user(username='race-admin', is_superuser=True)
        user = get_user_model().objects.create_user(username='race-user', first_name='زهرا', last_name='حسین پور')
        Author.objects.create(userId=user, shaba='IR760140040004110176408212')
        CallLog.objects.create(authorId=user, call_amount=2000000)
        return admin, user

    @skipUnlessDBFeature('has_select_for_update')
    def test_same_request_concurrently_returns_one_document(self):
        from .settlements import preview_settlement, confirm_settlement
        admin, user = self.account()
        token = preview_settlement(admin, [{'user_id': user.pk, 'amount_toman': 40000}])['token']
        paid_at = timezone.now() - timedelta(minutes=1)

        def confirm():
            return confirm_settlement(admin, token, 'RACE-SAME', paid_at)

        results = self.race([confirm, confirm])
        self.assertEqual(results[0], results[1])
        self.assertEqual(SettlementPayment.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(get_consultant_revenue(user.pk)['balance'], 60000)

    @skipUnlessDBFeature('has_select_for_update')
    def test_same_reversal_concurrently_restores_balance_once(self):
        from .settlements import preview_settlement, confirm_settlement, reverse_payment
        admin, user = self.account()
        token = preview_settlement(admin, [{'user_id': user.pk, 'amount_toman': 40000}])['token']
        paid_at = timezone.now() - timedelta(minutes=1)
        batch = confirm_settlement(admin, token, 'RACE-ORIGINAL', paid_at)
        payment_id = batch['payments'][0]['id']
        request_id = uuid4()

        def reverse():
            return reverse_payment(admin, payment_id, request_id, 'RACE-REVERSE', paid_at, 'اصلاح تست')

        results = self.race([reverse, reverse])
        self.assertEqual(results[0], results[1])
        self.assertEqual(SettlementPayment.objects.count(), 2)
        self.assertEqual(get_consultant_revenue(user.pk)['balance'], 100000)
