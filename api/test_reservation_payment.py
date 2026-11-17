"""Full-price top-up followed by booking, using mocked gateway connections only."""
from uuid import uuid4
from unittest.mock import patch
from django.test import TestCase, override_settings
from background_task.models import Task
from .models import ReservationCredit, Transaction
from . import test_reservations as fixtures


@override_settings(ROOT_URLCONF='api.reservation_regression_test_urls')
class ReservationPaymentTests(TestCase):
    setUp = fixtures.ReservationTests.setUp
    post = fixtures.ReservationTests.post
    balance = fixtures.ReservationTests.balance

    def prepare_payment(self):
        self.user.amount = 100000  # 10,000 toman already in the wallet
        self.user.save()
        self.author.call_price = 5000  # 10 minutes costs 50,000 toman
        self.author.save()
        self.key = str(uuid4())
        response = self.post(duration=10, quoted_amount_rial=500000, request_key=self.key)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'insufficient_funds')
        self.assertEqual(self.balance(), 100000)
        self.assertFalse(ReservationCredit.objects.exists())
        return_path = '/visits/{}/name?reservation_payment={}'.format(self.author.pk, self.key)
        response = self.client.post('/transaction/', {
            'userId': self.user.pk, 'amount': 500000, 'authorLink': return_path,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        order = response.data['id']
        with patch('payment.paystar_views.create_payment', return_value={
            'ref_num': 'reservation-ref', 'paid': 500000,
            'link': 'https://core.paystar.ir/api/pardakht/payment?token=fake',
        }) as create:
            response = self.client.post('/gateway/paystar/create/link/', {'order_id': order}, format='json')
        self.assertEqual(response.status_code, 200)
        create.assert_called_once_with(500000, order)
        return {'status': '1', 'order_id': str(order), 'ref_num': 'reservation-ref',
                'card_number': 'masked', 'tracking_code': 'test-track'}

    @patch('payment.paystar_views.verify_payment', return_value={'card_number': 'masked'})
    def test_full_payment_preserves_old_balance_and_resume_is_idempotent(self, verify):
        callback = self.prepare_payment()
        for _ in range(2):
            response = self.client.post('/gateway/paystar/confirm/', callback, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        verify.assert_called_once()
        self.assertEqual(self.balance(), 600000)
        for _ in range(2):
            response = self.post(duration=10, quoted_amount_rial=500000, request_key=self.key)
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.balance(), 100000)
        self.assertEqual(ReservationCredit.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(Transaction.objects.get(pk=callback['order_id']).amount, 500000)

    @patch('payment.paystar_views.verify_payment')
    def test_cancelled_payment_never_credits_wallet_or_books(self, verify):
        callback = self.prepare_payment()
        callback['status'] = '-98'
        self.assertEqual(self.client.post('/gateway/paystar/confirm/', callback, format='json').status_code, 400)
        verify.assert_not_called()
        self.assertEqual(self.balance(), 100000)
        self.assertFalse(ReservationCredit.objects.exists())
        self.assertFalse(Task.objects.exists())

    @patch('payment.paystar_views.verify_payment', return_value={'card_number': 'masked'})
    def test_slot_taken_during_payment_keeps_full_topup_in_wallet(self, verify):
        from . import reservation_services as services
        callback = self.prepare_payment()
        services.book(self.other, self.author.pk, self.other.username, self.start, 10, uuid4())
        response = self.client.post('/gateway/paystar/confirm/', callback, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.post(duration=10, quoted_amount_rial=500000, request_key=self.key)
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(self.balance(), 600000)
        self.assertFalse(ReservationCredit.objects.filter(payer=self.user).exists())
        self.assertEqual(ReservationCredit.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 3)
