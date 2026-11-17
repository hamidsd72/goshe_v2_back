from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch
import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError
from io import StringIO
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from background_task.models import Task
from call.models import CallLog, Number
from .models import Author, AuthorVisit, ReservationCredit
from . import reservation_services as svc
from .reservation_providers import send_pattern
from account.services import SmsDeliveryError
from .tasks import reservation_call, reservation_sms


class ReservationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='9120000001', amount=1000000)
        self.doctor = get_user_model().objects.create_user(username='9120000002', is_author=True)
        self.other = get_user_model().objects.create_user(username='9120000003', amount=1000000)
        self.author = Author.objects.create(userId=self.doctor, status=True, call_price=1000,
            **{day: '09:00,18:00' for day in svc.DAYS})
        tomorrow = timezone.localtime(timezone.now(), svc.TEHRAN) + timedelta(days=1)
        self.start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def book(self, **kwargs):
        args = dict(user=self.user, author_id=self.author.pk, number=self.user.username,
                    start=self.start, duration=30, request_key=uuid4())
        args.update(kwargs)
        return svc.book(**args)

    def balance(self):
        self.user.refresh_from_db()
        return self.user.amount

    def post(self, **kwargs):
        body = dict(AuthorId=self.author.pk, number=self.user.username, visitTime=self.start.isoformat(), duration=30, request_key=str(uuid4()))
        body.update(kwargs)
        body.setdefault('quoted_amount_rial', body['duration'] * 10000)
        return self.client.post('/user-register-shift-using-author/', body, format='json')

    def due(self, credit):
        return patch('django.utils.timezone.now', return_value=credit.visit.visitTime)

    def test_booking_snapshots_rial_amount_and_queues_atomically(self):
        with patch('account.services.requests.post') as http:
            credit = self.book()
        self.assertEqual((credit.amount_rial, credit.rate_rial, self.balance()), (300000, 10000, 700000))
        self.assertEqual(credit.consultant_number, self.doctor.username)
        self.assertTrue(credit.visit.active and credit.visit.autoDial)
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(Task.objects.get(pk=credit.task_id).run_at, self.start)
        self.assertEqual(credit.notifications.count(), 2)
        http.assert_not_called()

    def test_all_durations_use_server_price_and_owner(self):
        for offset, duration in enumerate((10, 30, 60)):
            response = self.post(duration=duration, visitTime=(self.start + timedelta(days=offset)).isoformat(),
                amount_rial=1, userId=self.other.pk, AuthorUserId=self.other.pk)
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data['amount_rial'], duration * 10000)
            self.assertEqual(response.data['userId'], self.user.pk)

    def test_invalid_times_durations_and_closed_hours_leave_no_charge(self):
        today = self.start - timedelta(days=1)
        for start, duration in [(today, 10), (today - timedelta(days=1), 10),
            (self.start.replace(hour=8), 10), (self.start.replace(hour=17, minute=40), 30),
            (self.start.replace(minute=1), 10), (self.start, 20), (self.start + timedelta(days=15), 10)]:
            self.assertEqual(self.post(visitTime=start.isoformat(), duration=duration).status_code, 400)
        setattr(self.author, svc.DAYS[self.start.weekday()], '18:00,09:00'); self.author.save()
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(self.balance(), 1000000)
        self.assertFalse(Task.objects.exists())

    def test_insufficient_funds_and_unowned_numbers_leave_no_rows(self):
        self.assertEqual(self.post(number=self.other.username).status_code, 400)
        self.assertEqual(self.post(number='09120000001').status_code, 400)
        get_user_model().objects.filter(pk=self.user.pk).update(amount=1)
        self.assertEqual(self.post().status_code, 400)
        self.assertFalse(ReservationCredit.objects.exists())
        self.assertFalse(AuthorVisit.objects.exists())

    def test_registered_landline_uses_login_mobile_for_sms(self):
        Number.objects.create(userId=self.user, number='2112345678')
        credit = self.book(number='2112345678')
        self.assertEqual(credit.customer_sms_number, '0' + self.user.username)

    def test_overlap_across_duplicate_author_profiles_is_rejected(self):
        self.book()
        duplicate = Author.objects.create(userId=self.doctor, status=True, call_price=1000,
            **{day: '09:00,18:00' for day in svc.DAYS})
        response = self.post(AuthorId=duplicate.pk, visitTime=(self.start + timedelta(minutes=10)).isoformat())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(ReservationCredit.objects.count(), 1)
        self.assertEqual(self.balance(), 700000)

    def test_adjacent_reservations_allowed(self):
        self.book(); self.book(start=self.start + timedelta(minutes=30))
        self.assertEqual(ReservationCredit.objects.count(), 2)

    def test_request_key_deduplicates_retries_and_rejects_changed_payload(self):
        key = str(uuid4())
        a = self.post(request_key=key); b = self.post(request_key=key)
        self.assertEqual(a.data['id'], b.data['id'])
        self.assertEqual(self.balance(), 700000)
        self.assertEqual(Task.objects.count(), 3)
        self.assertEqual(self.post(request_key=key, duration=10).status_code, 400)

    def test_queue_failure_rolls_back_wallet_and_booking(self):
        with patch('api.tasks.reservation_call', side_effect=RuntimeError('queue failed')):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.book()
        self.assertEqual(self.balance(), 1000000)
        self.assertFalse(AuthorVisit.objects.exists())

    def test_cancel_refunds_once_deletes_job_and_notifies(self):
        credit = self.book(); self.client.force_authenticate(self.doctor)
        url = '/author-shift/{}/cancel/'.format(credit.pk)
        for _ in range(2):
            self.assertEqual(self.client.post(url, {}, format='json').status_code, 200)
        self.assertEqual(self.balance(), 1000000)
        credit.refresh_from_db()
        self.assertEqual(credit.refunded_rial, credit.amount_rial)
        self.assertFalse(Task.objects.filter(pk=credit.task_id).exists())
        self.assertEqual(credit.notifications.filter(kind='cancellation').count(), 1)
        with patch('api.reservation_providers.create_call') as provider:
            reservation_call.now(credit.pk)
        provider.assert_not_called()

    def test_cancel_permissions_and_old_mutation_routes_closed(self):
        credit = self.book()
        self.assertEqual(self.client.post('/author-shift/{}/cancel/'.format(credit.pk)).status_code, 404)
        self.assertEqual(self.client.patch('/user-register-shift-using-author/{}/'.format(credit.pk), {'active': True}).status_code, 405)
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.patch('/author-shift/{}/'.format(credit.pk), {'active': True}).status_code, 405)

    def test_anonymous_cannot_read_or_book(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/author-shift-list/?authorId={}'.format(self.author.pk)).status_code, 401)
        self.assertEqual(self.post().status_code, 401)

    def test_available_slots_exclude_today_and_overlapping_intervals(self):
        self.book()
        response = self.client.get('/author-shift-list/', {'authorId': self.author.pk, 'duration': 60})
        self.assertEqual(response.status_code, 200)
        starts = [s['start'] for s in response.data['slots']]
        self.assertNotIn(self.start.isoformat(), starts)
        self.assertNotIn((self.start - timedelta(minutes=20)).isoformat(), starts)
        self.assertIn((self.start + timedelta(minutes=30)).isoformat(), starts)
        for item in response.data['slots']:
            start = timezone.datetime.fromisoformat(item['start'])
            self.assertGreater(start.date(), timezone.localtime(timezone.now(), svc.TEHRAN).date())
            self.assertLessEqual(start.hour, 17)

    def test_legacy_records_remain_and_block_conflicting_interval(self):
        old = AuthorVisit.objects.create(AuthorId=self.author, AuthorUserId=self.doctor, userId=self.other,
            number=self.other.username, visitTime=self.start, active=True)
        self.assertEqual(self.post().status_code, 409)
        self.assertFalse(ReservationCredit.objects.filter(visit=old).exists())

    def test_booking_and_cancellation_sms_patterns_and_arguments(self):
        credit = self.book()
        with patch('api.reservation_providers.send_pattern', return_value='9999999999999999') as sms:
            for notice in credit.notifications.all():
                reservation_sms.now(notice.pk); reservation_sms.now(notice.pk)
        self.assertEqual(sms.call_count, 2)
        for call in sms.call_args_list:
            self.assertEqual(call.args[1], 589588)
            self.assertEqual(call.args[2][1], '10:00')
            self.assertEqual(len(call.args[2]), 2)
        svc.cancel(credit.pk, self.doctor)
        with patch('api.reservation_providers.send_pattern', return_value='9999999999999999') as sms:
            reservation_sms.now(credit.notifications.get(kind='cancellation').pk)
        self.assertEqual(sms.call_args.args[1], 589593)
        self.assertEqual(len(sms.call_args.args[2]), 1)

    def test_sms_timeout_does_not_undo_booking_or_blindly_resend(self):
        credit = self.book(); notice = credit.notifications.first()
        with patch('api.reservation_providers.send_pattern', side_effect=requests.Timeout) as sms:
            reservation_sms.now(notice.pk); reservation_sms.now(notice.pk)
        self.assertEqual(sms.call_count, 1)
        notice.refresh_from_db(); self.assertEqual(notice.status, 'unknown')
        self.assertEqual(self.balance(), 700000)

    def test_call_uses_only_reserved_credit_original_rate_and_phones(self):
        credit = self.book()
        self.author.call_price = 9000; self.author.save()
        self.doctor.username = '9120000099'; self.doctor.save()
        with self.due(credit), patch('call.views.requests.request') as http:
            http.return_value.json.return_value = {'Sitak_id': 999, 'status_id': 1}
            reservation_call.now(credit.pk); reservation_call.now(credit.pk)
        self.assertEqual(http.call_count, 1)
        data = http.call_args.kwargs['data']
        self.assertEqual(data['Credit'], '300000'); self.assertEqual(data['AmountPerMin'], '10000')
        self.assertEqual(data['ConsultantNum'], '09120000002'); self.assertEqual(data['CustomerNum'], '09120000001')
        self.assertEqual(self.balance(), 700000); self.assertEqual(CallLog.objects.count(), 1)

    def test_early_job_never_calls(self):
        credit = self.book()
        with patch('api.reservation_providers.create_call') as provider:
            with self.assertRaises(ValueError): reservation_call.now(credit.pk)
        provider.assert_not_called()

    def test_late_call_refunds_without_dialing(self):
        credit = self.book()
        with patch('django.utils.timezone.now', return_value=self.start + timedelta(minutes=6)), patch('api.reservation_providers.create_call') as provider:
            reservation_call.now(credit.pk)
        provider.assert_not_called(); self.assertEqual(self.balance(), 1000000)

    def test_unknown_call_result_holds_funds_without_duplicate_call(self):
        credit = self.book()
        with self.due(credit), patch('api.reservation_providers.create_call', side_effect=requests.Timeout) as provider:
            reservation_call.now(credit.pk); reservation_call.now(credit.pk)
        self.assertEqual(provider.call_count, 1)
        credit.refresh_from_db(); self.assertEqual(credit.status, 'uncertain')
        self.assertEqual(self.balance(), 700000)

    def test_callback_returns_unused_credit_once(self):
        credit = self.book()
        with self.due(credit), patch('api.reservation_providers.create_call', return_value=999): reservation_call.now(credit.pk)
        admin = get_user_model().objects.create_superuser(username='9120000098', password='test')
        self.client.force_authenticate(admin)
        data = {'Sitak_id': 999, 'LastCredit': 100000, 'call_amount': 200000,
                'Customer_Call_Detail': 'done', 'Consultant_Call_Detail': 'done'}
        for _ in range(2):
            response = self.client.post('/update_call/', data, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.balance(), 800000)
        credit.refresh_from_db(); self.assertEqual(credit.status, 'completed')
        self.assertEqual(credit.refunded_rial, 100000); self.assertEqual(credit.call.call_amount, 200000)

    def test_bad_or_unauthorized_callback_does_not_refund(self):
        credit = self.book()
        with self.due(credit), patch('api.reservation_providers.create_call', return_value=999): reservation_call.now(credit.pk)
        self.assertEqual(self.client.post('/update_call/', {'Sitak_id': 999, 'LastCredit': 999999}).status_code, 403)
        with self.assertRaises(ValidationError): svc.settle(CallLog.objects.get().pk, 400000, 0, 'bad')
        self.assertEqual(self.balance(), 700000)

    def test_callback_before_create_response_cannot_reopen_completed_call(self):
        credit = self.book()
        def callback(call, held):
            svc.settle(call.pk, held.amount_rial, 0, 'no answer')
            return 999
        with self.due(credit), patch('api.reservation_providers.create_call', side_effect=callback): reservation_call.now(credit.pk)
        credit.refresh_from_db(); self.assertEqual(credit.status, 'completed')
        self.assertEqual(self.balance(), 1000000)

    def test_sms_adapter_uses_console_token_json_and_receipt(self):
        with patch('account.services.requests.post') as http:
            http.return_value.json.return_value = {'status': 'خطا'}
            with self.assertRaises(SmsDeliveryError): send_pattern(self.user.username, 589588, ['1405/01/01', '10:00'])
            http.return_value.json.return_value = {'recId': '9999999999999999', 'status': 'عملیات موفق'}
            self.assertEqual(send_pattern(self.user.username, 589588, ['1405/01/01', '10:00']), '9999999999999999')
            self.assertEqual(http.call_args.args[0], 'https://console.melipayamak.com/api/send/shared/test-only-console-token')
            self.assertEqual(http.call_args.kwargs['json'], {
                'bodyId': 589588, 'to': '09120000001', 'args': ['1405/01/01', '10:00']})
            self.assertNotIn('data', http.call_args.kwargs)

    def test_inactive_or_unconfigured_consultant_cannot_charge(self):
        self.author.status = False; self.author.save()
        self.assertEqual(self.post().status_code, 400)
        self.author.status = True; self.author.save()
        with override_settings(MELIPAYAMAK_OTP_TOKEN=''):
            self.assertEqual(self.post().status_code, 400)
        self.assertEqual(self.balance(), 1000000)

    def test_busy_participant_at_due_time_refunds_once(self):
        credit = self.book()
        CallLog.objects.create(userId=self.other, authorId=self.doctor, type='کد 1 در حال تماس')
        with self.due(credit), patch('api.reservation_providers.create_call') as provider:
            reservation_call.now(credit.pk); reservation_call.now(credit.pk)
        provider.assert_not_called()
        self.assertEqual(self.balance(), 1000000)

    def test_ordinary_call_cannot_overlap_reserved_call(self):
        credit = self.book()
        with self.due(credit), patch('api.reservation_providers.create_call', return_value=999): reservation_call.now(credit.pk)
        with patch('call.views.requests.request') as provider:
            response = self.client.post('/call_create/', {'userNember': self.user.username, 'userIdAuthor': self.doctor.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.balance(), 700000)
        provider.assert_not_called()

    def test_cancel_after_dispatch_or_due_time_is_rejected(self):
        credit = self.book()
        with self.due(credit):
            with self.assertRaises(ValidationError): svc.cancel(credit.pk, self.doctor)
            with patch('api.reservation_providers.create_call', return_value=999): reservation_call.now(credit.pk)
        with self.assertRaises(ValidationError): svc.cancel(credit.pk, self.doctor)
        self.assertEqual(self.balance(), 700000)

    def test_owners_lists_do_not_leak_other_reservations(self):
        credit = self.book()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/user-register-shift-using-author/').data, [])
        self.assertEqual(self.client.get('/author-shift/').data, [])
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.get('/author-shift/').data[0]['id'], credit.pk)

    def test_stuck_call_reconciliation_requires_confirmation_and_never_double_refunds(self):
        credit = self.book()
        with self.due(credit), patch('api.reservation_providers.create_call', side_effect=requests.Timeout): reservation_call.now(credit.pk)
        with self.assertRaises(CommandError): call_command('reconcile_reservation', credit.pk, not_created=True)
        call_command('reconcile_reservation', credit.pk, not_created=True, confirm_provider_checked=True, stdout=StringIO())
        self.assertEqual(self.balance(), 1000000)
        with self.assertRaises(CommandError):
            call_command('reconcile_reservation', credit.pk, not_created=True, confirm_provider_checked=True)

    def test_unknown_sms_retry_requires_confirmation(self):
        credit = self.book(); notice = credit.notifications.first()
        with patch('api.reservation_providers.send_pattern', side_effect=requests.Timeout): reservation_sms.now(notice.pk)
        with self.assertRaises(CommandError): call_command('retry_reservation_sms', notice.pk)
        call_command('retry_reservation_sms', notice.pk, confirm_provider_checked=True, stdout=StringIO())
        notice.refresh_from_db(); self.assertEqual(notice.status, 'pending')

    def test_stale_price_quote_never_silently_charges_higher_rate(self):
        self.assertEqual(self.post(quoted_amount_rial=1).status_code, 409)
        self.assertEqual(self.balance(), 1000000)
        self.assertFalse(ReservationCredit.objects.exists())

    def test_invalid_consultant_phone_is_validation_error_not_server_error(self):
        self.doctor.username = 'not-a-phone'; self.doctor.save()
        self.assertEqual(self.post().status_code, 400)
        self.assertEqual(self.balance(), 1000000)
