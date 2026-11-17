"""Real row-lock assertions. SQLite deliberately skips these tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from uuid import uuid4
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.exceptions import APIException
from .models import Author, ReservationCredit
from . import reservation_services as svc


@skipUnlessDBFeature('has_select_for_update')
class ReservationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.doctor = get_user_model().objects.create_user(username='9120000002')
        self.users = [get_user_model().objects.create_user(username='912000000' + str(i), amount=300000) for i in (1, 3)]
        self.author = Author.objects.create(userId=self.doctor, status=True, call_price=1000,
            service_time=timezone.now() + timedelta(days=365), **{d: '09:00,18:00' for d in svc.DAYS})
        self.start = (timezone.localtime(timezone.now(), svc.TEHRAN) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    def booking(self, user_id, start=None):
        user = get_user_model().objects.get(pk=user_id)
        return svc.book(user, self.author.pk, user.username, start or self.start, 30, uuid4())

    def threaded(self, function):
        close_old_connections()
        try:
            return function()
        except APIException as error:
            return error.status_code
        finally:
            close_old_connections()

    def race(self, functions):
        barrier = Barrier(len(functions))
        def run(fn):
            barrier.wait(timeout=10)
            return self.threaded(fn)
        with ThreadPoolExecutor(max_workers=len(functions)) as pool:
            futures = [pool.submit(run, fn) for fn in functions]
            return [f.result(timeout=20) for f in futures]

    def test_two_users_overlapping_interval_only_one_wins(self):
        results = self.race([lambda: self.booking(self.users[0].pk),
            lambda: self.booking(self.users[1].pk, self.start + timedelta(minutes=10))])
        self.assertEqual(sum(isinstance(r, ReservationCredit) for r in results), 1)
        self.assertIn(409, results)
        self.assertEqual(ReservationCredit.objects.count(), 1)
        self.assertEqual(sum(get_user_model().objects.get(pk=u.pk).amount for u in self.users), 300000)

    def test_same_wallet_concurrent_nonoverlapping_bookings_cannot_overspend(self):
        results = self.race([lambda: self.booking(self.users[0].pk),
            lambda: self.booking(self.users[0].pk, self.start + timedelta(hours=1))])
        self.assertEqual(sum(isinstance(r, ReservationCredit) for r in results), 1)
        self.assertIn(400, results)
        self.assertEqual(get_user_model().objects.get(pk=self.users[0].pk).amount, 0)

    def test_concurrent_cancellations_refund_once(self):
        credit = self.booking(self.users[0].pk)
        self.race([lambda: svc.cancel(credit.pk, self.doctor), lambda: svc.cancel(credit.pk, self.doctor)])
        self.assertEqual(get_user_model().objects.get(pk=self.users[0].pk).amount, 300000)
        credit.refresh_from_db()
        self.assertEqual(credit.refunded_rial, 300000)
        self.assertEqual(credit.notifications.filter(kind='cancellation').count(), 1)

    def test_duplicate_workers_cannot_dispatch_second_call(self):
        credit = self.booking(self.users[0].pk)
        accepted = Event(); release = Event()
        def provider(*args):
            accepted.set()
            if not release.wait(timeout=10): raise RuntimeError('test timeout')
            return 12345
        with patch('django.utils.timezone.now', return_value=self.start), patch('api.reservation_providers.create_call', side_effect=provider) as mock:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(self.threaded, lambda: svc.dispatch(credit.pk))
                self.assertTrue(accepted.wait(timeout=10))
                second = pool.submit(self.threaded, lambda: svc.dispatch(credit.pk))
                second.result(timeout=10)
                release.set(); first.result(timeout=10)
        self.assertEqual(mock.call_count, 1)

    def test_concurrent_final_callbacks_refund_once(self):
        credit = self.booking(self.users[0].pk)
        with patch('django.utils.timezone.now', return_value=self.start), patch('api.reservation_providers.create_call', return_value=123):
            svc.dispatch(credit.pk)
        credit.refresh_from_db()
        self.race([lambda: svc.settle(credit.call_id, 100000, 200000, 'done'),
            lambda: svc.settle(credit.call_id, 100000, 200000, 'done')])
        self.assertEqual(get_user_model().objects.get(pk=self.users[0].pk).amount, 100000)
